"""
Canonical neurotype (archetype) registry — the single source of truth for the
10 archetypes' presentation and graph metadata.

Previously this lived only in the frontend (base44 `NEUROTYPES` in zimaData),
which meant the network graph, the badges and the API descriptions could drift
apart. It lives here now so every surface (Discord bot, web quiz, globe, API)
reads the same definitions.

Design notes:
  - Pure data + stdlib only. No third-party deps, no I/O, no LLM — cheap to
    import and trivial to port.
  - `connects_to` is authored per-node; `edges()` derives the de-duplicated,
    symmetric edge set for the graph so authoring stays simple but the graph
    stays consistent.
  - `skill_affinities` are lowercase keyword stems; `score_skills()` turns a
    profile's free-text skills into a per-type contribution that feeds the
    assessed neurotype alongside the quiz (your "general skills reflect a
    type"). Matching is substring-on-word so "ui design" hits "design".
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Ordered so any UI that iterates is stable.
NEUROTYPE_IDS: Tuple[str, ...] = (
    "seedcaster",
    "fabricant",
    "mycelian",
    "terraformer",
    "developer",
    "artisan",
    "chronicler",
    "cultivar",
    "loomkeeper",
    "verdant",
)

# Solarpunk-leaning palette; each type gets a distinct hue. Colours are plain
# hex strings so any renderer (globe, cards, Discord embeds) can use them.
NEUROTYPES: Dict[str, dict] = {
    "seedcaster": {
        "label": "Seedcaster",
        "emoji": "🌱",
        "tagline": "They plant what others haven't imagined yet.",
        "color": {"base": "#7BC86C", "border": "#4E9A45", "text": "#1E3A17", "badge_bg": "#E7F5E3"},
        "connects_to": ["verdant", "cultivar", "mycelian"],
        "skill_affinities": ["ideation", "vision", "strategy", "research", "futures", "concept", "founder", "product"],
    },
    "fabricant": {
        "label": "Fabricant",
        "emoji": "🛠️",
        "tagline": "If it doesn't exist, they build it.",
        "color": {"base": "#F0A64E", "border": "#C87E2A", "text": "#3A2410", "badge_bg": "#FBEEDD"},
        "connects_to": ["developer", "terraformer", "artisan"],
        "skill_affinities": ["hardware", "engineering", "manufacturing", "fabrication", "prototyping", "maker", "robotics", "cad"],
    },
    "mycelian": {
        "label": "Mycelian",
        "emoji": "🍄",
        "tagline": "They think in networks and grow in the dark.",
        "color": {"base": "#B784D8", "border": "#8B57B0", "text": "#2C1938", "badge_bg": "#F1E8F8"},
        "connects_to": ["loomkeeper", "seedcaster", "developer"],
        "skill_affinities": ["systems", "networks", "data", "analysis", "infrastructure", "protocol", "backend", "distributed"],
    },
    "terraformer": {
        "label": "Terraformer",
        "emoji": "🏗️",
        "tagline": "They redesign the spaces we inhabit.",
        "color": {"base": "#5FB0B7", "border": "#3B8189", "text": "#12302F", "badge_bg": "#E1F1F2"},
        "connects_to": ["fabricant", "cultivar", "verdant"],
        "skill_affinities": ["architecture", "urban", "spatial", "environment", "construction", "planning", "landscape", "3d"],
    },
    "developer": {
        "label": "Developer",
        "emoji": "💻",
        "tagline": "They write the tools of sovereignty.",
        "color": {"base": "#6C8CE0", "border": "#4560AE", "text": "#141F3A", "badge_bg": "#E4EAFA"},
        "connects_to": ["fabricant", "mycelian", "artisan"],
        "skill_affinities": ["software", "programming", "code", "developer", "javascript", "python", "web", "app", "fullstack", "devops"],
    },
    "artisan": {
        "label": "Artisan",
        "emoji": "🎨",
        "tagline": "They make the future beautiful enough to want.",
        "color": {"base": "#E87DA0", "border": "#B84E73", "text": "#3A1522", "badge_bg": "#FBE6EE"},
        "connects_to": ["chronicler", "developer", "fabricant"],
        "skill_affinities": ["design", "art", "illustration", "ui", "ux", "brand", "visual", "animation", "graphic", "creative"],
    },
    "chronicler": {
        "label": "Chronicler",
        "emoji": "📜",
        "tagline": "They make sure the work gets seen.",
        "color": {"base": "#E0C24E", "border": "#AE9327", "text": "#332A0E", "badge_bg": "#FAF3D9"},
        "connects_to": ["artisan", "loomkeeper", "verdant"],
        "skill_affinities": ["writing", "storytelling", "content", "media", "video", "social", "community media", "marketing", "documentation", "archiving"],
    },
    "cultivar": {
        "label": "Cultivar",
        "emoji": "🌾",
        "tagline": "They bridge the lab and the land.",
        "color": {"base": "#8FBF6B", "border": "#5F8F3D", "text": "#1F2E14", "badge_bg": "#EAF3E1"},
        "connects_to": ["seedcaster", "terraformer", "loomkeeper"],
        "skill_affinities": ["biology", "agriculture", "science", "food", "sustainability", "ecology", "chemistry", "lab", "farming"],
    },
    "loomkeeper": {
        "label": "Loomkeeper",
        "emoji": "🧵",
        "tagline": "They hold the network together.",
        "color": {"base": "#D98E6A", "border": "#A85E3C", "text": "#331A0F", "badge_bg": "#F8E9E0"},
        "connects_to": ["mycelian", "chronicler", "cultivar"],
        "skill_affinities": ["community", "organizing", "events", "partnerships", "operations", "facilitation", "fundraising", "coordination", "people"],
    },
    "verdant": {
        "label": "Verdant",
        "emoji": "🌍",
        "tagline": "They change the rules of the game.",
        "color": {"base": "#4FB477", "border": "#2E8451", "text": "#0F2E1C", "badge_bg": "#E0F2E8"},
        "connects_to": ["seedcaster", "terraformer", "chronicler"],
        "skill_affinities": ["policy", "advocacy", "law", "governance", "economics", "finance", "activism", "systems change", "funding"],
    },
}


def is_valid_type(neurotype: str) -> bool:
    return neurotype in NEUROTYPES


def get_neurotype(neurotype: str) -> dict:
    if neurotype not in NEUROTYPES:
        raise KeyError(f"Unknown neurotype: {neurotype!r}")
    return {"id": neurotype, **NEUROTYPES[neurotype]}


def all_neurotypes() -> List[dict]:
    return [get_neurotype(nid) for nid in NEUROTYPE_IDS]


def edges() -> List[Tuple[str, str]]:
    """De-duplicated symmetric edge list for the graph. If A lists B (or B
    lists A), the edge (A, B) appears exactly once, in NEUROTYPE_IDS order."""
    order = {nid: i for i, nid in enumerate(NEUROTYPE_IDS)}
    seen = set()
    out: List[Tuple[str, str]] = []
    for nid in NEUROTYPE_IDS:
        for other in NEUROTYPES[nid]["connects_to"]:
            if other not in NEUROTYPES:
                continue
            a, b = (nid, other) if order[nid] < order[other] else (other, nid)
            if (a, b) not in seen:
                seen.add((a, b))
                out.append((a, b))
    return out


def score_skills(skills: List[str]) -> Dict[str, float]:
    """Turn a profile's skills into a per-type contribution. Each skill that
    matches a type's affinity keyword (word-substring, case-insensitive) adds
    1.0 to that type. Deterministic, no allocation beyond the result dict."""
    scores = {nid: 0.0 for nid in NEUROTYPE_IDS}
    if not skills:
        return scores
    normalized = [str(s).strip().lower() for s in skills if str(s).strip()]
    for nid in NEUROTYPE_IDS:
        affinities = NEUROTYPES[nid]["skill_affinities"]
        for skill in normalized:
            if any(kw in skill for kw in affinities):
                scores[nid] += 1.0
    return scores
