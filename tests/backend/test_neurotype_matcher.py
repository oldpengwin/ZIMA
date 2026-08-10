"""
Test neurotype matching algorithm
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.neurotype_matcher import NeurotypeMatcher, Profile, Neurotype


def test_profile_creation():
    """Test profile creation"""
    profile = Profile(
        id="test-id",
        discord_id="test-user",
        display_name="Test User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python", "JavaScript"],
        offering=["Backend development"],
        looking_for=["Frontend developers"],
        projects=["ZIMA Platform"],
        location="Test City"
    )

    assert profile.id == "test-id"
    assert profile.discord_id == "test-user"
    assert profile.display_name == "Test User"
    assert profile.neurotype == Neurotype.DEVELOPER
    assert len(profile.skills) == 2


def test_neurotype_compatibility_matrix():
    """Test that compatibility matrix is properly defined"""
    assert len(NeurotypeMatcher.COMPATIBILITY_MATRIX) == 10  # 10 neurotypes

    for neurotype in Neurotype:
        assert neurotype in NeurotypeMatcher.COMPATIBILITY_MATRIX
        compatibilities = NeurotypeMatcher.COMPATIBILITY_MATRIX[neurotype]
        assert len(compatibilities) == 10  # Each neurotype has 10 compatibility scores

        # Check that scores are between 0 and 1
        for other_neurotype, score in compatibilities.items():
            assert 0.0 <= score <= 1.0


def test_skill_complementarity_score():
    """Test skill complementarity scoring"""
    matcher = NeurotypeMatcher([])

    user1 = Profile(
        id="user1",
        discord_id="user1",
        display_name="User 1",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python", "JavaScript"],
        offering=["Backend development", "API design"],
        looking_for=["Frontend developers"],
        projects=[],
        location=""
    )

    user2 = Profile(
        id="user2",
        discord_id="user2",
        display_name="User 2",
        neurotype=Neurotype.ARTISAN,
        skills=["Design", "UI/UX"],
        offering=["UI design"],
        looking_for=["Backend development", "API design"],
        projects=[],
        location=""
    )

    score = matcher.calculate_skill_score(user1, user2)
    # User1 offers what user2 is looking for (Backend development, API design)
    # User2 offers what user1 is looking for (Frontend developers - UI design is close)
    assert 0.0 <= score <= 1.0
    # Should have high score due to good complementarity
    assert score > 0.5


def test_neurotype_compatibility_score():
    """Test neurotype compatibility scoring"""
    matcher = NeurotypeMatcher([])

    user1 = Profile(
        id="user1",
        discord_id="user1",
        display_name="User 1",
        neurotype=Neurotype.DEVELOPER,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location=""
    )

    user2 = Profile(
        id="user2",
        discord_id="user2",
        display_name="User 2",
        neurotype=Neurotype.FABRICANT,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location=""
    )

    score = matcher.calculate_neurotype_score(user1, user2)
    # Developer and Fabricant should have high compatibility (0.85)
    assert score == 0.85


def test_project_alignment_score():
    """Test project alignment scoring"""
    matcher = NeurotypeMatcher([])

    user1 = Profile(
        id="user1",
        discord_id="user1",
        display_name="User 1",
        neurotype=Neurotype.DEVELOPER,
        skills=[],
        offering=[],
        looking_for=[],
        projects=["ZIMA Platform", "Open Source"],
        location=""
    )

    user2 = Profile(
        id="user2",
        discord_id="user2",
        display_name="User 2",
        neurotype=Neurotype.ARTISAN,
        skills=[],
        offering=[],
        looking_for=[],
        projects=["ZIMA Platform", "Design System"],
        location=""
    )

    score = matcher.calculate_project_score(user1, user2)
    # Should have score based on shared project (ZIMA Platform)
    assert 0.0 <= score <= 1.0
    assert score > 0.0  # Should be > 0 due to shared project


def test_location_score():
    """Test location proximity scoring"""
    matcher = NeurotypeMatcher([])

    user1 = Profile(
        id="user1",
        discord_id="user1",
        display_name="User 1",
        neurotype=Neurotype.DEVELOPER,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location="New York"
    )

    user2 = Profile(
        id="user2",
        discord_id="user2",
        display_name="User 2",
        neurotype=Neurotype.ARTISAN,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location="New York"
    )

    score = matcher.calculate_location_score(user1, user2)
    # Same location should give high score
    assert score == 1.0


def test_comprehensive_match_score():
    """Test comprehensive match scoring"""
    matcher = NeurotypeMatcher([])

    user1 = Profile(
        id="user1",
        discord_id="user1",
        display_name="User 1",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=["Backend development"],
        looking_for=["UI design"],
        projects=["ZIMA"],
        location="New York"
    )

    user2 = Profile(
        id="user2",
        discord_id="user2",
        display_name="User 2",
        neurotype=Neurotype.FABRICANT,
        skills=["JavaScript"],
        offering=["UI design"],
        looking_for=["Backend development"],
        projects=["ZIMA"],
        location="New York"
    )

    score = matcher.calculate_match_score(user1, user2)

    # Check that we get a breakdown
    assert "total" in score
    assert "breakdown" in score
    assert "skill_score" in score["breakdown"]
    assert "neurotype_score" in score["breakdown"]
    assert "project_score" in score["breakdown"]
    assert "location_score" in score["breakdown"]

    # Total should be weighted average
    total = score["total"]
    assert 0.0 <= total <= 1.0


def test_find_top_matches():
    """Test finding top matches"""
    # Create test profiles
    profiles = []

    # User 0 - Developer
    profiles.append(Profile(
        id="user0",
        discord_id="user0",
        display_name="Developer User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python", "JavaScript"],
        offering=["Backend development"],
        looking_for=["UI design"],
        projects=["ZIMA"],
        location="New York"
    ))

    # User 1 - Fabricant (high compatibility with Developer)
    profiles.append(Profile(
        id="user1",
        discord_id="user1",
        display_name="Fabricant User",
        neurotype=Neurotype.FABRICANT,
        skills=["Hardware", "Electronics"],
        offering=["Prototyping"],
        looking_for=["Software"],
        projects=["ZIMA"],
        location="New York"
    ))

    # User 2 - Artisan (medium compatibility)
    profiles.append(Profile(
        id="user2",
        discord_id="user2",
        display_name="Artisan User",
        neurotype=Neurotype.ARTISAN,
        skills=["Design", "UI/UX"],
        offering=["UI design"],
        looking_for=["Backend"],
        projects=["Design System"],
        location="Boston"
    ))

    matcher = NeurotypeMatcher(profiles)
    top_matches = matcher.find_top_matches("user0", limit=2)

    # Should return 2 matches
    assert len(top_matches) == 2

    # First match should be user1 (Fabricant - higher compatibility)
    assert top_matches[0]["profile"].id == "user1"
    assert top_matches[0]["score"]["total"] > 0.5

    # Second match should be user2 (Artisan - medium compatibility)
    assert top_matches[1]["profile"].id == "user2"
    assert top_matches[1]["score"]["total"] > 0.4


def test_search_profiles():
    """Test profile search functionality"""
    profiles = [
        Profile(
            id="user1",
            discord_id="user1",
            display_name="John Developer",
            neurotype=Neurotype.DEVELOPER,
            skills=["Python", "JavaScript"],
            offering=[],
            looking_for=[],
            projects=["ZIMA"],
            location="New York"
        ),
        Profile(
            id="user2",
            discord_id="user2",
            display_name="Jane Designer",
            neurotype=Neurotype.ARTISAN,
            skills=["Design", "UI/UX"],
            offering=[],
            looking_for=[],
            projects=["Design"],
            location="Boston"
        ),
        Profile(
            id="user3",
            discord_id="user3",
            display_name="Bob Builder",
            neurotype=Neurotype.FABRICANT,
            skills=["Hardware", "Electronics"],
            offering=[],
            looking_for=[],
            projects=["Hardware"],
            location="San Francisco"
        )
    ]

    matcher = NeurotypeMatcher(profiles)

    # Search by name
    results = matcher.search_profiles("John")
    assert len(results) == 1
    assert results[0].display_name == "John Developer"

    # Search by skill
    results = matcher.search_profiles("Design")
    assert len(results) == 1
    assert results[0].display_name == "Jane Designer"

    # Search by location
    results = matcher.search_profiles("York")
    assert len(results) == 1
    assert results[0].display_name == "John Developer"

    # Search by project
    results = matcher.search_profiles("ZIMA")
    assert len(results) == 1
    assert results[0].display_name == "John Developer"


def test_get_profile_by_id():
    """Test getting profile by ID"""
    profiles = [
        Profile(
            id="user1",
            discord_id="user1",
            display_name="Test User",
            neurotype=Neurotype.DEVELOPER,
            skills=[],
            offering=[],
            looking_for=[],
            projects=[],
            location=""
        )
    ]

    matcher = NeurotypeMatcher(profiles)

    profile = matcher.get_profile_by_id("user1")
    assert profile is not None
    assert profile.id == "user1"

    # Non-existent ID
    profile = matcher.get_profile_by_id("nonexistent")
    assert profile is None


def test_get_profile_by_discord_id():
    """Test getting profile by Discord ID"""
    profiles = [
        Profile(
            id="user1",
            discord_id="discord123",
            display_name="Test User",
            neurotype=Neurotype.DEVELOPER,
            skills=[],
            offering=[],
            looking_for=[],
            projects=[],
            location=""
        )
    ]

    matcher = NeurotypeMatcher(profiles)

    profile = matcher.get_profile_by_discord_id("discord123")
    assert profile is not None
    assert profile.discord_id == "discord123"

    # Non-existent Discord ID
    profile = matcher.get_profile_by_discord_id("nonexistent")
    assert profile is None


def test_find_matches_by_neurotype():
    """Test finding profiles by neurotype"""
    profiles = [
        Profile(
            id="user1",
            discord_id="user1",
            display_name="Developer 1",
            neurotype=Neurotype.DEVELOPER,
            skills=[],
            offering=[],
            looking_for=[],
            projects=[],
            location=""
        ),
        Profile(
            id="user2",
            discord_id="user2",
            display_name="Developer 2",
            neurotype=Neurotype.DEVELOPER,
            skills=[],
            offering=[],
            looking_for=[],
            projects=[],
            location=""
        ),
        Profile(
            id="user3",
            discord_id="user3",
            display_name="Artisan",
            neurotype=Neurotype.ARTISAN,
            skills=[],
            offering=[],
            looking_for=[],
            projects=[],
            location=""
        )
    ]

    matcher = NeurotypeMatcher(profiles)

    # Find developers
    results = matcher.find_matches_by_neurotype(Neurotype.DEVELOPER)
    assert len(results) == 2
    assert all(p.neurotype == Neurotype.DEVELOPER for p in results)

    # Find artisans
    results = matcher.find_matches_by_neurotype(Neurotype.ARTISAN)
    assert len(results) == 1
    assert results[0].neurotype == Neurotype.ARTISAN
