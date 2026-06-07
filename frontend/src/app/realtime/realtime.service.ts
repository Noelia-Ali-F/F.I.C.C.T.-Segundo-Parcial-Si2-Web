import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Observable, Subject, filter } from 'rxjs';

import { readStoredAppSession } from '../auth/session-context';
import { buildRealtimeWebSocketUrl } from '../shared/api-base';
import {
  ConnectionState,
  EmergencyRealtimeEvent,
  RealtimeEvent,
  WsConnectedEvent,
} from './realtime.types';

const EMERGENCY_EVENT_TYPES = new Set([
  'emergency_registered',
  'technician_assigned',
  'emergency_status_updated',
  'technician_on_the_way',
  'technician_on_site',
  'service_started',
  'service_finished',
  'request_rejected',
  'tracking_location_updated',
]);

@Injectable({ providedIn: 'root' })
export class RealtimeService {
  private readonly connectionStateSubject = new BehaviorSubject<ConnectionState>('idle');
  private readonly eventsSubject = new Subject<RealtimeEvent | WsConnectedEvent>();
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private manualDisconnect = false;

  readonly connectionState$ = this.connectionStateSubject.asObservable();
  readonly events$ = this.eventsSubject.asObservable();
  readonly emergencyEvents$: Observable<EmergencyRealtimeEvent | RealtimeEvent> = this.events$.pipe(
    filter((event) =>
      event.type === 'ws_connected' ? false : EMERGENCY_EVENT_TYPES.has(String(event.type)),
    ),
  );

  constructor(private readonly ngZone: NgZone) {}

  connect(): void {
    const session = readStoredAppSession();
    const token = session?.accessToken?.trim();

    if (!token) {
      this.manualDisconnect = false;
      this.clearReconnectTimer();
      this.closeSocket();
      this.connectionStateSubject.next('disconnected');
      return;
    }

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.manualDisconnect = false;
    this.clearReconnectTimer();
    this.connectionStateSubject.next(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');

    const socket = new WebSocket(buildRealtimeWebSocketUrl(token));
    this.socket = socket;

    socket.onopen = () => {
      this.ngZone.run(() => {
        if (this.socket !== socket) {
          return;
        }
        this.reconnectAttempts = 0;
        this.clearReconnectTimer();
        this.connectionStateSubject.next('connected');
      });
    };

    socket.onmessage = (message) => {
      this.ngZone.run(() => {
        if (this.socket !== socket) {
          return;
        }
        const parsed = this.parseEvent(message.data);
        if (parsed) {
          this.eventsSubject.next(parsed);
        }
      });
    };

    socket.onerror = () => {
      this.ngZone.run(() => {
        if (this.socket !== socket) {
          return;
        }
        this.connectionStateSubject.next('error');
        if (!this.manualDisconnect) {
          this.closeSocket(socket);
        }
      });
    };

    socket.onclose = () => {
      this.ngZone.run(() => {
        if (this.socket === socket) {
          this.socket = null;
        }
        if (this.manualDisconnect) {
          this.connectionStateSubject.next('disconnected');
          return;
        }
        this.connectionStateSubject.next('disconnected');
        this.scheduleReconnect();
      });
    };
  }

  disconnect(): void {
    this.manualDisconnect = true;
    this.reconnectAttempts = 0;
    this.clearReconnectTimer();
    this.closeSocket();
    this.connectionStateSubject.next('disconnected');
  }

  sendPing(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    this.socket.send(JSON.stringify({ type: 'ping' }));
  }

  private scheduleReconnect(): void {
    const session = readStoredAppSession();
    if (this.manualDisconnect || !session?.accessToken?.trim()) {
      this.clearReconnectTimer();
      this.connectionStateSubject.next('disconnected');
      return;
    }

    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.clearReconnectTimer();
    this.reconnectAttempts += 1;
    this.connectionStateSubject.next('reconnecting');

    const delayMs = Math.min(1000 * 2 ** Math.max(0, this.reconnectAttempts - 1), 10000);
    this.reconnectTimer = setTimeout(() => this.connect(), delayMs);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private closeSocket(targetSocket?: WebSocket | null): void {
    const socketToClose = targetSocket ?? this.socket;
    if (!socketToClose) {
      return;
    }

    socketToClose.close();
    if (this.socket === socketToClose) {
      this.socket = null;
    }
  }

  private parseEvent(rawData: unknown): RealtimeEvent | WsConnectedEvent | null {
    if (typeof rawData !== 'string') {
      return null;
    }

    try {
      const parsed = JSON.parse(rawData) as RealtimeEvent | WsConnectedEvent;
      return parsed && typeof parsed.type === 'string' ? parsed : null;
    } catch {
      return null;
    }
  }
}
