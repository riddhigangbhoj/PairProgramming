import React, { useState, useEffect, useRef, useCallback } from 'react';
import Editor, { OnMount, Monaco } from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import { WebSocketService } from '../services/websocket';

interface CodeEditorProps {
  roomId: string;
  language: string;
}

interface RemoteUser {
  userId: string;
  userName: string;
  position: { line: number; column: number };
  color: string;
  decorations: string[];
}

const USER_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
  '#DDA15E', '#BC6C25', '#F4A261', '#E76F51', '#2A9D8F'
];

const CodeEditor: React.FC<CodeEditorProps> = ({ roomId, language }) => {
  const [code, setCode] = useState('# Start coding here...');
  const [connected, setConnected] = useState(false);
  const [userCount, setUserCount] = useState(1);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const wsService = useRef<WebSocketService | null>(null);
  const remoteUsers = useRef<Map<string, RemoteUser>>(new Map());
  const isRemoteChange = useRef(false);
  const reconnectTimeout = useRef<number>(1000);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const cursorUpdateThrottle = useRef<NodeJS.Timeout | null>(null);
  const aiRequestController = useRef<AbortController | null>(null);
  const aiDebounceTimer = useRef<NodeJS.Timeout | null>(null);

  // Generate consistent color for user ID
  const getUserColor = (userId: string): string => {
    const hash = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return USER_COLORS[hash % USER_COLORS.length];
  };

  // Handle editor mount
  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // Register AI inline completion provider
    registerInlineCompletionProvider(monaco, language);

    // Listen for cursor position changes
    editor.onDidChangeCursorPosition((e) => {
      if (!isRemoteChange.current) {
        sendCursorUpdate(e.position.lineNumber, e.position.column);
      }
    });

    // Listen for content changes
    editor.onDidChangeModelContent((e) => {
      if (!isRemoteChange.current && e.changes.length > 0) {
        const newCode = editor.getValue();
        setCode(newCode);
        wsService.current?.sendCodeUpdate(newCode);

        // Trigger AI autocomplete (debounced)
        triggerAIAutocomplete(newCode, editor.getPosition());
      }
    });
  };

  // Register inline completion provider for AI suggestions
  const registerInlineCompletionProvider = (monaco: Monaco, lang: string) => {
    monaco.languages.registerInlineCompletionsProvider(lang, {
      provideInlineCompletions: async (
        _model: monaco.editor.ITextModel,
        _position: monaco.Position,
        _context: monaco.languages.InlineCompletionContext,
        _token: monaco.CancellationToken
      ) => {
        // This will be triggered by Monaco automatically
        // We'll use our manual trigger instead for more control
        return { items: [] };
      },
      freeInlineCompletions: () => {}
    });
  };

  // Trigger AI autocomplete with debouncing
  const triggerAIAutocomplete = (code: string, position: monaco.Position | null) => {
    if (!position || code.length === 0) return;

    // Clear existing debounce timer
    if (aiDebounceTimer.current) {
      clearTimeout(aiDebounceTimer.current);
    }

    // Cancel any in-flight request
    if (aiRequestController.current) {
      aiRequestController.current.abort();
    }

    // Debounce for 500ms
    aiDebounceTimer.current = setTimeout(() => {
      fetchAISuggestions(code, position);
    }, 500);
  };

  // Fetch AI suggestions from backend
  const fetchAISuggestions = async (code: string, position: monaco.Position) => {
    try {
      setAiLoading(true);
      aiRequestController.current = new AbortController();

      const offset = editorRef.current?.getModel()?.getOffsetAt(position) || 0;

      const response = await fetch('http://localhost:8000/autocomplete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          cursor_position: offset,
          language,
        }),
        signal: aiRequestController.current.signal,
      });

      if (!response.ok) throw new Error('Autocomplete request failed');

      const data = await response.json();

      // Show suggestions (for now, we'll log them)
      // In a future enhancement, we could show them in a custom widget
      if (data.suggestions.length > 0 && data.confidence > 0.7) {
        console.log('AI Suggestions:', data.suggestions, 'Confidence:', data.confidence);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Autocomplete error:', err);
      }
    } finally {
      setAiLoading(false);
      aiRequestController.current = null;
    }
  };

  // Send cursor update to other users (throttled)
  const sendCursorUpdate = (line: number, column: number) => {
    if (cursorUpdateThrottle.current) return;

    cursorUpdateThrottle.current = setTimeout(() => {
      wsService.current?.send({
        type: 'cursor_update',
        data: {
          position: { line, column }
        }
      });
      cursorUpdateThrottle.current = null;
    }, 100);
  };

  // Update remote user cursor
  const updateRemoteCursor = (userId: string, userName: string, position: { line: number; column: number }) => {
    if (!editorRef.current || !monacoRef.current) return;

    const editor = editorRef.current;
    const monaco = monacoRef.current;

    let user = remoteUsers.current.get(userId);

    if (!user) {
      user = {
        userId,
        userName,
        position,
        color: getUserColor(userId),
        decorations: []
      };
      remoteUsers.current.set(userId, user);
    }

    user.position = position;

    // Create cursor decoration
    const decorations = editor.deltaDecorations(
      user.decorations,
      [
        {
          range: new monaco.Range(position.line, position.column, position.line, position.column),
          options: {
            className: `remote-cursor remote-cursor-${userId}`,
            stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
            beforeContentClassName: 'cursor-line',
            after: {
              content: userName,
              inlineClassName: `cursor-label`,
              inlineClassNameAffectsLetterSpacing: true
            }
          }
        }
      ]
    );

    user.decorations = decorations;
    remoteUsers.current.set(userId, user);

    // Inject dynamic styles for this user's color
    injectUserCursorStyles(userId, user.color);
  };

  // Remove remote user cursor
  const removeRemoteCursor = (userId: string) => {
    if (!editorRef.current) return;

    const user = remoteUsers.current.get(userId);
    if (user) {
      editorRef.current.deltaDecorations(user.decorations, []);
      remoteUsers.current.delete(userId);
    }
  };

  // Inject CSS for user cursor color
  const injectUserCursorStyles = (userId: string, color: string) => {
    const styleId = `cursor-style-${userId}`;
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .remote-cursor-${userId} .cursor-line::before {
        content: '';
        position: absolute;
        width: 2px;
        height: 1.2em;
        background-color: ${color};
        animation: cursorBlink 1s infinite;
      }
      .remote-cursor-${userId} .cursor-label {
        background-color: ${color};
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 500;
        margin-left: 4px;
        white-space: nowrap;
      }
    `;
    document.head.appendChild(style);
  };

  // Handle reconnection with exponential backoff
  const attemptReconnect = useCallback(() => {
    if (reconnectTimer.current) return;

    setIsReconnecting(true);

    reconnectTimer.current = setTimeout(() => {
      console.log(`Attempting to reconnect... (timeout: ${reconnectTimeout.current}ms)`);

      // Re-initialize WebSocket
      if (wsService.current) {
        wsService.current.disconnect();
      }
      initializeWebSocket();

      reconnectTimer.current = null;

      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      reconnectTimeout.current = Math.min(reconnectTimeout.current * 2, 30000);
    }, reconnectTimeout.current);
  }, []);

  // Initialize WebSocket connection
  const initializeWebSocket = useCallback(() => {
    wsService.current = new WebSocketService(roomId);

    wsService.current.onMessage((message) => {
      switch (message.type) {
        case 'init':
          setCode(message.data.code);
          setConnected(true);
          setIsReconnecting(false);
          reconnectTimeout.current = 1000; // Reset backoff on successful connection

          // Update editor with initial code
          if (editorRef.current && message.data.code !== editorRef.current.getValue()) {
            isRemoteChange.current = true;
            editorRef.current.setValue(message.data.code);
            isRemoteChange.current = false;
          }
          break;

        case 'code_update':
          isRemoteChange.current = true;
          setCode(message.data.code);
          if (editorRef.current && message.data.code !== editorRef.current.getValue()) {
            editorRef.current.setValue(message.data.code);
          }
          isRemoteChange.current = false;
          break;

        case 'cursor_update':
          if (message.data.user_id && message.data.position) {
            updateRemoteCursor(
              message.data.user_id,
              message.data.user_name || 'Anonymous',
              message.data.position
            );
          }
          break;

        case 'user_joined':
        case 'user_left':
          setUserCount(message.data.user_count);

          // Clean up cursor if user left
          if (message.type === 'user_left' && message.data.user_id) {
            removeRemoteCursor(message.data.user_id);
          }
          break;
      }
    });

    wsService.current.onClose(() => {
      setConnected(false);
      attemptReconnect();
    });
  }, [roomId, attemptReconnect]);

  useEffect(() => {
    initializeWebSocket();

    // Cleanup on unmount
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (cursorUpdateThrottle.current) {
        clearTimeout(cursorUpdateThrottle.current);
      }
      if (aiDebounceTimer.current) {
        clearTimeout(aiDebounceTimer.current);
      }
      if (aiRequestController.current) {
        aiRequestController.current.abort();
      }
      wsService.current?.disconnect();
    };
  }, [initializeWebSocket]);

  // Manual autocomplete request
  const requestAutocomplete = async () => {
    if (!editorRef.current) return;

    const position = editorRef.current.getPosition();
    if (position) {
      await fetchAISuggestions(editorRef.current.getValue(), position);
    }
  };

  return (
    <div className="code-editor">
      <div className="editor-toolbar">
        <div className="toolbar-left">
          <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '🟢 Connected' : isReconnecting ? '🟡 Reconnecting...' : '🔴 Disconnected'}
          </span>
          <span className="user-count">👥 {userCount} user(s)</span>
          {aiLoading && <span className="ai-loading">✨ AI thinking...</span>}
        </div>
        <div className="toolbar-right">
          <button onClick={requestAutocomplete} disabled={!connected || aiLoading}>
            ✨ Get AI Suggestions
          </button>
        </div>
      </div>

      {isReconnecting && (
        <div className="reconnection-banner">
          Connection lost. Reconnecting...
        </div>
      )}

      <Editor
        height="600px"
        language={language}
        value={code}
        onMount={handleEditorDidMount}
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          quickSuggestions: false,
          suggestOnTriggerCharacters: false,
          tabSize: 2,
          insertSpaces: true,
          readOnly: !connected,
          cursorStyle: 'line',
          cursorBlinking: 'blink',
        }}
        theme="vs-dark"
      />

      <div className="editor-footer">
        <span>Language: {language}</span>
        <span>Room ID: {roomId}</span>
      </div>

      <style>{`
        .code-editor {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #1e1e1e;
        }

        .editor-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: #2d2d30;
          border-bottom: 1px solid #3e3e42;
        }

        .toolbar-left {
          display: flex;
          gap: 16px;
          align-items: center;
        }

        .status-indicator {
          font-size: 14px;
          font-weight: 500;
        }

        .status-indicator.connected {
          color: #4ec9b0;
        }

        .status-indicator.disconnected {
          color: #f48771;
        }

        .user-count {
          color: #cccccc;
          font-size: 14px;
        }

        .ai-loading {
          color: #dcdcaa;
          font-size: 12px;
          font-style: italic;
        }

        .toolbar-right button {
          background: #0e639c;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
        }

        .toolbar-right button:hover:not(:disabled) {
          background: #1177bb;
        }

        .toolbar-right button:disabled {
          background: #3e3e42;
          color: #858585;
          cursor: not-allowed;
        }

        .reconnection-banner {
          background: #f4a261;
          color: #1e1e1e;
          padding: 8px 16px;
          text-align: center;
          font-weight: 500;
          animation: slideDown 0.3s ease-out;
        }

        @keyframes slideDown {
          from {
            transform: translateY(-100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .editor-footer {
          display: flex;
          justify-content: space-between;
          padding: 8px 16px;
          background: #2d2d30;
          border-top: 1px solid #3e3e42;
          color: #cccccc;
          font-size: 12px;
        }

        @keyframes cursorBlink {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }

        .remote-cursor {
          position: relative;
        }

        .cursor-line {
          position: relative;
        }
      `}</style>
    </div>
  );
};

export default CodeEditor;
