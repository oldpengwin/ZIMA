"""
Tests for scripts/classify_public.py — the deny-by-default public-tier
classifier that decides which files reach the public mirror.

The matching/precedence logic (Classification) is tested directly with
in-memory file lists (no git needed). The git-backed commands (--list,
--check) are tested against a throwaway git repo in a tmp dir.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import classify_public as cp  # noqa: E402


def write_control(root: Path, allow=(), deny=(), exclude=()):
    (root / cp.ALLOW_FILE).write_text("\n".join(allow) + "\n", encoding="utf-8")
    (root / cp.DENY_FILE).write_text("\n".join(deny) + "\n", encoding="utf-8")
    (root / cp.EXCLUDE_FILE).write_text("\n".join(exclude) + "\n", encoding="utf-8")


# ─────────────────────────── glob matching ───────────────────────────


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        ("demo/**", "demo/index.html", True),
        ("demo/**", "demo/nested/deep/file.html", True),
        ("demo/**", "src/demo.py", False),
        ("demo/", "demo/index.html", True),          # trailing slash == dir contents
        ("README.md", "README.md", True),
        ("README.md", "src/README.md", False),        # anchored to root
        ("*.md", "README.md", True),
        ("*.md", "docs/x.md", False),                 # * does not cross separators
        ("**/*.md", "docs/x.md", True),
        ("**/.env*", ".env", True),
        ("**/.env*", "src/.env.local", True),
        ("**/*secret*", "src/core/mysecret_config.py", True),
        ("src/core/neurotype_matcher.py", "src/core/neurotype_matcher.py", True),
        ("src/core/neurotype_matcher.py", "src/core/neurotype_matcher.pyc", False),
    ],
)
def test_translate_matching(pattern, path, expected):
    assert bool(cp._translate(pattern).match(path)) is expected


# ─────────────────────────── precedence ───────────────────────────


def test_deny_wins_over_allow(tmp_path):
    write_control(tmp_path, allow=["src/**"], deny=["src/core/neurotype_matcher.py"])
    cls = cp.Classification(tmp_path)
    assert cls.classify("src/core/neurotype_matcher.py") == "blocked"
    assert cls.classify("src/api/routes.py") == "public"  # allowed, not denied


def test_allow_makes_public(tmp_path):
    write_control(tmp_path, allow=["demo/**", "README.md"])
    cls = cp.Classification(tmp_path)
    assert cls.classify("demo/index.html") == "public"
    assert cls.classify("README.md") == "public"


def test_exclude_is_reviewed_private(tmp_path):
    write_control(tmp_path, allow=["demo/**"], exclude=["src/api/routes.py"])
    cls = cp.Classification(tmp_path)
    assert cls.classify("src/api/routes.py") == "private"


def test_unclassified_is_undecided(tmp_path):
    write_control(tmp_path, allow=["demo/**"])
    cls = cp.Classification(tmp_path)
    assert cls.classify("src/api/routes.py") == "undecided"


def test_buckets_and_conflicts(tmp_path):
    write_control(tmp_path, allow=["demo/**", "secret.txt"], deny=["secret.txt"])
    cls = cp.Classification(tmp_path)
    files = ["demo/a.html", "secret.txt", "src/x.py"]
    buckets = cls.buckets(files)
    assert buckets["public"] == ["demo/a.html"]
    assert buckets["blocked"] == ["secret.txt"]      # deny wins
    assert buckets["undecided"] == ["src/x.py"]
    assert cls.conflicts(files) == ["secret.txt"]     # on both lists


# ─────────────────────────── git-backed commands ───────────────────────────


@pytest.fixture
def git_repo(tmp_path):
    def run(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    run("init")
    run("config", "user.email", "t@t.t")
    run("config", "user.name", "t")
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "README.md").write_text("# public", encoding="utf-8")
    (tmp_path / "secret.env").write_text("KEY=abc", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "routes.py").write_text("x = 1", encoding="utf-8")
    run("add", "-A")
    run("commit", "-m", "init")
    return tmp_path


def test_list_prints_only_public(git_repo, capsys):
    write_control(git_repo, allow=["demo/**", "README.md"], deny=["**/*.env"])
    # control files themselves are now tracked-less (not committed) but git ls-files
    # only returns committed/staged; add them so they appear, then they're undecided.
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    rc = cp.cmd_list(git_repo)
    out = capsys.readouterr().out.splitlines()
    assert rc == 0
    assert "demo/index.html" in out
    assert "README.md" in out
    assert "src/routes.py" not in out
    assert "secret.env" not in out


def test_check_fails_on_undecided(git_repo, capsys):
    write_control(git_repo, allow=["demo/**", "README.md"])
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    rc = cp.cmd_check(git_repo)
    assert rc == 1  # src/routes.py, secret.env, and control files are undecided


def test_keep_rest_private_then_check_passes(git_repo):
    write_control(git_repo, allow=["demo/**", "README.md"], deny=["**/*.env"])
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    assert cp.cmd_check(git_repo) == 1                 # undecided files exist
    assert cp.cmd_keep_rest_private(git_repo) == 0     # sweep them to private
    assert cp.cmd_check(git_repo) == 0                 # now green
    # demo + README still public, nothing got dragged into the public set
    public = cp.Classification(git_repo).buckets(cp._tracked_files(git_repo))["public"]
    assert "demo/index.html" in public and "README.md" in public
    assert "src/routes.py" not in public and "secret.env" not in public


def test_check_passes_when_all_classified(git_repo):
    write_control(
        git_repo,
        allow=["demo/**", "README.md"],
        deny=["**/*.env"],
        exclude=["src/routes.py", "secret.env", ".public-allow", ".public-deny", ".public-exclude"],
    )
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    rc = cp.cmd_check(git_repo)
    assert rc == 0
