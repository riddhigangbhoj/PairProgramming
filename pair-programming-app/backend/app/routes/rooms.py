"""
Room management endpoints.
Handles creating, retrieving, listing, and deleting rooms.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import RoomCreate, RoomResponse
from app.services.room_service import RoomService


router = APIRouter()


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(room_data: RoomCreate, db: Session = Depends(get_db)):
    """
    Create a new coding room for pair programming.
    - **name**: Name of the room
    - **language**: Programming language (default: python)
    """
    room_service = RoomService(db)
    room = room_service.create_room(room_data)
    return room


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str, db: Session = Depends(get_db)):
    """
    Get room details by ID.
    """
    room_service = RoomService(db)
    room = room_service.get_room(room_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {room_id} not found"
        )
    
    return room


@router.get("/", response_model=List[RoomResponse])
async def list_rooms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all available rooms.
    """
    room_service = RoomService(db)
    rooms = room_service.list_rooms(skip=skip, limit=limit)
    return rooms


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: str, db: Session = Depends(get_db)):
    """
    Delete a room by ID.
    """
    room_service = RoomService(db)
    success = room_service.delete_room(room_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {room_id} not found"
        )
    
    return None