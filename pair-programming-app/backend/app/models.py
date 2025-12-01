"""
Data models for the pair programming application.
Includes both SQLAlchemy models (database) and Pydantic models (API validation).
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel, Field
import uuid

# SQLAlchemy 2.0 Style Base
class Base(DeclarativeBase):
    pass


# ============================================================================
# SQLAlchemy Models (Database Tables)
# ============================================================================

class Room(Base):
    """
    Database model for a coding room.
    Stores the room's code state and metadata.
    """
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    code = Column(Text, default="# Start coding here...")
    language = Column(String(50), default="python")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Room {self.name} ({self.id})>"


# ============================================================================
# Pydantic Models (API Request/Response Schemas)
# ============================================================================

class RoomCreate(BaseModel):
    """Request model for creating a new room"""
    name: str = Field(..., min_length=1, max_length=255, description="Room name")
    language: Optional[str] = Field(default="python", description="Programming language")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Coding Room",
                "language": "python"
            }
        }


class RoomResponse(BaseModel):
    """Response model for room data"""
    id: str
    name: str
    code: str
    language: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "abc123-def456",
                "name": "My Coding Room",
                "code": "# Start coding here...",
                "language": "python",
                "created_at": "2024-11-26T10:00:00",
                "updated_at": "2024-11-26T10:30:00"
            }
        }


class CodeUpdate(BaseModel):
    """Model for code update messages"""
    room_id: str
    code: str
    user_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "abc123",
                "code": "print('Hello World')",
                "user_id": "user_001"
            }
        }


class AutocompleteRequest(BaseModel):
    """Request for AI autocomplete suggestions"""
    code: str = Field(..., description="Current code context")
    cursor_position: int = Field(..., ge=0, description="Cursor position in code")
    language: Optional[str] = Field(default="python", description="Programming language")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "def hel",
                "cursor_position": 7,
                "language": "python"
            }
        }


class AutocompleteResponse(BaseModel):
    """Response with autocomplete suggestions"""
    suggestions: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "suggestions": ["def hello_world():", "def help():"],
                "confidence": 0.85
            }
        }


class WebSocketMessage(BaseModel):
    """
    Message format for WebSocket communication.
    Types: "code_update", "cursor_position", "user_joined", "user_left"
    """
    type: str
    data: dict
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "code_update",
                "data": {"code": "print('hello')"},
                "user_id": "user_001",
                "timestamp": "2024-11-26T10:30:00"
            }
        }