import React, { useState, useEffect } from 'react';

interface Room {
  id: string;
  name: string;
  language: string;
  created_at: string;
}

interface RoomManagerProps {
  onJoinRoom: (room: Room) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const RoomManager: React.FC<RoomManagerProps> = ({ onJoinRoom }) => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [roomName, setRoomName] = useState('');
  const [language, setLanguage] = useState('python');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRooms();
  }, []);

  const fetchRooms = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rooms`);
      if (!response.ok) throw new Error('Failed to fetch rooms');
      const data = await response.json();
      setRooms(data);
    } catch (err) {
      setError('Failed to load rooms. Is the backend running?');
      console.error(err);
    }
  };

  const createRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: roomName, language }),
      });

      if (!response.ok) throw new Error('Failed to create room');

      const newRoom = await response.json();
      setRooms([...rooms, newRoom]);
      setRoomName('');
      onJoinRoom(newRoom);
    } catch (err) {
      setError('Failed to create room');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const deleteRoom = async (roomId: string, roomName: string) => {
    if (!confirm(`Delete room "${roomName}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete room');

      // Remove room from local state
      setRooms(rooms.filter(room => room.id !== roomId));
    } catch (err) {
      setError('Failed to delete room');
      console.error(err);
    }
  };

  return (
    <div className="room-manager">
      <div className="create-room-section">
        <h2>Create New Room</h2>
        <form onSubmit={createRoom}>
          <input
            type="text"
            placeholder="Room name"
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
            required
            disabled={loading}
          />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading}
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
          </select>
          <button type="submit" disabled={loading || !roomName.trim()}>
            {loading ? 'Creating...' : 'Create Room'}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="rooms-list-section">
        <h2>Previously Created Rooms ({rooms.length})</h2>
        {rooms.length === 0 ? (
          <p className="no-rooms">No rooms available. Create one to get started!</p>
        ) : (
          <div className="rooms-grid">
            {rooms.map((room) => (
              <div key={room.id} className="room-card">
                <h3>{room.name}</h3>
                <p className="room-language">{room.language}</p>
                <p className="room-date">
                  Created: {new Date(room.created_at).toLocaleDateString()}
                </p>
                <div className="room-actions">
                  <button onClick={() => onJoinRoom(room)} className="join-btn">
                    Join Room
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteRoom(room.id, room.name);
                    }}
                    className="delete-btn"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RoomManager;
