/* eslint-disable @typescript-eslint/no-explicit-any */
import { logError } from "./helpers";

export type WebsocketStatusPhase =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "offline"
  | "disconnected";

export type WebsocketStatus = {
  phase: WebsocketStatusPhase;
  attempt: number;
  maxAttempts: number;
};

export type WebsocketConnOptions = {
  maxReconnectAttempts: number;
  reconnectBaseDelayMs: number;
  reconnectMaxDelayMs: number;
};

const DEFAULT_OPTIONS: WebsocketConnOptions = {
  maxReconnectAttempts: 5,
  reconnectBaseDelayMs: 1000,
  reconnectMaxDelayMs: 16_000,
};

/** A small socket.io-like client with bounded retry and status reporting. */
export class WebsocketConn {
  private ws: WebSocket | null = null;
  private connected = false;
  private connecting = false;
  private closed = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private generation = 0;
  private reconnectAttempts = 0;
  private readonly options: WebsocketConnOptions;
  private eventToHandlers: Map<string, any[]> = new Map();
  private messages: string[] = [];

  constructor(
    private url: string,
    options: Partial<WebsocketConnOptions> = {},
  ) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  public on(event: string, handler: any) {
    let handlers = this.eventToHandlers.get(event);
    if (!handlers) {
      handlers = [];
      this.eventToHandlers.set(event, handlers);
    }
    handlers.push(handler);
  }

  private notify(event: string, ...args: any[]) {
    const handlers = this.eventToHandlers.get(event);
    if (!handlers) return;
    for (const handler of handlers) {
      try {
        handler(...args);
      } catch (error) {
        logError(error);
      }
    }
  }

  private notifyStatus(phase: WebsocketStatusPhase, attempt = this.reconnectAttempts) {
    const status: WebsocketStatus = {
      phase,
      attempt,
      maxAttempts: this.options.maxReconnectAttempts,
    };
    this.notify("status", status);
  }

  public async emit(event: string, data: any = undefined) {
    const message: any = { event };
    if (data !== undefined) message.data = data;
    this.messages.push(JSON.stringify(message));
    await this.processMessages();
  }

  private async processMessages() {
    if (!this.connected || !this.ws) return;
    while (this.messages.length > 0) {
      try {
        this.ws.send(this.messages[0]);
        this.messages.shift();
      } catch (error) {
        logError(error);
        break;
      }
    }
  }

  public connect(): Promise<void> {
    return this.startConnection(false);
  }

  private startConnection(isRetry: boolean): Promise<void> {
    this.closed = false;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.connecting || this.connected) return Promise.resolve();
    if (!isRetry && this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this.reconnectAttempts = 0;
    }

    this.connecting = true;
    const generation = ++this.generation;
    this.notifyStatus(
      this.reconnectAttempts > 0 ? "reconnecting" : "connecting",
    );

    return new Promise<void>((resolve, reject) => {
      let settled = false;
      const resolveOnce = () => {
        if (settled) return;
        settled = true;
        resolve();
      };
      const rejectOnce = () => {
        if (settled) return;
        settled = true;
        reject(new Error("WebSocket connection failed."));
      };
      const fail = () => {
        if (generation !== this.generation) return;
        this.connected = false;
        this.connecting = false;
        this.notify("disconnect");
        rejectOnce();
        this.handleClose(generation);
      };

      try {
        const ws = new WebSocket(this.url);
        this.ws = ws;
        ws.onopen = () => {
          if (generation !== this.generation) return;
          this.connected = true;
          this.connecting = false;
          this.reconnectAttempts = 0;
          this.notifyStatus("connected", 0);
          this.notify("connect");
          void this.processMessages();
          resolveOnce();
        };
        ws.onmessage = this.handleMessage;
        ws.onclose = () => {
          if (generation !== this.generation) return;
          const wasConnecting = this.connecting;
          this.handleClose(generation);
          if (wasConnecting) rejectOnce();
        };
        ws.onerror = fail;
      } catch {
        fail();
      }
    });
  }

  private handleMessage = (message: MessageEvent) => {
    if (!message.data) return;
    try {
      const { event, data } = JSON.parse(message.data);
      if (!event) return;
      if (data !== undefined) this.notify(event, data);
      else this.notify(event);
    } catch {
      logError(new Error("Runtime sent an invalid WebSocket message."));
    }
  };

  private handleClose = (generation: number) => {
    if (generation !== this.generation) return;
    this.connected = false;
    this.connecting = false;
    this.ws = null;

    if (this.closed) {
      this.notifyStatus("disconnected", this.reconnectAttempts);
      return;
    }
    if (this.reconnectTimer !== null) return;
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this.notifyStatus("offline", this.options.maxReconnectAttempts);
      return;
    }

    this.reconnectAttempts += 1;
    this.notifyStatus("reconnecting", this.reconnectAttempts);
    const delay = Math.min(
      this.options.reconnectBaseDelayMs * 2 ** (this.reconnectAttempts - 1),
      this.options.reconnectMaxDelayMs,
    );
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.closed || generation !== this.generation) return;
      void this.startConnection(true).catch(() => undefined);
    }, delay);
  };

  public disconnect() {
    this.closed = true;
    this.generation += 1;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.messages = [];
    this.ws?.close();
    this.ws = null;
    this.connected = false;
    this.connecting = false;
    this.notifyStatus("disconnected", this.reconnectAttempts);
  }
}
