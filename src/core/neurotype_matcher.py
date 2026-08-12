"""
Neurotype Matching Algorithm for ZIMA Platform

This module implements the core matching algorithm that connects builders
based on neurotype compatibility, skill complementarity, project alignment,
and location proximity.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math
from enum import Enum


class Neurotype(Enum):
    """Neurotype enum with compatibility definitions"""
    SEEDCASTER = "seedcaster"
    FABRICANT = "fabricant"
    MYCELIAN = "mycelian"
    TERRAFORMER = "terraformer"
    DEVELOPER = "developer"
    ARTISAN = "artisan"
    CHRONICLER = "chronicler"
    CULTIVAR = "cultivar"
    LOOMKEEPER = "loomkeeper"
    VERDANT = "verdant"


@dataclass
class Profile:
    """Data class representing a user profile"""
    id: str
    discord_id: str
    display_name: str
    neurotype: Neurotype
    skills: List[str]
    offering: List[str]
    looking_for: List[str]
    projects: List[str]
    location: Optional[str]
    is_open: bool = True


class NeurotypeMatcher:
    """
    Core matching algorithm for ZIMA platform

    Uses a weighted scoring system across multiple dimensions:
    - Skill complementarity (40%): What one offers vs what another needs
    - Neurotype compatibility (25%): Predefined compatibility matrix
    - Project alignment (20%): Shared project interests
    - Location proximity (15%): Geographic/regional matching
    """

    # Neurotype compatibility matrix - scores from 0.0 (incompatible) to 1.0 (highly compatible)
    COMPATIBILITY_MATRIX = {
        Neurotype.SEEDCASTER: {
            Neurotype.SEEDCASTER: 0.7,
            Neurotype.FABRICANT: 0.8,
            Neurotype.CULTIVAR: 0.9,
            Neurotype.TERRAFORMER: 0.7,
            Neurotype.MYCELIAN: 0.6,
            Neurotype.DEVELOPER: 0.5,
            Neurotype.ARTISAN: 0.7,
            Neurotype.CHRONICLER: 0.6,
            Neurotype.LOOMKEEPER: 0.8,
            Neurotype.VERDANT: 0.5
        },
        Neurotype.FABRICANT: {
            Neurotype.FABRICANT: 0.7,
            Neurotype.SEEDCASTER: 0.8,
            Neurotype.DEVELOPER: 0.85,
            Neurotype.ARTISAN: 0.75,
            Neurotype.MYCELIAN: 0.65,
            Neurotype.TERRAFORMER: 0.7,
            Neurotype.CULTIVAR: 0.6,
            Neurotype.CHRONICLER: 0.5,
            Neurotype.LOOMKEEPER: 0.7,
            Neurotype.VERDANT: 0.6
        },
        Neurotype.MYCELIAN: {
            Neurotype.MYCELIAN: 0.7,
            Neurotype.FABRICANT: 0.65,
            Neurotype.CULTIVAR: 0.8,
            Neurotype.DEVELOPER: 0.7,
            Neurotype.ARTISAN: 0.6,
            Neurotype.TERRAFORMER: 0.75,
            Neurotype.SEEDCASTER: 0.6,
            Neurotype.CHRONICLER: 0.5,
            Neurotype.LOOMKEEPER: 0.6,
            Neurotype.VERDANT: 0.7
        },
        Neurotype.TERRAFORMER: {
            Neurotype.TERRAFORMER: 0.7,
            Neurotype.SEEDCASTER: 0.7,
            Neurotype.FABRICANT: 0.7,
            Neurotype.MYCELIAN: 0.75,
            Neurotype.ARTISAN: 0.8,
            Neurotype.DEVELOPER: 0.6,
            Neurotype.CULTIVAR: 0.7,
            Neurotype.CHRONICLER: 0.6,
            Neurotype.LOOMKEEPER: 0.8,
            Neurotype.VERDANT: 0.7
        },
        Neurotype.DEVELOPER: {
            Neurotype.DEVELOPER: 0.7,
            Neurotype.FABRICANT: 0.85,
            Neurotype.MYCELIAN: 0.7,
            Neurotype.ARTISAN: 0.7,
            Neurotype.CHRONICLER: 0.6,
            Neurotype.LOOMKEEPER: 0.6,
            Neurotype.VERDANT: 0.8,
            Neurotype.SEEDCASTER: 0.5,
            Neurotype.CULTIVAR: 0.6,
            Neurotype.TERRAFORMER: 0.6
        },
        Neurotype.ARTISAN: {
            Neurotype.ARTISAN: 0.7,
            Neurotype.FABRICANT: 0.75,
            Neurotype.TERRAFORMER: 0.8,
            Neurotype.CHRONICLER: 0.8,
            Neurotype.DEVELOPER: 0.7,
            Neurotype.MYCELIAN: 0.6,
            Neurotype.SEEDCASTER: 0.7,
            Neurotype.CULTIVAR: 0.7,
            Neurotype.LOOMKEEPER: 0.7,
            Neurotype.VERDANT: 0.6
        },
        Neurotype.CHRONICLER: {
            Neurotype.CHRONICLER: 0.7,
            Neurotype.ARTISAN: 0.8,
            Neurotype.LOOMKEEPER: 0.8,
            Neurotype.VERDANT: 0.7,
            Neurotype.SEEDCASTER: 0.6,
            Neurotype.FABRICANT: 0.5,
            Neurotype.MYCELIAN: 0.5,
            Neurotype.TERRAFORMER: 0.6,
            Neurotype.DEVELOPER: 0.6,
            Neurotype.CULTIVAR: 0.7
        },
        Neurotype.CULTIVAR: {
            Neurotype.CULTIVAR: 0.7,
            Neurotype.SEEDCASTER: 0.9,
            Neurotype.MYCELIAN: 0.8,
            Neurotype.TERRAFORMER: 0.7,
            Neurotype.FABRICANT: 0.6,
            Neurotype.ARTISAN: 0.7,
            Neurotype.CHRONICLER: 0.7,
            Neurotype.LOOMKEEPER: 0.7,
            Neurotype.VERDANT: 0.8,
            Neurotype.DEVELOPER: 0.6
        },
        Neurotype.LOOMKEEPER: {
            Neurotype.LOOMKEEPER: 0.7,
            Neurotype.SEEDCASTER: 0.8,
            Neurotype.FABRICANT: 0.7,
            Neurotype.TERRAFORMER: 0.8,
            Neurotype.CHRONICLER: 0.8,
            Neurotype.VERDANT: 0.9,
            Neurotype.ARTISAN: 0.7,
            Neurotype.MYCELIAN: 0.6,
            Neurotype.DEVELOPER: 0.6,
            Neurotype.CULTIVAR: 0.7
        },
        Neurotype.VERDANT: {
            Neurotype.VERDANT: 0.7,
            Neurotype.DEVELOPER: 0.8,
            Neurotype.LOOMKEEPER: 0.9,
            Neurotype.CHRONICLER: 0.7,
            Neurotype.MYCELIAN: 0.7,
            Neurotype.CULTIVAR: 0.8,
            Neurotype.SEEDCASTER: 0.5,
            Neurotype.FABRICANT: 0.6,
            Neurotype.TERRAFORMER: 0.7,
            Neurotype.ARTISAN: 0.6
        }
    }

    def __init__(self, profiles: List[Profile]):
        """
        Initialize matcher with list of profiles.

        An empty list is allowed: the pairwise calculate_*_score methods are
        pure functions of two Profile arguments and don't need a populated
        pool. Methods that DO need a pool (find_top_matches,
        find_matches_by_neurotype, search_profiles) raise or return empty
        results on their own when there's nothing to search — see below.

        Args:
            profiles: List of Profile objects to match against
        """
        self.profiles = profiles
        self._index_profiles()

    def _index_profiles(self) -> None:
        """Create lookup indexes for faster matching"""
        self._profile_by_id = {profile.id: profile for profile in self.profiles}
        self._profile_by_discord = {profile.discord_id: profile for profile in self.profiles}

    def _normalize_string(self, text: Optional[str]) -> str:
        """Normalize string for comparison"""
        if not text:
            return ""
        return text.lower().strip()

    def calculate_skill_score(self, user1: Profile, user2: Profile) -> float:
        """
        Calculate skill complementarity score

        Measures how well what user1 offers matches what user2 is looking for,
        and vice versa.

        Args:
            user1: First profile
            user2: Second profile

        Returns:
            float: Score between 0.0 and 1.0
        """
        user1_offering = set(user1.offering or [])
        user2_looking = set(user2.looking_for or [])

        user2_offering = set(user2.offering or [])
        user1_looking = set(user1.looking_for or [])

        # Calculate matches in both directions
        matches_1_to_2 = len(user1_offering.intersection(user2_looking))
        matches_2_to_1 = len(user2_offering.intersection(user1_looking))

        total_possible = max(len(user1_offering) + len(user2_offering), 1)

        return (matches_1_to_2 + matches_2_to_1) / total_possible

    def calculate_neurotype_score(self, user1: Profile, user2: Profile) -> float:
        """
        Calculate neurotype compatibility score

        Uses predefined compatibility matrix for neurotype pairs.

        Args:
            user1: First profile
            user2: Second profile

        Returns:
            float: Score between 0.0 and 1.0
        """
        compatibility = self.COMPATIBILITY_MATRIX.get(user1.neurotype, {}).get(user2.neurotype)
        return compatibility if compatibility is not None else 0.5

    def calculate_project_score(self, user1: Profile, user2: Profile) -> float:
        """
        Calculate project alignment score

        Measures overlap in project interests.

        Args:
            user1: First profile
            user2: Second profile

        Returns:
            float: Score between 0.0 and 1.0
        """
        user1_projects = set(user1.projects or [])
        user2_projects = set(user2.projects or [])

        if not user1_projects and not user2_projects:
            return 0.5  # Neutral score if no projects specified

        intersection = len(user1_projects.intersection(user2_projects))
        union = len(user1_projects.union(user2_projects))

        return intersection / union if union > 0 else 0.0

    def calculate_location_score(self, user1: Profile, user2: Profile) -> float:
        """
        Calculate location proximity score

        Simple string matching for now - could be enhanced with geocoding.

        Args:
            user1: First profile
            user2: Second profile

        Returns:
            float: Score between 0.0 and 1.0
        """
        loc1 = self._normalize_string(user1.location)
        loc2 = self._normalize_string(user2.location)

        if not loc1 or not loc2:
            return 0.5  # Neutral score if location not specified

        return 1.0 if loc1 == loc2 else 0.3

    def calculate_match_score(self, user1: Profile, user2: Profile) -> Dict[str, float]:
        """
        Calculate comprehensive match score

        Combines multiple scoring dimensions with weighted averages:
        - Skill complementarity: 40%
        - Neurotype compatibility: 25%
        - Project alignment: 20%
        - Location proximity: 15%

        Args:
            user1: First profile
            user2: Second profile

        Returns:
            Dict with total score and breakdown
        """
        skill_score = self.calculate_skill_score(user1, user2)
        neurotype_score = self.calculate_neurotype_score(user1, user2)
        project_score = self.calculate_project_score(user1, user2)
        location_score = self.calculate_location_score(user1, user2)

        total_score = (
            skill_score * 0.4 +
            neurotype_score * 0.25 +
            project_score * 0.2 +
            location_score * 0.15
        )

        return {
            "total": round(total_score, 4),
            "breakdown": {
                "skill_score": round(skill_score, 4),
                "neurotype_score": round(neurotype_score, 4),
                "project_score": round(project_score, 4),
                "location_score": round(location_score, 4)
            }
        }

    def find_top_matches(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Find top matches for a user

        Args:
            user_id: ID of user to find matches for
            limit: Maximum number of matches to return

        Returns:
            List of match dictionaries with profile and score

        Raises:
            KeyError: If user_id not found in profiles
        """
        if user_id not in self._profile_by_id:
            raise KeyError(f"User {user_id} not found in profiles")

        user = self._profile_by_id[user_id]

        # Filter out self and closed profiles
        candidates = [
            profile for profile in self.profiles
            if profile.id != user_id and profile.is_open
        ]

        # Calculate scores and sort
        scored_matches = []
        for candidate in candidates:
            score = self.calculate_match_score(user, candidate)
            scored_matches.append({
                "profile": candidate,
                "score": score
            })

        # Sort by total score (descending) and return top matches
        scored_matches.sort(key=lambda x: x["score"]["total"], reverse=True)

        return scored_matches[:limit]

    def find_matches_by_neurotype(self, neurotype: Neurotype, limit: int = 10) -> List[Profile]:
        """
        Find profiles by neurotype

        Args:
            neurotype: Neurotype to filter by
            limit: Maximum number of profiles to return

        Returns:
            List of matching profiles
        """
        return [
            profile for profile in self.profiles
            if profile.neurotype == neurotype and profile.is_open
        ][:limit]

    def search_profiles(self, query: str, limit: int = 10) -> List[Profile]:
        """
        Search profiles by name, skills, or location

        Args:
            query: Search term
            limit: Maximum number of results

        Returns:
            List of matching profiles
        """
        if not query:
            return []

        normalized_query = self._normalize_string(query)

        results = []
        for profile in self.profiles:
            if not profile.is_open:
                continue

            # Search in multiple fields
            if (normalized_query in self._normalize_string(profile.display_name) or
                normalized_query in self._normalize_string(profile.location or "") or
                any(normalized_query in self._normalize_string(skill) for skill in profile.skills or []) or
                any(normalized_query in self._normalize_string(project) for project in profile.projects or [])):
                results.append(profile)

                if len(results) >= limit:
                    break

        return results

    def get_profile_by_id(self, profile_id: str) -> Optional[Profile]:
        """Get profile by ID"""
        return self._profile_by_id.get(profile_id)

    def get_profile_by_discord_id(self, discord_id: str) -> Optional[Profile]:
        """Get profile by Discord ID"""
        return self._profile_by_discord.get(discord_id)