"""
Profile Manager for ZIMA Platform

DEPRECATED as of the backend-rebuild pass: the FastAPI backend (src/api/routes.py)
now uses the SQLAlchemy-based src/services/*.py layer instead of this raw-psycopg2
implementation. This file is kept only because src/bot/cogs/matching.py (a second,
unwired Python Discord bot — see zima_codebase_audit memory) still imports it, and
that bot's fate (retire vs. reconcile with the Node bot) is a decision flagged for
Frost rather than something to resolve unilaterally here. Do not build new features
against this module — use src/services/ instead.

Handles CRUD operations for user profiles with PostgreSQL database.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as _connection
from psycopg2.errors import UniqueViolation, ForeignKeyViolation

from .neurotype_matcher import Profile, Neurotype


class DatabaseError(Exception):
    """Base database exception"""
    pass


class ProfileNotFoundError(DatabaseError):
    """Profile not found exception"""
    pass


class ProfileManager:
    """
    Profile management with PostgreSQL backend

    Handles all CRUD operations for user profiles with proper
    error handling, transaction management, and connection pooling.
    """

    def __init__(self, db_url: str, pool_min: int = 1, pool_max: int = 10):
        """
        Initialize profile manager with database connection

        Args:
            db_url: PostgreSQL connection string
            pool_min: Minimum connections in pool
            pool_max: Maximum connections in pool

        Raises:
            DatabaseError: If connection fails
        """
        self.db_url = db_url
        self.pool_min = pool_min
        self.pool_max = pool_max
        self.logger = logging.getLogger(__name__)

        # Initialize connection pool
        self._connection_pool = extras.RealDictConnectionPool(
            minconn=pool_min,
            maxconn=pool_max,
            dsn=db_url
        )

        # Test connection
        try:
            with self._get_connection() as conn:
                self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")

    @contextmanager
    def _get_connection(self) -> _connection:
        """Get database connection from pool"""
        conn = self._connection_pool.getconn()
        try:
            yield conn
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            self._connection_pool.putconn(conn)

    def _execute_query(self, query: sql.Composed, params: tuple = None, fetch: bool = False) -> Any:
        """
        Execute SQL query with proper error handling

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results if fetch=True, None otherwise

        Raises:
            DatabaseError: On query execution errors
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if fetch:
                        return cursor.fetchall()
                    conn.commit()
        except UniqueViolation as e:
            self.logger.warning(f"Unique constraint violation: {e}")
            raise DatabaseError(f"Duplicate entry: {e}")
        except ForeignKeyViolation as e:
            self.logger.warning(f"Foreign key violation: {e}")
            raise DatabaseError(f"Referential integrity violation: {e}")
        except psycopg2.Error as e:
            self.logger.error(f"Database query error: {e}")
            raise DatabaseError(f"Query execution failed: {e}")

    def create_profile(self, profile_data: Dict[str, Any]) -> Profile:
        """
        Create a new profile

        Args:
            profile_data: Dictionary containing profile data

        Returns:
            Created Profile object

        Raises:
            ValueError: If profile data is invalid
            DatabaseError: If database operation fails
        """
        # Validate required fields
        required_fields = ['discord_id', 'display_name', 'neurotype']
        for field in required_fields:
            if field not in profile_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate neurotype
        try:
            neurotype = Neurotype(profile_data['neurotype'])
        except ValueError:
            raise ValueError(f"Invalid neurotype: {profile_data['neurotype']}")

        # Generate ID and timestamps
        profile_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Build profile object
        profile = Profile(
            id=profile_id,
            discord_id=profile_data['discord_id'],
            display_name=profile_data['display_name'],
            neurotype=neurotype,
            skills=profile_data.get('skills', []),
            offering=profile_data.get('offering', []),
            looking_for=profile_data.get('looking_for', []),
            projects=profile_data.get('projects', []),
            location=profile_data.get('location'),
            is_open=profile_data.get('is_open', True)
        )

        # Insert into database
        query = sql.SQL("""
            INSERT INTO profiles (
                id, discord_id, display_name, neurotype,
                skills, offering, looking_for, projects,
                location, is_open, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """)

        result = self._execute_query(
            query,
            (
                profile.id,
                profile.discord_id,
                profile.display_name,
                profile.neurotype.value,
                profile.skills,
                profile.offering,
                profile.looking_for,
                profile.projects,
                profile.location,
                profile.is_open,
                now,
                now
            ),
            fetch=True
        )

        if not result:
            raise DatabaseError("Failed to create profile")

        return self._row_to_profile(result[0])

    def get_profile_by_id(self, profile_id: str) -> Optional[Profile]:
        """
        Get profile by ID

        Args:
            profile_id: Profile ID

        Returns:
            Profile object if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        query = sql.SQL("SELECT * FROM profiles WHERE id = %s")
        result = self._execute_query(query, (profile_id,), fetch=True)

        if not result:
            return None

        return self._row_to_profile(result[0])

    def get_profile_by_discord_id(self, discord_id: str) -> Optional[Profile]:
        """
        Get profile by Discord ID

        Args:
            discord_id: Discord user ID

        Returns:
            Profile object if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        query = sql.SQL("SELECT * FROM profiles WHERE discord_id = %s")
        result = self._execute_query(query, (discord_id,), fetch=True)

        if not result:
            return None

        return self._row_to_profile(result[0])

    def update_profile(self, profile_id: str, updates: Dict[str, Any]) -> Profile:
        """
        Update profile

        Args:
            profile_id: Profile ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated Profile object

        Raises:
            ProfileNotFoundError: If profile not found
            ValueError: If update data is invalid
            DatabaseError: If database operation fails
        """
        # Get current profile
        current_profile = self.get_profile_by_id(profile_id)
        if not current_profile:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")

        # Validate neurotype if being updated
        if 'neurotype' in updates:
            try:
                Neurotype(updates['neurotype'])
            except ValueError:
                raise ValueError(f"Invalid neurotype: {updates['neurotype']}")

        # Build update query dynamically
        set_clauses = []
        params = []
        param_index = 1

        for field, value in updates.items():
            if field == 'neurotype' and value:
                set_clauses.append(sql.SQL("neurotype = %s"))
                params.append(Neurotype(value).value)
            elif field == 'is_open':
                set_clauses.append(sql.SQL("is_open = %s"))
                params.append(bool(value))
            elif field in ['skills', 'offering', 'looking_for', 'projects']:
                set_clauses.append(sql.SQL(f"{field} = %s"))
                params.append(value or [])
            elif field in ['display_name', 'location', 'bio']:
                set_clauses.append(sql.SQL(f"{field} = %s"))
                params.append(value)

        if not set_clauses:
            return current_profile

        # Add updated_at timestamp
        set_clauses.append(sql.SQL("updated_at = %s"))
        params.append(datetime.utcnow())
        param_index += 1

        query = sql.SQL("""
            UPDATE profiles
            SET {set_clauses}
            WHERE id = %s
            RETURNING *
        """).format(set_clauses=sql.SQL(', ').join(set_clauses))

        params.append(profile_id)

        result = self._execute_query(query, tuple(params), fetch=True)

        if not result:
            raise DatabaseError("Failed to update profile")

        return self._row_to_profile(result[0])

    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete profile

        Args:
            profile_id: Profile ID to delete

        Returns:
            True if successful, False if profile not found

        Raises:
            DatabaseError: If database operation fails
        """
        # Check if profile exists
        if not self.get_profile_by_id(profile_id):
            return False

        query = sql.SQL("DELETE FROM profiles WHERE id = %s")
        self._execute_query(query, (profile_id,))

        return True

    def get_all_profiles(self, limit: int = None, offset: int = 0) -> List[Profile]:
        """
        Get all profiles

        Args:
            limit: Maximum number of profiles to return
            offset: Offset for pagination

        Returns:
            List of Profile objects

        Raises:
            DatabaseError: If database operation fails
        """
        query = sql.SQL("SELECT * FROM profiles ORDER BY created_at DESC")
        params = ()

        if limit is not None:
            query = sql.SQL("SELECT * FROM profiles ORDER BY created_at DESC LIMIT %s OFFSET %s")
            params = (limit, offset)

        result = self._execute_query(query, params, fetch=True)

        return [self._row_to_profile(row) for row in result]

    def search_profiles(self, query: str, limit: int = 10, offset: int = 0) -> List[Profile]:
        """
        Search profiles by name, skills, or location

        Args:
            query: Search term
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching Profile objects

        Raises:
            DatabaseError: If database operation fails
        """
        search_query = sql.SQL("""
            SELECT * FROM profiles
            WHERE
                display_name ILIKE %s OR
                location ILIKE %s OR
                EXISTS (SELECT 1 FROM unnest(skills) AS skill WHERE skill ILIKE %s) OR
                EXISTS (SELECT 1 FROM unnest(projects) AS project WHERE project ILIKE %s)
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """)

        search_term = f"%{query}%"
        params = (search_term, search_term, search_term, search_term, limit, offset)

        result = self._execute_query(search_query, params, fetch=True)

        return [self._row_to_profile(row) for row in result]

    def _row_to_profile(self, row: Dict[str, Any]) -> Profile:
        """Convert database row to Profile object"""
        return Profile(
            id=str(row['id']),
            discord_id=row['discord_id'],
            display_name=row['display_name'],
            neurotype=Neurotype(row['neurotype']),
            skills=row['skills'] or [],
            offering=row['offering'] or [],
            looking_for=row['looking_for'] or [],
            projects=row['projects'] or [],
            location=row['location'],
            is_open=row['is_open']
        )

    def close(self) -> None:
        """Close all database connections"""
        self._connection_pool.closeall()
        self.logger.info("Database connections closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()