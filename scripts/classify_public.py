#!/usr/bin/env python3
"""
Public-tier classifier for the ZIMA public-mirror system.

This private repo is the team's single source of truth. A separate PUBLIC
mirror repo is generated from it, containing ONLY the files that have been
explicitly marked public here. The guiding rule is DENY-BY-DEFAULT: a file
is private unless it is on the allowlist, so forgetting about a file can
never leak it - the only way to expose something is to actively add it.

Three plain, gitignore-style control files at the repo root drive this:

  .public-allow    globs that ARE published to the public mirror
  .public-deny     hard fuse - always wins over allow, even by accident
                   (secrets, the matching algorithm / core IP, internal docs)
  .public-exclude  files a human has reviewed and deliberately kept private
                   (so `--check` stays quiet and interactive stops re-asking)

Precedence for any tracked file:
    on deny         -> BLOCKED (never public, even if also allowed)
    on allow        -> PUBLIC
    on exclude      -> private (reviewed)
    none of these   -> UNDECIDED (needs a human decision)

Usage:
    python scripts/classify_public.py                    # interactive review of UNDECIDED files
    python scripts/classify_public.py --keep-rest-private # mark all UNDECIDED files private in one shot
    python scripts/classify_public.py --check             # CI gate: non-zero exit on problems
    python scripts/classify_public.py --list              # print resolved PUBLIC paths (for the sync)
    python scripts/classify_public.py --summary           # human-readable counts

`--check` fails (exit 1) if either:
  * an allowlisted file is also denylisted (a contradiction to resolve), or
  * any tracked file is still UNDECIDED (someone must choose public/private).
This is what makes "it asks people whether a file is open or closed" an
enforced step: a new file cannot pass CI until it has been classified.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

ALLOW_FILE = ".public-allow"
DENY_FILE = ".public-deny"
EXCLUDE_FILE = ".public-exclude"


# ------------------------------- glob matching -------------------------------
#
# gitignore-style matching, stdlib-only (no pathspec dependency):
#   **   matches across path separators (any number of segments)
#   *    matches within a single path segment
#   ?    matches a single non-separator character
#   dir/ (trailing slash) matches everything under that directory
# Patterns are matched against repo-root-relative POSIX paths.


def _translate(pattern: str) -> re.Pattern[str]:
    pattern = pattern.strip().replace(os.sep, "/")
    # A trailing "/" means "this directory and everything under it".
    if pattern.endswith("/"):
        pattern = pattern + "**"

    out: List[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # "**" - consume it (and an immediately following "/") and match
                # any run of characters including separators.
                i += 2
                if i < n and pattern[i] == "/":
                    i += 1
                out.append(".*")
                continue
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _matches_any(path: str, patterns: Sequence[re.Pattern[str]]) -> bool:
    return any(p.match(path) for p in patterns)


# ------------------------------- control files -------------------------------


def _read_patterns(root: Path, name: str) -> List[str]:
    f = root / name
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    return out


def _append_pattern(root: Path, name: str, pattern: str) -> None:
    f = root / name
    existing = _read_patterns(root, name)
    if pattern in existing:
        return
    with f.open("a", encoding="utf-8") as fh:
        if f.exists() and f.stat().st_size > 0 and not f.read_text(encoding="utf-8").endswith("\n"):
            fh.write("\n")
        fh.write(pattern + "\n")


def _tracked_files(root: Path) -> List[str]:
    """All files git tracks, as repo-root-relative POSIX paths."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


# ------------------------------- classification -------------------------------


class Classification:
    def __init__(self, root: Path):
        self.root = root
        self._allow = [_translate(p) for p in _read_patterns(root, ALLOW_FILE)]
        self._deny = [_translate(p) for p in _read_patterns(root, DENY_FILE)]
        self._exclude = [_translate(p) for p in _read_patterns(root, EXCLUDE_FILE)]

    def classify(self, path: str) -> str:
        """Returns one of: 'blocked', 'public', 'private', 'undecided'."""
        if _matches_any(path, self._deny):
            return "blocked"
        if _matches_any(path, self._allow):
            return "public"
        if _matches_any(path, self._exclude):
            return "private"
        return "undecided"

    def conflicts(self, files: Sequence[str]) -> List[str]:
        """Files matched by BOTH allow and deny - a contradiction to fix."""
        return [
            f
            for f in files
            if _matches_any(f, self._allow) and _matches_any(f, self._deny)
        ]

    def buckets(self, files: Sequence[str]) -> dict[str, List[str]]:
        out: dict[str, List[str]] = {"public": [], "private": [], "blocked": [], "undecided": []}
        for f in files:
            out[self.classify(f)].append(f)
        return out


# ------------------------------- commands -------------------------------


def cmd_list(root: Path) -> int:
    cls = Classification(root)
    for f in sorted(cls.buckets(_tracked_files(root))["public"]):
        print(f)
    return 0


def cmd_summary(root: Path) -> int:
    cls = Classification(root)
    buckets = cls.buckets(_tracked_files(root))
    print("Public-mirror classification summary")
    print(f"  PUBLIC    : {len(buckets['public']):>4}  (published to the mirror)")
    print(f"  private   : {len(buckets['private']):>4}  (reviewed, kept private)")
    print(f"  blocked   : {len(buckets['blocked']):>4}  (denylist fuse)")
    print(f"  UNDECIDED : {len(buckets['undecided']):>4}  (need a decision)")
    if buckets["undecided"]:
        print("\nUndecided files (run without --summary to classify):")
        for f in sorted(buckets["undecided"]):
            print(f"  ? {f}")
    return 0


def cmd_check(root: Path) -> int:
    cls = Classification(root)
    files = _tracked_files(root)
    problems = 0

    conflicts = cls.conflicts(files)
    if conflicts:
        problems += len(conflicts)
        print("ERROR: files are on BOTH .public-allow and .public-deny (deny wins, but fix the intent):", file=sys.stderr)
        for f in sorted(conflicts):
            print(f"  ! {f}", file=sys.stderr)

    undecided = cls.buckets(files)["undecided"]
    if undecided:
        problems += len(undecided)
        print("ERROR: tracked files are unclassified - mark each public or private first:", file=sys.stderr)
        print("       run:  python scripts/classify_public.py", file=sys.stderr)
        for f in sorted(undecided):
            print(f"  ? {f}", file=sys.stderr)

    if problems:
        print(f"\n{problems} problem(s). Public mirror will NOT be published until resolved.", file=sys.stderr)
        return 1

    public = cls.buckets(files)["public"]
    print(f"OK: {len(public)} file(s) resolved as public, nothing undecided, no conflicts.")
    return 0


def cmd_interactive(root: Path) -> int:
    cls = Classification(root)
    undecided = sorted(cls.buckets(_tracked_files(root))["undecided"])
    if not undecided:
        print("Nothing to classify - every tracked file is already public, private, or blocked.")
        return 0

    if not sys.stdin.isatty():
        print("Refusing to run interactively without a TTY. Use --check in CI.", file=sys.stderr)
        return 2

    print(f"{len(undecided)} undecided file(s). For each: [p]ublic  [k]eep private  [s]kip  [q]uit\n")
    for f in undecided:
        while True:
            choice = input(f"  {f}  ->  [p/k/s/q]? ").strip().lower()
            if choice in ("p", "public"):
                _append_pattern(root, ALLOW_FILE, f)
                print(f"    + published: added to {ALLOW_FILE}")
                break
            if choice in ("k", "keep", ""):
                _append_pattern(root, EXCLUDE_FILE, f)
                print(f"    - kept private: added to {EXCLUDE_FILE}")
                break
            if choice in ("s", "skip"):
                print("    (skipped - still undecided)")
                break
            if choice in ("q", "quit"):
                print("\nStopped. Remaining files are still undecided.")
                return 0
            print("    please answer p, k, s, or q")
    print("\nDone. Re-run with --summary to review, --check to gate.")
    return 0


def cmd_keep_rest_private(root: Path) -> int:
    cls = Classification(root)
    undecided = sorted(cls.buckets(_tracked_files(root))["undecided"])
    if not undecided:
        print("Nothing undecided - every tracked file is already classified.")
        return 0
    for f in undecided:
        _append_pattern(root, EXCLUDE_FILE, f)
    print(f"Marked {len(undecided)} undecided file(s) as private (added to {EXCLUDE_FILE}):")
    for f in undecided:
        print(f"  - {f}")
    print("\nPublic tier is unchanged - edit .public-allow to publish any of these later.")
    return 0


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify files into the public mirror tier (deny-by-default).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="CI gate: non-zero exit on conflicts or undecided files")
    group.add_argument("--list", action="store_true", help="print resolved public paths, one per line")
    group.add_argument("--summary", action="store_true", help="print human-readable counts")
    group.add_argument(
        "--keep-rest-private",
        action="store_true",
        help="non-interactively mark every currently-undecided file as private",
    )
    parser.add_argument("--root", default=None, help="repo root (default: git toplevel)")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else _repo_root()

    if args.keep_rest_private:
        return cmd_keep_rest_private(root)
    if args.list:
        return cmd_list(root)
    if args.summary:
        return cmd_summary(root)
    if args.check:
        return cmd_check(root)
    return cmd_interactive(root)


if __name__ == "__main__":
    raise SystemExit(main())
