"""
Neurotype quiz engine — deterministic, pure-math scoring. No LLM, no I/O
beyond loading the JSON bank, stdlib + the neurotypes registry only.

Two concerns, kept separate so both are easy to reason about:
  1. clean_answers()  — the SECURITY / data-cleaning boundary. Anything that
     isn't a real (question_id, option_id) pair from the loaded bank is
     dropped. Nothing untrusted from the wire reaches scoring or the DB.
  2. score()          — pure arithmetic over cleaned answers + the profile's
     skills, producing a ranked, normalized result. Same input -> same output.

The question bank is a versioned JSON file (bank_v1.json, bank_v2.json ...);
swap/extend it to retune without touching this engine. That is the "modular,
keep changing and testing" requirement.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.neurotypes import NEUROTYPE_IDS, score_skills

# Skills nudge the result; the quiz dominates. Tunable in one place.
SKILL_WEIGHT = 0.5
# Hard cap on how many answer pairs we'll even look at, so an oversized payload
# can't make us do unbounded work before validation trims it.
_MAX_ANSWER_PAIRS = 500
_BANK_DIR = Path(__file__).resolve().parent
_VERSION_RE = re.compile(r"^v[0-9]{1,4}$")


class QuizError(Exception):
    pass


class UnknownBankError(QuizError):
    pass


class InvalidBankError(QuizError):
    pass


@functools.lru_cache(maxsize=8)
def load_bank(version: str = "v1") -> dict:
    """Load and validate a question bank by version. `version` is sanitized
    (v + digits only) so it can be passed straight from an API query without
    path traversal risk."""
    if not isinstance(version, str) or not _VERSION_RE.match(version):
        raise UnknownBankError(f"Invalid bank version: {version!r}")
    path = _BANK_DIR / f"bank_{version}.json"
    if not path.is_file():
        raise UnknownBankError(f"No question bank for version {version!r}")
    try:
        bank = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise InvalidBankError(f"Could not read bank {version!r}: {e}") from e
    _validate_bank(bank)
    return bank


def _validate_bank(bank: Any) -> None:
    if not isinstance(bank, dict) or "questions" not in bank or "version" not in bank:
        raise InvalidBankError("Bank must be an object with 'version' and 'questions'.")
    valid_types = set(NEUROTYPE_IDS)
    seen_q = set()
    if not isinstance(bank["questions"], list) or not bank["questions"]:
        raise InvalidBankError("Bank 'questions' must be a non-empty list.")
    for q in bank["questions"]:
        if not isinstance(q, dict) or "id" not in q or "options" not in q:
            raise InvalidBankError("Each question needs 'id' and 'options'.")
        if q["id"] in seen_q:
            raise InvalidBankError(f"Duplicate question id: {q['id']}")
        seen_q.add(q["id"])
        if not isinstance(q["options"], list) or not q["options"]:
            raise InvalidBankError(f"Question {q['id']} needs a non-empty 'options' list.")
        seen_o = set()
        for o in q["options"]:
            if not isinstance(o, dict) or "id" not in o or "weights" not in o:
                raise InvalidBankError(f"Option in {q['id']} needs 'id' and 'weights'.")
            if o["id"] in seen_o:
                raise InvalidBankError(f"Duplicate option id {o['id']} in {q['id']}")
            seen_o.add(o["id"])
            if not isinstance(o["weights"], dict):
                raise InvalidBankError(f"Weights for {q['id']}/{o['id']} must be an object.")
            for t in o["weights"]:
                if t not in valid_types:
                    raise InvalidBankError(f"Unknown neurotype {t!r} in {q['id']}/{o['id']}")


@functools.lru_cache(maxsize=8)
def _index(version: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """{question_id: {option_id: {type: weight}}} for O(1) validation + scoring."""
    bank = load_bank(version)
    idx: Dict[str, Dict[str, Dict[str, float]]] = {}
    for q in bank["questions"]:
        idx[q["id"]] = {o["id"]: {t: float(w) for t, w in o["weights"].items()} for o in q["options"]}
    return idx


def public_bank(version: str = "v1") -> dict:
    """The bank as sent to clients (Discord/web) to render — WITHOUT the
    scoring weights, so the mapping isn't guessable from the payload."""
    bank = load_bank(version)
    return {
        "version": bank["version"],
        "title": bank.get("title", ""),
        "description": bank.get("description", ""),
        "questions": [
            {
                "id": q["id"],
                "prompt": q["prompt"],
                "options": [{"id": o["id"], "label": o["label"]} for o in q["options"]],
            }
            for q in bank["questions"]
        ],
    }


def clean_answers(answers: Any, version: str = "v1") -> Dict[str, str]:
    """SECURITY boundary. Accepts either {question_id: option_id} or
    [{"question_id":..,"option_id":..}], and returns only the pairs that are
    real for this bank. Unknown/duplicate/oversized input is silently dropped —
    nothing untrusted survives to scoring or storage. Last answer for a
    question wins."""
    idx = _index(version)
    pairs: List[Tuple[Any, Any]] = []
    if isinstance(answers, dict):
        pairs = list(answers.items())
    elif isinstance(answers, list):
        for a in answers:
            if isinstance(a, dict) and "question_id" in a and "option_id" in a:
                pairs.append((a["question_id"], a["option_id"]))

    cleaned: Dict[str, str] = {}
    for qid, oid in pairs[:_MAX_ANSWER_PAIRS]:
        qid, oid = str(qid), str(oid)
        if qid in idx and oid in idx[qid]:
            cleaned[qid] = oid
    return cleaned


def score(answers: Any, skills: Optional[List[str]] = None, version: str = "v1") -> dict:
    """Clean, then score. Combines quiz weights with a modest skill nudge,
    normalizes to percentages, and ranks the 10 types deterministically
    (ties broken by canonical order). Returns everything needed to store an
    auditable QuizResponse and to show the user their result."""
    idx = _index(version)
    cleaned = clean_answers(answers, version)

    quiz = {t: 0.0 for t in NEUROTYPE_IDS}
    for qid, oid in cleaned.items():
        for t, w in idx[qid][oid].items():
            quiz[t] += w

    skill = score_skills(skills or [])
    combined = {t: quiz[t] + SKILL_WEIGHT * skill[t] for t in NEUROTYPE_IDS}
    total = sum(combined.values())

    order = {t: i for i, t in enumerate(NEUROTYPE_IDS)}
    ranked_ids = sorted(NEUROTYPE_IDS, key=lambda t: (-combined[t], order[t]))

    if total <= 0:
        # No usable signal (e.g. empty answers + no matching skills).
        percentages = {t: 0.0 for t in NEUROTYPE_IDS}
        top: Optional[str] = None
    else:
        percentages = {t: round(100.0 * combined[t] / total, 2) for t in NEUROTYPE_IDS}
        top = ranked_ids[0]

    return {
        "top": top,
        "top3": ranked_ids[:3] if top else [],
        "ranked": [
            {"id": t, "score": round(combined[t], 3), "percentage": percentages[t]}
            for t in ranked_ids
        ],
        "answered": len(cleaned),
        "total_questions": len(idx),
        "quiz_contribution": {t: round(quiz[t], 3) for t in NEUROTYPE_IDS},
        "skill_contribution": {t: round(skill[t], 3) for t in NEUROTYPE_IDS},
        "algorithm_version": version,
    }
