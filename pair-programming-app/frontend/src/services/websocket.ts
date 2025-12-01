const WS_BASE_URL = 'ws://localhost:8000';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: string;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private roomId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;

  constructor(roomId: string) {
    this.roomId = roomId;
    this.connect();
  }

  private connect() {
    const url = `${WS_BASE_URL}/ws/${this.roomId}`;
    console.log('Connecting to WebSocket:', url);

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
      setTimeout(() => this.connect(), this.reconnectDelay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  public onMessage(callback: (message: WebSocketMessage) => void) {
    if (this.ws) {
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          callback(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    }
  }

  public onClose(callback: () => void) {
    if (this.ws) {
      this.ws.onclose = () => {
        callback();
        this.attemptReconnect();
      };
    }
  }

  public sendCodeUpdate(code: string) {
    this.send({
      type: 'code_update',
      data: { code },
    });
  }

  public sendCursorPosition(line: number, column: number) {
    this.send({
      type: 'cursor_position',
      data: { line, column },
    });
  }

  public send(message: Omit<WebSocketMessage, 'timestamp'>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }

  public disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
