"""
FastAPI Routes for ZIMA Platform

RESTful API endpoints with authentication and validation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging

from ..core.profile_manager import ProfileManager, ProfileNotFoundError
from ..core.neurotype_matcher import Profile, Neurotype
from ..database.models import Profile as DBProfile


# Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Logger
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1")


class TokenData:
    discord_id: str
    username: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        discord_id: str = payload.get("sub")
        username: str = payload.get("username")
        if discord_id is None or username is None:
            raise credentials_exception
        return TokenData(discord_id=discord_id, username=username)
    except JWTError:
        raise credentials_exception


def get_profile_manager() -> ProfileManager:
    """Get profile manager instance"""
    # In production, this would use dependency injection
    # For now, we'll create a new instance
    return ProfileManager(db_url="postgresql://user:password@localhost/zima")


@router.post("/token", response_model=Dict[str, str])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """
    OAuth2 compatible token login endpoint

    Args:
        form_data: OAuth2 password form data

    Returns:
        Access token dictionary

    Raises:
        HTTPException: If authentication fails
    """
    # In a real implementation, this would verify against Discord OAuth
    # For now, we'll use a mock user
    user = {
        "discord_id": "mock_user_id",
        "username": form_data.username,
        "hashed_password": get_password_hash("mock_password")
    }

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["discord_id"], "username": user["username"]},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/profiles", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Create a new profile

    Args:
        profile_data: Profile data dictionary
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Created profile dictionary

    Raises:
        HTTPException: If profile creation fails
    """
    try:
        # Ensure user can only create their own profile
        if profile_data.get("discord_id") != current_user.discord_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create profile for yourself"
            )

        profile_data["discord_id"] = current_user.discord_id
        profile_data["discord_username"] = current_user.username

        profile = profile_manager.create_profile(profile_data)
        return profile.to_dict()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Profile creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile"
        )


@router.get("/profiles/me", response_model=Dict[str, Any])
async def get_my_profile(
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Get current user's profile

    Args:
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Profile dictionary

    Raises:
        HTTPException: If profile not found
    """
    profile = profile_manager.get_profile_by_discord_id(current_user.discord_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile.to_dict()


@router.get("/profiles/{profile_id}", response_model=Dict[str, Any])
async def get_profile(
    profile_id: str,
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Get profile by ID

    Args:
        profile_id: Profile ID
        profile_manager: Profile manager instance

    Returns:
        Profile dictionary

    Raises:
        HTTPException: If profile not found
    """
    profile = profile_manager.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile.to_dict()


@router.put("/profiles/{profile_id}", response_model=Dict[str, Any])
async def update_profile(
    profile_id: str,
    updates: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Update profile

    Args:
        profile_id: Profile ID to update
        updates: Dictionary of fields to update
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Updated profile dictionary

    Raises:
        HTTPException: If update fails
    """
    try:
        profile = profile_manager.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        # Ensure user can only update their own profile
        if profile.discord_id != current_user.discord_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own profile"
            )

        updated_profile = profile_manager.update_profile(profile_id, updates)
        return updated_profile.to_dict()

    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/profiles", response_model=List[Dict[str, Any]])
async def search_profiles(
    q: Optional[str] = Query(None, min_length=2),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> List[Dict[str, Any]]:
    """
    Search profiles

    Args:
        q: Search query
        limit: Maximum results
        offset: Pagination offset
        profile_manager: Profile manager instance

    Returns:
        List of matching profiles
    """
    if q:
        profiles = profile_manager.search_profiles(q, limit, offset)
    else:
        profiles = profile_manager.get_all_profiles(limit, offset)

    return [profile.to_dict() for profile in profiles]


@router.get("/match/{user_id}", response_model=Dict[str, Any])
async def find_matches(
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Find matches for a user

    Args:
        user_id: User ID to find matches for
        limit: Maximum number of matches
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Dictionary with matches and metadata

    Raises:
        HTTPException: If user not found or unauthorized
    """
    try:
        # Get user profile
        user_profile = profile_manager.get_profile_by_id(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Ensure user can only find matches for themselves
        if user_profile.discord_id != current_user.discord_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only find matches for yourself"
            )

        # Get all profiles for matching
        all_profiles = profile_manager.get_all_profiles()

        # Create matcher and find top matches
        from ..core.neurotype_matcher import NeurotypeMatcher
        matcher = NeurotypeMatcher(all_profiles)
        matches = matcher.find_top_matches(user_id, limit)

        # Format response
        formatted_matches = []
        for match in matches:
            formatted_matches.append({
                "profile": match["profile"].to_dict(),
                "score": match["score"]
            })

        return {
            "user_id": user_id,
            "matches": formatted_matches,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Match finding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find matches"
        )


@router.post("/match/request", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def request_connection(
    request_data: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Request connection with another user

    Args:
        request_data: Connection request data
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Created connection request

    Raises:
        HTTPException: If request fails
    """
    try:
        to_user_id = request_data.get("to_user_id")
        message = request_data.get("message", "")

        if not to_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="to_user_id is required"
            )

        # Get both profiles
        from_profile = profile_manager.get_profile_by_discord_id(current_user.discord_id)
        to_profile = profile_manager.get_profile_by_id(to_user_id)

        if not from_profile or not to_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both profiles not found"
            )

        # In a real implementation, this would create a database record
        # For now, we'll simulate it
        connection_request = {
            "id": str(uuid.uuid4()),
            "from_user_id": str(from_profile.id),
            "to_user_id": str(to_profile.id),
            "status": "pending",
            "message": message,
            "created_at": datetime.utcnow().isoformat()
        }

        return connection_request

    except Exception as e:
        logger.error(f"Connection request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create connection request"
        )


@router.get("/match/{user_id}/requests", response_model=Dict[str, Any])
async def get_connection_requests(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    profile_manager: ProfileManager = Depends(get_profile_manager)
) -> Dict[str, Any]:
    """
    Get connection requests for a user

    Args:
        user_id: User ID
        current_user: Current authenticated user
        profile_manager: Profile manager instance

    Returns:
        Dictionary with connection requests

    Raises:
        HTTPException: If user not found or unauthorized
    """
    try:
        # Get user profile
        user_profile = profile_manager.get_profile_by_id(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Ensure user can only get their own requests
        if user_profile.discord_id != current_user.discord_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only get your own connection requests"
            )

        # In a real implementation, this would query the database
        # For now, return empty array
        return {
            "user_id": user_id,
            "requests": [],
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get connection requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get connection requests"
        )


@router.get("/neurotypes", response_model=Dict[str, Any])
async def get_neurotypes() -> Dict[str, Any]:
    """
    Get all neurotypes with descriptions

    Returns:
        Dictionary of neurotypes
    """
    neurotypes = {}
    for neurotype in Neurotype:
        neurotypes[neurotype.value] = {
            "id": neurotype.value,
            "name": neurotype.name,
            "description": get_neurotype_description(neurotype)
        }

    return {"neurotypes": neurotypes}


def get_neurotype_description(neurotype: Neurotype) -> str:
    """Get description for neurotype"""
    descriptions = {
        Neurotype.SEEDCASTER: "They plant what others haven't imagined yet.",
        Neurotype.FABRICANT: "If it doesn't exist, they build it.",
        Neurotype.MYCELIAN: "They think in networks and grow in the dark.",
        Neurotype.TERRAFORMER: "They redesign the spaces we inhabit.",
        Neurotype.DEVELOPER: "They write the tools of sovereignty.",
        Neurotype.ARTISAN: "They make the future beautiful enough to want.",
        Neurotype.CHRONICLER: "They make sure the work gets seen.",
        Neurotype.CULTIVAR: "They bridge the lab and the land.",
        Neurotype.LOOMKEEPER: "They hold the network together.",
        Neurotype.VERDANT: "They change the rules of the game."
    }
    return descriptions.get(neurotype, "Unknown neurotype")