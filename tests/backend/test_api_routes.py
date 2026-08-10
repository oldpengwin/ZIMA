"""
Test API routes for ZIMA backend
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from main import app
from api.routes import get_profile_manager
from core.profile_manager import ProfileManager
from core.neurotype_matcher import Profile, Neurotype


client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "zima-api"
    assert data["version"] == "1.0.0"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert "health" in data


@patch('api.routes.ProfileManager')
def test_create_profile(MockProfileManager):
    """Test profile creation"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    mock_profile = Profile(
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
    mock_manager.create_profile.return_value = mock_profile
    MockProfileManager.return_value = mock_manager

    # Mock authentication
    from api.routes import get_current_user, TokenData
    with patch('api.routes.get_current_user') as mock_current_user:
        mock_current_user.return_value = TokenData(discord_id="test-user", username="testuser")

        response = client.post(
            "/api/v1/profiles",
            json={
                "discord_id": "test-user",
                "display_name": "Test User",
                "neurotype": "developer",
                "skills": ["Python", "JavaScript"],
                "offering": ["Backend development"],
                "looking_for": ["Frontend developers"],
                "projects": ["ZIMA Platform"],
                "location": "Test City"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Test User"
        assert data["neurotype"] == "developer"


@patch('api.routes.ProfileManager')
def test_get_profile(MockProfileManager):
    """Test getting a profile"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    mock_profile = Profile(
        id="test-id",
        discord_id="test-user",
        display_name="Test User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=[],
        looking_for=[],
        projects=[],
        location="Test City"
    )
    mock_manager.get_profile_by_id.return_value = mock_profile
    MockProfileManager.return_value = mock_manager

    response = client.get("/api/v1/profiles/test-id")
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Test User"


@patch('api.routes.ProfileManager')
def test_get_my_profile(MockProfileManager):
    """Test getting current user's profile"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    mock_profile = Profile(
        id="test-id",
        discord_id="test-user",
        display_name="Test User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=[],
        looking_for=[],
        projects=[],
        location="Test City"
    )
    mock_manager.get_profile_by_discord_id.return_value = mock_profile
    MockProfileManager.return_value = mock_manager

    # Mock authentication
    from api.routes import get_current_user, TokenData
    with patch('api.routes.get_current_user') as mock_current_user:
        mock_current_user.return_value = TokenData(discord_id="test-user", username="testuser")

        response = client.get("/api/v1/profiles/me")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test User"


@patch('api.routes.ProfileManager')
def test_search_profiles(MockProfileManager):
    """Test profile search"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    mock_profile = Profile(
        id="test-id",
        discord_id="test-user",
        display_name="Test User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=[],
        looking_for=[],
        projects=[],
        location="Test City"
    )
    mock_manager.search_profiles.return_value = [mock_profile]
    MockProfileManager.return_value = mock_manager

    response = client.get("/api/v1/profiles?q=test")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Test User"


@patch('api.routes.ProfileManager')
def test_find_matches(MockProfileManager):
    """Test finding matches"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    user_profile = Profile(
        id="user-id",
        discord_id="user",
        display_name="User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=["Development"],
        looking_for=["Designers"],
        projects=[],
        location="City"
    )
    match_profile = Profile(
        id="match-id",
        discord_id="match",
        display_name="Match",
        neurotype=Neurotype.ARTISAN,
        skills=["Design"],
        offering=["UI/UX"],
        looking_for=["Developers"],
        projects=[],
        location="City"
    )

    mock_manager.get_profile_by_id.return_value = user_profile
    mock_manager.get_all_profiles.return_value = [user_profile, match_profile]
    MockProfileManager.return_value = mock_manager

    # Mock authentication
    from api.routes import get_current_user, TokenData
    with patch('api.routes.get_current_user') as mock_current_user:
        mock_current_user.return_value = TokenData(discord_id="user", username="user")

        response = client.get("/api/v1/match/user-id")
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) > 0


@patch('api.routes.ProfileManager')
def test_request_connection(MockProfileManager):
    """Test connection request"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    from_profile = Profile(
        id="from-id",
        discord_id="from-user",
        display_name="From User",
        neurotype=Neurotype.DEVELOPER,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location=""
    )
    to_profile = Profile(
        id="to-id",
        discord_id="to-user",
        display_name="To User",
        neurotype=Neurotype.ARTISAN,
        skills=[],
        offering=[],
        looking_for=[],
        projects=[],
        location=""
    )

    mock_manager.get_profile_by_discord_id.side_effect = lambda x: from_profile if x == "from-user" else to_profile
    mock_manager.get_profile_by_id.return_value = to_profile
    MockProfileManager.return_value = mock_manager

    # Mock authentication
    from api.routes import get_current_user, TokenData
    with patch('api.routes.get_current_user') as mock_current_user:
        mock_current_user.return_value = TokenData(discord_id="from-user", username="fromuser")

        response = client.post(
            "/api/v1/match/request",
            json={"to_user_id": "to-id", "message": "Hello!"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"


@patch('api.routes.ProfileManager')
def test_update_profile(MockProfileManager):
    """Test profile update"""
    # Setup mock
    mock_manager = MagicMock(spec=ProfileManager)
    mock_profile = Profile(
        id="test-id",
        discord_id="test-user",
        display_name="Test User",
        neurotype=Neurotype.DEVELOPER,
        skills=["Python"],
        offering=[],
        looking_for=[],
        projects=[],
        location="Test City"
    )
    mock_manager.get_profile_by_id.return_value = mock_profile
    mock_manager.update_profile.return_value = mock_profile
    MockProfileManager.return_value = mock_manager

    # Mock authentication
    from api.routes import get_current_user, TokenData
    with patch('api.routes.get_current_user') as mock_current_user:
        mock_current_user.return_value = TokenData(discord_id="test-user", username="testuser")

        response = client.put(
            "/api/v1/profiles/test-id",
            json={"display_name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test User"


def test_get_neurotypes():
    """Test getting neurotypes"""
    response = client.get("/api/v1/neurotypes")
    assert response.status_code == 200
    data = response.json()
    assert "neurotypes" in data
    assert len(data["neurotypes"]) == 10  # 10 neurotypes
    assert "seedcaster" in data["neurotypes"]
    assert "fabricant" in data["neurotypes"]


def test_token_endpoint():
    """Test token endpoint"""
    response = client.post(
        "/api/v1/token",
        data={"username": "testuser", "password": "testpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
