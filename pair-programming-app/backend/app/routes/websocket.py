"""
WebSocket endpoints for real-time collaboration.
Handles WebSocket connections, message broadcasting, and room synchronization.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
import logging

from app.database import get_db
from app.services.websocket_manager import WebSocketManager
from app.services.room_service import RoomService


router = APIRouter()
manager = WebSocketManager()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for real-time collaboration in a room.

    Handles:
    - Code updates
    - Cursor position updates
    - User presence (join/leave)
    - Broadcasting to all connected clients
    """

    # Get database session
    db: Session = next(get_db())

    try:
        room_service = RoomService(db)

        # Verify room exists BEFORE accepting connection
        room = room_service.get_room(room_id)
        if not room:
            logger.warning(f"WebSocket connection rejected: Room {room_id} not found")
            await websocket.close(code=1008, reason="Room not found")
            return

        # Accept the connection and get user_id
        user_id = await manager.connect(websocket, room_id)
        user_name = f"User-{user_id}"  # Simple user name for now
        logger.info(f"WebSocket connected to room {room_id} with user_id {user_id}")

        try:
            # Send initial room state
            await websocket.send_json({
                "type": "init",
                "data": {
                    "room_id": room_id,
                    "code": room.code,
                    "language": room.language
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Notify others that a user joined
            user_count = len(manager.active_connections.get(room_id, []))
            await manager.broadcast(
                room_id,
                {
                    "type": "user_joined",
                    "data": {
                        "room_id": room_id,
                        "user_count": user_count
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                exclude=websocket
            )
            logger.debug(f"User joined room {room_id}, total users: {user_count}")

            # Listen for messages
            while True:
                data = await websocket.receive_text()

                # Handle invalid JSON
                try:
                    message = json.loads(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from room {room_id}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON format"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    continue

                # Validate message structure
                if not isinstance(message, dict) or "type" not in message:
                    logger.warning(f"Invalid message structure from room {room_id}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid message structure"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    continue

                msg_type = message.get("type")
                msg_data = message.get("data", {})

                # Handle different message types
                if msg_type == "code_update":
                    # Validate data structure
                    if not isinstance(msg_data, dict) or "code" not in msg_data:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Invalid code_update format"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        continue

                    # Handle database errors
                    try:
                        room_service.update_room_code(room_id, msg_data["code"])
                    except Exception as e:
                        logger.error(f"Failed to update room {room_id}: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Failed to save code"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        continue

                    # Broadcast to all clients except sender
                    await manager.broadcast(
                        room_id,
                        {
                            "type": "code_update",
                            "data": msg_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        exclude=websocket
                    )
                    logger.debug(f"Code updated in room {room_id}")

                elif msg_type == "cursor_position":
                    # Broadcast cursor position to others
                    await manager.broadcast(
                        room_id,
                        {
                            "type": "cursor_position",
                            "data": msg_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        exclude=websocket
                    )

                elif msg_type == "cursor_update":
                    # Broadcast cursor update with user info to others
                    msg_data["user_id"] = user_id
                    msg_data["user_name"] = user_name
                    await manager.broadcast(
                        room_id,
                        {
                            "type": "cursor_update",
                            "data": msg_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        exclude=websocket
                    )

                else:
                    # Unknown message type
                    logger.debug(f"Unknown message type '{msg_type}' from room {room_id}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {msg_type}"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected from room {room_id}")
            disconnected_user_id = manager.disconnect(websocket, room_id)

            # Notify others that a user left
            user_count = len(manager.active_connections.get(room_id, []))
            await manager.broadcast(
                room_id,
                {
                    "type": "user_left",
                    "data": {
                        "room_id": room_id,
                        "user_id": disconnected_user_id,
                        "user_count": user_count
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            logger.debug(f"User {disconnected_user_id} left room {room_id}, remaining users: {user_count}")

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"WebSocket error in room {room_id}: {e}", exc_info=True)
            manager.disconnect(websocket, room_id)
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass  # Connection might already be closed

    finally:
        # Always close database session
        db.close()
        logger.debug(f"Database session closed for room {room_id}")