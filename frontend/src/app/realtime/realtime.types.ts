export type ConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'error';

export type RealtimeEventType =
  | 'ws_connected'
  | 'pong'
  | 'emergency_registered'
  | 'technician_assigned'
  | 'emergency_status_updated'
  | 'technician_on_the_way'
  | 'technician_on_site'
  | 'service_started'
  | 'service_finished'
  | 'request_rejected'
  | 'tracking_location_updated'
  | 'ws_error';

export interface RealtimeEventPayload {
  emergency_id?: number;
  status?: string | null;
  client_id?: number | null;
  assigned_technician_id?: number | null;
  nearest_workshop_id?: number | null;
  sucursal_id?: number | null;
  technician_id?: number | null;
  tracking_latitude?: number | null;
  tracking_longitude?: number | null;
  tracking_source?: string | null;
  rejection_reason?: string | null;
  [key: string]: unknown;
}

export interface RealtimeEvent {
  type: RealtimeEventType | string;
  tenant_id?: number | null;
  tenant_slug?: string | null;
  sucursal_id?: number | null;
  user_id?: number | null;
  role_target?: string | null;
  entity_type?: string | null;
  entity_id?: number | null;
  payload?: RealtimeEventPayload;
  event_id?: string;
  created_at?: string;
  delivery_channel?: string | null;
  detail?: string;
}

export interface WsConnectedEvent {
  type: 'ws_connected';
  user_id: number;
  tenant_id: number | null;
  tenant_slug: string | null;
  role: string;
  sucursal_id: number | null;
  channels: string[];
}

export interface EmergencyRealtimeEvent extends RealtimeEvent {
  entity_type: 'emergency';
  entity_id: number;
  payload: RealtimeEventPayload;
}
