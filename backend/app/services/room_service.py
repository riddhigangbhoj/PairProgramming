"""
Room service for managing coding rooms.
Handles all business logic for room operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from datetime import datetime, timezone
import logging

from app.models import Room, RoomCreate

logger = logging.getLogger(__name__)


class RoomService:
    """Service for managing coding rooms with proper error handling."""

    def __init__(self, db: Session):
        self.db = db

    def create_room(self, room_data: RoomCreate) -> Room:
        """
        Create a new room.

        Args:
            room_data: Room creation data

        Returns:
            Created room object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            room = Room(
                name=room_data.name,
                language=room_data.language or "python",
                code="# Start coding here..."
            )
            self.db.add(room)
            self.db.commit()
            self.db.refresh(room)

            logger.info(f"Created room: {room.id} - {room.name}")
            return room

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating room: {e}")
            raise

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating room: {e}")
            raise

    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by ID.

        Args:
            room_id: UUID of the room

        Returns:
            Room object if found, None otherwise
        """
        try:
            room = self.db.query(Room).filter(Room.id == room_id).first()
            if room:
                logger.debug(f"Retrieved room: {room_id}")
            else:
                logger.debug(f"Room not found: {room_id}")
            return room

        except SQLAlchemyError as e:
            logger.error(f"Database error getting room {room_id}: {e}")
            raise

    def list_rooms(self, skip: int = 0, limit: int = 100) -> List[Room]:
        """
        List all rooms with pagination.

        Args:
            skip: Number of rooms to skip
            limit: Maximum number of rooms to return

        Returns:
            List of room objects
        """
        try:
            rooms = self.db.query(Room).offset(skip).limit(limit).all()
            logger.debug(f"Listed {len(rooms)} rooms (skip={skip}, limit={limit})")
            return rooms

        except SQLAlchemyError as e:
            logger.error(f"Database error listing rooms: {e}")
            raise

    def update_room_code(self, room_id: str, code: str) -> Optional[Room]:
        """
        Update the code in a room.

        Args:
            room_id: UUID of the room
            code: New code content

        Returns:
            Updated room object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            room = self.get_room(room_id)
            if room:
                room.code = code
                # Explicitly update the timestamp
                room.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(room)
                logger.debug(f"Updated code in room: {room_id}")
            else:
                logger.warning(f"Cannot update code - room not found: {room_id}")
            return room

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating room {room_id}: {e}")
            raise

    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room by ID.

        Args:
            room_id: UUID of the room

        Returns:
            True if deleted, False if room not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            room = self.get_room(room_id)
            if room:
                self.db.delete(room)
                self.db.commit()
                logger.info(f"Deleted room: {room_id} - {room.name}")
                return True
            else:
                logger.warning(f"Cannot delete - room not found: {room_id}")
                return False

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting room {room_id}: {e}")
            raise
