import React, { useState } from 'react';
import RoomManager from './components/RoomManager';
import CodeEditor from './components/CodeEditor';
import './App.css';

interface Room {
  id: string;
  name: string;
  language: string;
}

const App: React.FC = () => {
  const [currentRoom, setCurrentRoom] = useState<Room | null>(null);

  const handleJoinRoom = (room: Room) => {
    setCurrentRoom(room);
  };

  const handleLeaveRoom = () => {
    setCurrentRoom(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🐰 Pair Programming</h1>
        {currentRoom && (
          <div className="room-info">
            <span>Room: {currentRoom.name}</span>
            <button onClick={handleLeaveRoom} className="leave-btn">
              Leave Room
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        {!currentRoom ? (
          <RoomManager onJoinRoom={handleJoinRoom} />
        ) : (
          <CodeEditor
            roomId={currentRoom.id}
            language={currentRoom.language}
          />
        )}
      </main>
    </div>
  );
};

export default App;
