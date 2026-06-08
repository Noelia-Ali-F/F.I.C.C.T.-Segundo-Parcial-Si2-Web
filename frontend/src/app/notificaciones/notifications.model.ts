export interface SystemNotificationRecord {
  id: number;
  tenant_id: number | null;
  tenant_slug: string | null;
  sucursal_id: number | null;
  recipient_user_id: number;
  recipient_role: string;
  recipient_email: string | null;
  recipient_name: string | null;
  event_type: string;
  event_source: string;
  entity_type: string;
  entity_id: number | null;
  title: string;
  body: string;
  data_json: string | null;
  channel: string;
  delivery_status: string;
  read_status: string;
  error_code: string | null;
  error_message: string | null;
  fcm_token_id: number | null;
  fcm_message_id: string | null;
  retry_count: number;
  idempotency_key: string;
  created_at: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
}

export interface SystemNotificationListResponse {
  items: SystemNotificationRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface NotificationSummaryResponse {
  total: number;
  sent: number;
  failed: number;
  pending: number;
  skipped: number;
  retried: number;
  read: number;
  unread: number;
  by_event_type: Record<string, number>;
}

export interface NotificationFilters {
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  recipient_user_id?: number | null;
  recipient_role?: string | null;
  event_type?: string | null;
  delivery_status?: string | null;
  read_status?: string | null;
  entity_type?: string | null;
  entity_id?: number | null;
}
