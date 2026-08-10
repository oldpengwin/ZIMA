"""
Test profile manager with database operations
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
import os
import uuid

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.profile_manager import ProfileManager, ProfileNotFoundError, DatabaseError
from core.neurotype_matcher import Profile, Neurotype


@pytest.fixture
def mock_db_connection():
    """Fixture to mock database connection"""
    with patch('psycopg2.extras.RealDictConnectionPool') as mock_pool:
        mock_conn = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn
        mock_pool.return_value.putconn.return_value = None
        yield mock_pool


def test_profile_manager_initialization(mock_db_connection):
    """Test profile manager initialization"""
    # Should not raise exception
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")
    assert manager.db_url == "postgresql://user:pass@localhost/db"


def test_create_profile(mock_db_connection):
    """Test profile creation"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    profile_data = {
        "discord_id": "test-user",
        "display_name": "Test User",
        "neurotype": "developer",
        "skills": ["Python", "JavaScript"],
        "offering": ["Backend development"],
        "looking_for": ["Frontend developers"],
        "projects": ["ZIMA Platform"],
        "location": "Test City",
        "is_open": True
    }

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [{
        "id": str(uuid.uuid4()),
        "discord_id": "test-user",
        "display_name": "Test User",
        "neurotype": "developer",
        "skills": ["Python", "JavaScript"],
        "offering": ["Backend development"],
        "looking_for": ["Frontend developers"],
        "projects": ["ZIMA Platform"],
        "location": "Test City",
        "is_open": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profile = manager.create_profile(profile_data)

        assert profile is not None
        assert profile.discord_id == "test-user"
        assert profile.display_name == "Test User"
        assert profile.neurotype == Neurotype.DEVELOPER


def test_create_profile_missing_required_fields():
    """Test profile creation with missing required fields"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Missing discord_id
    with pytest.raises(ValueError, match="Missing required field: discord_id"):
        manager.create_profile({
            "display_name": "Test User",
            "neurotype": "developer"
        })

    # Missing display_name
    with pytest.raises(ValueError, match="Missing required field: display_name"):
        manager.create_profile({
            "discord_id": "test-user",
            "neurotype": "developer"
        })

    # Missing neurotype
    with pytest.raises(ValueError, match="Missing required field: neurotype"):
        manager.create_profile({
            "discord_id": "test-user",
            "display_name": "Test User"
        })


def test_create_profile_invalid_neurotype():
    """Test profile creation with invalid neurotype"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    with pytest.raises(ValueError, match="Invalid neurotype: invalid_type"):
        manager.create_profile({
            "discord_id": "test-user",
            "display_name": "Test User",
            "neurotype": "invalid_type"
        })


def test_get_profile_by_id(mock_db_connection):
    """Test getting profile by ID"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [{
        "id": "test-id",
        "discord_id": "test-user",
        "display_name": "Test User",
        "neurotype": "developer",
        "skills": ["Python"],
        "offering": [],
        "looking_for": [],
        "projects": [],
        "location": "Test City",
        "is_open": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profile = manager.get_profile_by_id("test-id")

        assert profile is not None
        assert profile.id == "test-id"
        assert profile.display_name == "Test User"


def test_get_profile_by_id_not_found(mock_db_connection):
    """Test getting non-existent profile by ID"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query - no results
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profile = manager.get_profile_by_id("nonexistent-id")

        assert profile is None


def test_get_profile_by_discord_id(mock_db_connection):
    """Test getting profile by Discord ID"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [{
        "id": "test-id",
        "discord_id": "discord-123",
        "display_name": "Test User",
        "neurotype": "developer",
        "skills": ["Python"],
        "offering": [],
        "looking_for": [],
        "projects": [],
        "location": "Test City",
        "is_open": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profile = manager.get_profile_by_discord_id("discord-123")

        assert profile is not None
        assert profile.discord_id == "discord-123"


def test_get_profile_by_discord_id_not_found(mock_db_connection):
    """Test getting non-existent profile by Discord ID"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query - no results
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profile = manager.get_profile_by_discord_id("nonexistent-discord-id")

        assert profile is None


def test_update_profile(mock_db_connection):
    """Test profile update"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [{
        "id": "test-id",
        "discord_id": "test-user",
        "display_name": "Updated Name",
        "neurotype": "developer",
        "skills": ["Python", "JavaScript"],
        "offering": [],
        "looking_for": [],
        "projects": [],
        "location": "Updated City",
        "is_open": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-02T00:00:00"
    }]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # Mock get_profile_by_id to return a profile
        with patch.object(manager, 'get_profile_by_id') as mock_get:
            mock_get.return_value = Profile(
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

            updates = {
                "display_name": "Updated Name",
                "skills": ["Python", "JavaScript"],
                "location": "Updated City"
            }

            updated_profile = manager.update_profile("test-id", updates)

            assert updated_profile is not None
            assert updated_profile.display_name == "Updated Name"
            assert updated_profile.location == "Updated City"


def test_update_profile_not_found():
    """Test updating non-existent profile"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock get_profile_by_id to return None
    with patch.object(manager, 'get_profile_by_id') as mock_get:
        mock_get.return_value = None

        with pytest.raises(ProfileNotFoundError, match="Profile test-id not found"):
            manager.update_profile("test-id", {"display_name": "Updated"})


def test_delete_profile(mock_db_connection):
    """Test profile deletion"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # Mock get_profile_by_id to return a profile
        with patch.object(manager, 'get_profile_by_id') as mock_get:
            mock_get.return_value = Profile(
                id="test-id",
                discord_id="test-user",
                display_name="Test User",
                neurotype=Neurotype.DEVELOPER,
                skills=[],
                offering=[],
                looking_for=[],
                projects=[],
                location=""
            )

            result = manager.delete_profile("test-id")
            assert result is True


def test_delete_profile_not_found():
    """Test deleting non-existent profile"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock get_profile_by_id to return None
    with patch.object(manager, 'get_profile_by_id') as mock_get:
        mock_get.return_value = None

        result = manager.delete_profile("nonexistent-id")
        assert result is False


def test_get_all_profiles(mock_db_connection):
    """Test getting all profiles"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [
        {
            "id": "test-id-1",
            "discord_id": "test-user-1",
            "display_name": "Test User 1",
            "neurotype": "developer",
            "skills": ["Python"],
            "offering": [],
            "looking_for": [],
            "projects": [],
            "location": "City 1",
            "is_open": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        },
        {
            "id": "test-id-2",
            "discord_id": "test-user-2",
            "display_name": "Test User 2",
            "neurotype": "artisan",
            "skills": ["Design"],
            "offering": [],
            "looking_for": [],
            "projects": [],
            "location": "City 2",
            "is_open": True,
            "created_at": "2024-01-02T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profiles = manager.get_all_profiles()

        assert len(profiles) == 2
        assert profiles[0].display_name == "Test User 1"
        assert profiles[1].display_name == "Test User 2"


def test_get_all_profiles_with_limit(mock_db_connection):
    """Test getting all profiles with limit"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [
        {
            "id": "test-id-1",
            "discord_id": "test-user-1",
            "display_name": "Test User 1",
            "neurotype": "developer",
            "skills": [],
            "offering": [],
            "looking_for": [],
            "projects": [],
            "location": "",
            "is_open": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profiles = manager.get_all_profiles(limit=1)

        assert len(profiles) == 1


def test_search_profiles(mock_db_connection):
    """Test profile search"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the database query
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [
        {
            "id": "test-id",
            "discord_id": "test-user",
            "display_name": "Test User",
            "neurotype": "developer",
            "skills": ["Python"],
            "offering": [],
            "looking_for": [],
            "projects": [],
            "location": "Test City",
            "is_open": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch.object(manager, '_get_connection') as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        profiles = manager.search_profiles("Test", limit=10)

        assert len(profiles) == 1
        assert profiles[0].display_name == "Test User"


def test_row_to_profile_conversion():
    """Test database row to profile conversion"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    row = {
        "id": "test-id",
        "discord_id": "test-user",
        "display_name": "Test User",
        "neurotype": "developer",
        "skills": ["Python", "JavaScript"],
        "offering": ["Backend"],
        "looking_for": ["Frontend"],
        "projects": ["ZIMA"],
        "location": "Test City",
        "is_open": True
    }

    profile = manager._row_to_profile(row)

    assert profile.id == "test-id"
    assert profile.discord_id == "test-user"
    assert profile.display_name == "Test User"
    assert profile.neurotype == Neurotype.DEVELOPER
    assert profile.skills == ["Python", "JavaScript"]
    assert profile.offering == ["Backend"]
    assert profile.looking_for == ["Frontend"]
    assert profile.projects == ["ZIMA"]
    assert profile.location == "Test City"
    assert profile.is_open is True


def test_close_connection():
    """Test closing database connections"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the connection pool
    mock_pool = MagicMock()
    manager._connection_pool = mock_pool

    manager.close()

    mock_pool.closeall.assert_called_once()


def test_context_manager():
    """Test profile manager as context manager"""
    manager = ProfileManager(db_url="postgresql://user:pass@localhost/db")

    # Mock the connection pool
    mock_pool = MagicMock()
    manager._connection_pool = mock_pool

    with manager as m:
        assert m is manager

    mock_pool.closeall.assert_called_once()
