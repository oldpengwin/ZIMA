"""Connection request CRUD (send/accept/reject a connection between two profiles)."""

import logging
import uuid
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import Connection, ConnectionStatusEnum, Profile

logger = logging.getLogger(__name__)


class ConnectionServiceError(Exception):
    pass


class ConnectionNotFoundError(ConnectionServiceError):
    pass


class DuplicateConnectionError(ConnectionServiceError):
    pass


def create_connection(db: Session, from_user_id: str, to_user_id: str, message: str = "") -> Connection:
    if str(from_user_id) == str(to_user_id):
        raise ConnectionServiceError("Cannot connect to yourself")
    if not db.get(Profile, uuid.UUID(str(to_user_id))):
        raise ConnectionServiceError(f"Target profile {to_user_id} does not exist")

    conn = Connection(
        id=uuid.uuid4(),
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        status=ConnectionStatusEnum.PENDING.value,
        message=message,
    )
    db.add(conn)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateConnectionError("A connection request already exists between these users") from e
    db.refresh(conn)
    return conn


def update_connection_status(db: Session, connection_id: str, status: str) -> Connection:
    if status not in {s.value for s in ConnectionStatusEnum}:
        raise ConnectionServiceError(f"Invalid status: {status}")
    conn = db.get(Connection, uuid.UUID(str(connection_id)))
    if not conn:
        raise ConnectionNotFoundError(f"Connection {connection_id} not found")
    conn.status = status
    db.commit()
    db.refresh(conn)
    return conn


def get_connections_for_user(db: Session, user_id: str, status: Optional[str] = None) -> List[Connection]:
    q = db.query(Connection).filter(
        or_(Connection.from_user_id == user_id, Connection.to_user_id == user_id)
    )
    if status:
        q = q.filter(Connection.status == status)
    return q.order_by(Connection.created_at.desc()).all()
