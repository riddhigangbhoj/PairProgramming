"""
WebSocket connection manager.
Manages all WebSocket connections, room assignments, and message broadcasting.
This is the core of the real-time collaboration system.
"""

from fastapi import WebSocket
from typing import Dict, List, Optional, Tuple
import logging
import uuid

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manager for WebSocket connections and broadcasting."""

    def __init__(self):
        # Map of room_id -> list of (WebSocket, user_id) tuples
        self.active_connections: Dict[str, List[Tuple[WebSocket, str]]] = {}
        # Map of WebSocket -> user_id
        self.websocket_to_user: Dict[WebSocket, str] = {}
        logger.info("WebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket, room_id: str) -> str:
        """Accept a new WebSocket connection and add to room. Returns user_id."""
        await websocket.accept()

        # Generate unique user ID
        user_id = str(uuid.uuid4())[:8]  # Short user ID

        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
            logger.info(f"Created new room: {room_id}")

        self.active_connections[room_id].append((websocket, user_id))
        self.websocket_to_user[websocket] = user_id
        connection_count = len(self.active_connections[room_id])
        logger.info(
            f"WebSocket connected to room {room_id} with user_id {user_id} "
            f"(total connections: {connection_count})"
        )
        return user_id
    
    def disconnect(self, websocket: WebSocket, room_id: str) -> Optional[str]:
        """Remove a WebSocket connection from a room. Returns user_id if found."""
        user_id = self.websocket_to_user.get(websocket)

        if room_id in self.active_connections:
            # Find and remove the connection tuple
            self.active_connections[room_id] = [
                (ws, uid) for ws, uid in self.active_connections[room_id]
                if ws != websocket
            ]
            connection_count = len(self.active_connections[room_id])
            logger.info(
                f"WebSocket disconnected from room {room_id} "
                f"(remaining connections: {connection_count})"
            )

            # Clean up empty rooms
            if len(self.active_connections[room_id]) == 0:
                del self.active_connections[room_id]
                logger.info(f"Room {room_id} removed (no active connections)")

        # Clean up user mapping
        if websocket in self.websocket_to_user:
            del self.websocket_to_user[websocket]

        return user_id
    
    async def broadcast(self, room_id: str, message: dict, exclude: Optional[WebSocket] = None):
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: The room to broadcast to
            message: The message to send (will be converted to JSON)
            exclude: Optional WebSocket to exclude from broadcast (e.g., sender)
        """
        if room_id not in self.active_connections:
            return

        # Get list of connections to broadcast to
        connections = [
            ws for ws, uid in self.active_connections[room_id]
            if ws != exclude
        ]

        # Send to all connections
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to broadcast to connection in room {room_id}: {e}"
                )
                disconnected.append(connection)

        # Clean up disconnected clients
        if disconnected:
            logger.info(
                f"Cleaning up {len(disconnected)} disconnected clients from room {room_id}"
            )
            for connection in disconnected:
                self.disconnect(connection, room_id)
    
    def get_room_connection_count(self, room_id: str) -> int:
        """Get the number of active connections in a room."""
        return len(self.active_connections.get(room_id, []))

    def get_user_id(self, websocket: WebSocket) -> Optional[str]:
        """Get user_id for a websocket connection."""
        return self.websocket_to_user.get(websocket)

    def get_all_rooms(self) -> List[str]:
        """Get list of all room IDs with active connections."""
        return list(self.active_connections.keys())