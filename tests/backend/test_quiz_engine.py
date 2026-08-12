"""
Tests for the neurotype quiz engine + registry — the correctness-critical,
pure-math core. No DB/deps, so these run anywhere.
"""

import sys
from pathlib import Path

import pytest

# Make `src` importable without the repo's conftest (which pulls in dotenv).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core import neurotypes as nt  # noqa: E402
from src.quiz import engine  # noqa: E402


# ─────────────────────────── registry ───────────────────────────


def test_ten_neurotypes_all_well_formed():
    assert len(nt.NEUROTYPE_IDS) == 10
    for n in nt.all_neurotypes():
        assert n["id"] in nt.NEUROTYPE_IDS
        assert n["label"] and n["emoji"] and n["tagline"]
        assert set(n["color"]) >= {"base", "border", "text", "badge_bg"}
        for other in n["connects_to"]:
            assert nt.is_valid_type(other)


def test_edges_are_symmetric_and_deduped():
    e = nt.edges()
    assert len(e) == len(set(e))                      # no dupes
    for a, b in e:
        assert a != b
        # authored from at least one side
        assert b in nt.NEUROTYPES[a]["connects_to"] or a in nt.NEUROTYPES[b]["connects_to"]


def test_score_skills_maps_keywords():
    s = nt.score_skills(["python developer", "ui design"])
    assert s["developer"] >= 1.0        # "python"/"developer" hit
    assert s["artisan"] >= 1.0          # "design" hits
    assert nt.score_skills([]) == {t: 0.0 for t in nt.NEUROTYPE_IDS}


# ─────────────────────────── bank loading ───────────────────────────


def test_load_bank_v1():
    bank = engine.load_bank("v1")
    assert bank["version"] == "v1"
    assert len(bank["questions"]) == 20


def test_bad_bank_version_rejected():
    for bad in ["../secrets", "v1; rm", "latest", "v", ""]:
        with pytest.raises(engine.UnknownBankError):
            engine.load_bank(bad)


def test_public_bank_hides_weights():
    pub = engine.public_bank("v1")
    for q in pub["questions"]:
        for o in q["options"]:
            assert "weights" not in o
            assert set(o) == {"id", "label"}


# ─────────────────────────── cleaning (security) ───────────────────────────


def test_clean_answers_drops_unknown_and_dedupes():
    ans = {
        "q01": "a",            # valid
        "q02": "zzz",          # bad option -> dropped
        "nope": "a",           # bad question -> dropped
        "q03": "b",            # valid
    }
    cleaned = engine.clean_answers(ans, "v1")
    assert cleaned == {"q01": "a", "q03": "b"}


def test_clean_answers_accepts_list_form_and_last_wins():
    ans = [
        {"question_id": "q01", "option_id": "a"},
        {"question_id": "q01", "option_id": "b"},   # last wins
        {"question_id": "junk"},                     # malformed -> ignored
        "not-a-dict",                                # ignored
    ]
    cleaned = engine.clean_answers(ans, "v1")
    assert cleaned == {"q01": "b"}


def test_clean_answers_handles_garbage_input():
    assert engine.clean_answers(None, "v1") == {}
    assert engine.clean_answers(42, "v1") == {}
    assert engine.clean_answers("hax", "v1") == {}


# ─────────────────────────── scoring ───────────────────────────


def test_score_empty_gives_no_top():
    r = engine.score({}, [], "v1")
    assert r["top"] is None
    assert r["answered"] == 0
    assert all(x["percentage"] == 0.0 for x in r["ranked"])


def test_score_is_deterministic_and_normalized():
    ans = {"q01": "c", "q02": "a", "q13": "a"}   # all lean fabricant
    r1 = engine.score(ans, [], "v1")
    r2 = engine.score(ans, [], "v1")
    assert r1 == r2                                   # deterministic
    assert r1["top"] == "fabricant"
    assert abs(sum(x["percentage"] for x in r1["ranked"]) - 100.0) < 0.5
    assert r1["ranked"][0]["id"] == "fabricant"
    assert r1["ranked"] == sorted(r1["ranked"], key=lambda x: -x["score"])


def test_skills_nudge_but_quiz_dominates():
    ans = {"q01": "c", "q02": "a"}  # fabricant-leaning
    with_dev_skills = engine.score(ans, ["python", "javascript", "devops"], "v1")
    # developer contribution should be > 0 from skills even though quiz didn't pick it
    assert with_dev_skills["skill_contribution"]["developer"] > 0
    assert with_dev_skills["top"] == "fabricant"   # quiz still wins


def test_score_only_from_skills():
    r = engine.score({}, ["policy", "advocacy", "governance"], "v1")
    assert r["top"] == "verdant"
    assert r["answered"] == 0
