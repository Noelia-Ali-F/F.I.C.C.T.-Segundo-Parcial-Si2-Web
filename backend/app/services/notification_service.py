from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, list_active_device_fcm_tokens
from app.tenant_context import get_tenant
from app.tenant_schema import (
    CREATE_SYSTEM_NOTIFICATIONS_TENANT_SQL,
    TENANT_SCHEMA_UPGRADE_STATEMENTS,
)
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    TokenPayload,
    compact_push_text,
    firebase_push_is_ready,
    get_effective_technician_id,
    normalize_role,
    send_push_to_device_token,
)

logger = logging.getLogger(__name__)

DELIVERY_PENDING = "pending"
DELIVERY_SENT = "sent"
DELIVERY_FAILED = "failed"
DELIVERY_SKIPPED = "skipped"
DELIVERY_RETRIED = "retried"

READ_UNREAD = "unread"
READ_READ = "read"

VISIBLE_NOTIFICATION_EVENT_TYPES = {
    "EMERGENCY_REGISTERED",
    "REQUEST_ACCEPTED",
    "REQUEST_REJECTED",
    "TECHNICIAN_ASSIGNED",
    "TECHNICIAN_ON_THE_WAY",
    "TECHNICIAN_ARRIVED",
    "SERVICE_STARTED",
    "SERVICE_FINISHED",
    "EMERGENCY_STATUS_CHANGED",
    "SERVICE_CANCELLED",
    "QUOTATION_RECEIVED",
    "QUOTATION_ACCEPTED",
}

_schema_ready_keys: set[str] = set()


@dataclass(frozen=True)
class NotificationRecipient:
    user_id: int
    role: str
    sucursal_id: int | None = None
    email: str | None = None
    name: str | None = None


def _tenant_key() -> str:
    tenant = get_tenant()
    if tenant and tenant.get("slug"):
        return str(tenant["slug"])
    return "default"


def ensure_system_notifications_schema() -> None:
    key = _tenant_key()
    if key in _schema_ready_keys:
        return
    with engine.begin() as connection:
        connection.execute(CREATE_SYSTEM_NOTIFICATIONS_TENANT_SQL)
        for stmt in TENANT_SCHEMA_UPGRADE_STATEMENTS:
            sql_text = str(getattr(stmt, "text", stmt))
            if "system_notifications" not in sql_text:
                continue
            connection.execute(stmt)
    _schema_ready_keys.add(key)


def _tenant_metadata() -> tuple[int | None, str | None]:
    tenant = get_tenant()
    if not tenant:
        return None, None
    tenant_id = int(tenant["id"]) if tenant.get("id") is not None else None
    tenant_slug = str(tenant["slug"]) if tenant.get("slug") else None
    return tenant_id, tenant_slug


def _json_payload(data: Mapping[str, object] | None) -> str | None:
    if not data:
        return None
    return json.dumps(dict(data), ensure_ascii=False, sort_keys=True)


def _event_version(data: Mapping[str, object] | None, explicit_version: str | None) -> str:
    if explicit_version:
        return explicit_version
    if not data:
        return "default"
    for key in ("status", "status_label", "assignment_status", "quotation_status"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return compact_push_text(value, fallback="default", max_length=60)
    return "default"


def build_idempotency_key(
    *,
    tenant_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    recipient_user_id: int,
    event_version: str,
) -> str:
    tenant_value = str(tenant_id) if tenant_id is not None else "none"
    entity_value = str(entity_id) if entity_id is not None else "none"
    version = compact_push_text(event_version, fallback="default", max_length=60)
    return (
        f"tenant:{tenant_value}|event:{event_type}|entity:{entity_type}|"
        f"id:{entity_value}|user:{recipient_user_id}|version:{version}"
    )


def _one_or_none(connection, sql, params: Mapping[str, object]) -> dict[str, object] | None:
    row = connection.execute(sql, params).mappings().first()
    return dict(row) if row else None


def _event_title_body(
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    data: Mapping[str, object] | None,
) -> tuple[str, str]:
    safe_data = dict(data or {})
    incident = compact_push_text(
        safe_data.get("incident_description")
        or safe_data.get("problem_type")
        or safe_data.get("status_label"),
        fallback="Evento del sistema",
        max_length=100,
    )
    workshop_name = compact_push_text(safe_data.get("workshop_name"), fallback="la sucursal", max_length=80)
    technician_name = compact_push_text(safe_data.get("technician_name"), fallback="el técnico", max_length=80)
    status_label = compact_push_text(safe_data.get("status_label"), fallback="Actualización", max_length=80)
    price_label = compact_push_text(safe_data.get("price_label"), fallback="precio disponible", max_length=60)

    templates: dict[str, tuple[str, str]] = {
        "EMERGENCY_REGISTERED": (
            "Nueva emergencia registrada",
            f"Se registró una nueva emergencia: {incident}.",
        ),
        "REQUEST_ACCEPTED": (
            "Emergencia aceptada",
            f"{workshop_name} aceptó la solicitud: {incident}.",
        ),
        "REQUEST_REJECTED": (
            "Emergencia rechazada",
            f"La solicitud fue rechazada: {incident}.",
        ),
        "TECHNICIAN_ASSIGNED": (
            "Técnico asignado",
            f"{technician_name} fue asignado para atender {incident}.",
        ),
        "TECHNICIAN_ON_THE_WAY": (
            "Técnico en camino",
            f"{technician_name} va en camino para atender {incident}.",
        ),
        "TECHNICIAN_ARRIVED": (
            "Técnico en sitio",
            f"{technician_name} llegó al lugar para atender {incident}.",
        ),
        "SERVICE_STARTED": (
            "Servicio iniciado",
            f"El servicio para {incident} ya está en proceso.",
        ),
        "SERVICE_FINISHED": (
            "Servicio finalizado",
            f"El servicio para {incident} fue finalizado.",
        ),
        "EMERGENCY_STATUS_CHANGED": (
            "Estado actualizado",
            f"La emergencia cambió a: {status_label}.",
        ),
        "SERVICE_CANCELLED": (
            "Servicio cancelado",
            f"La emergencia fue cancelada: {incident}.",
        ),
        "REQUEST_SENT_TO_WORKSHOPS": (
            "Nueva solicitud de cotización",
            "Se envió una nueva solicitud de cotización a tu sucursal.",
        ),
        "QUOTATION_RECEIVED": (
            "Cotización recibida",
            f"Se recibió una nueva cotización por {price_label}.",
        ),
        "QUOTATION_ACCEPTED": (
            "Cotización aceptada",
            "La cotización fue aceptada y debe gestionarse en la sucursal correspondiente.",
        ),
    }
    if event_type in templates:
        return templates[event_type]
    fallback_title = compact_push_text(event_type.replace("_", " ").title(), fallback="Notificación", max_length=160)
    return fallback_title, f"Evento {fallback_title} sobre {entity_type} #{entity_id or 's/d'}."


def _insert_notification_record(
    *,
    recipient: NotificationRecipient,
    event_type: str,
    event_source: str,
    entity_type: str,
    entity_id: int | None,
    sucursal_id: int | None,
    title: str,
    body: str,
    data: Mapping[str, object] | None,
    channel: str,
    idempotency_key: str,
) -> dict[str, object]:
    ensure_system_notifications_schema()
    tenant_id, tenant_slug = _tenant_metadata()
    with engine.begin() as connection:
        existing = _one_or_none(
            connection,
            text("SELECT * FROM system_notifications WHERE idempotency_key = :idempotency_key LIMIT 1"),
            {"idempotency_key": idempotency_key},
        )
        if existing:
            return existing
        row = connection.execute(
            text(
                """
                INSERT INTO system_notifications (
                    tenant_id, tenant_slug, sucursal_id, recipient_user_id, recipient_role,
                    recipient_email, recipient_name, event_type, event_source, entity_type,
                    entity_id, title, body, data_json, channel, delivery_status, read_status,
                    retry_count, idempotency_key
                ) VALUES (
                    :tenant_id, :tenant_slug, :sucursal_id, :recipient_user_id, :recipient_role,
                    :recipient_email, :recipient_name, :event_type, :event_source, :entity_type,
                    :entity_id, :title, :body, :data_json, :channel, :delivery_status, :read_status,
                    0, :idempotency_key
                )
                RETURNING *
                """
            ),
            {
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "sucursal_id": sucursal_id,
                "recipient_user_id": recipient.user_id,
                "recipient_role": recipient.role,
                "recipient_email": recipient.email,
                "recipient_name": recipient.name,
                "event_type": event_type,
                "event_source": event_source,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "title": title,
                "body": body,
                "data_json": _json_payload(data),
                "channel": channel,
                "delivery_status": DELIVERY_PENDING,
                "read_status": READ_UNREAD,
                "idempotency_key": idempotency_key,
            },
        ).mappings().first()
    return dict(row)


def _update_notification_status(
    notification_id: int,
    *,
    delivery_status: str,
    error_code: str | None = None,
    error_message: str | None = None,
    fcm_token_id: int | None = None,
    fcm_message_id: str | None = None,
    sent_at: datetime | None = None,
    failed_at: datetime | None = None,
    increment_retry: bool = False,
) -> dict[str, object]:
    ensure_system_notifications_schema()
    delivered_at_value = sent_at if delivery_status in {DELIVERY_SENT, DELIVERY_RETRIED} and sent_at is not None else None
    failed_at_value = failed_at if failed_at is not None else (
        datetime.now(timezone.utc) if delivery_status == DELIVERY_FAILED else None
    )
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                UPDATE system_notifications
                SET delivery_status = CAST(:delivery_status AS VARCHAR(30)),
                    error_code = CAST(:error_code AS VARCHAR(80)),
                    error_message = CAST(:error_message AS TEXT),
                    fcm_token_id = COALESCE(:fcm_token_id, fcm_token_id),
                    fcm_message_id = COALESCE(CAST(:fcm_message_id AS VARCHAR(255)), fcm_message_id),
                    sent_at = COALESCE(CAST(:sent_at AS TIMESTAMPTZ), sent_at),
                    delivered_at = COALESCE(CAST(:delivered_at AS TIMESTAMPTZ), delivered_at),
                    failed_at = COALESCE(CAST(:failed_at AS TIMESTAMPTZ), failed_at),
                    retry_count = CASE WHEN :increment_retry THEN retry_count + 1 ELSE retry_count END
                WHERE id = :notification_id
                RETURNING *
                """
            ),
            {
                "notification_id": notification_id,
                "delivery_status": delivery_status,
                "error_code": error_code,
                "error_message": error_message,
                "fcm_token_id": fcm_token_id,
                "fcm_message_id": fcm_message_id,
                "sent_at": sent_at,
                "delivered_at": delivered_at_value,
                "failed_at": failed_at_value,
                "increment_retry": increment_retry,
            },
        ).mappings().first()
    return dict(row)


def _list_active_tokens_for_recipient(recipient: NotificationRecipient) -> list[dict[str, object]]:
    tenant_id, tenant_slug = _tenant_metadata()
    return list_active_device_fcm_tokens(
        user_id=recipient.user_id,
        role=recipient.role,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        sucursal_id=recipient.sucursal_id,
    )


def _recipient_token_scope_sucursal_id(notification: Mapping[str, object]) -> int | None:
    role = str(notification.get("recipient_role") or "")
    if role in {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO}:
        return int(notification["sucursal_id"]) if notification.get("sucursal_id") is not None else None
    return None


def send_push_notification(notification: Mapping[str, object], *, is_retry: bool = False) -> dict[str, object]:
    recipient = NotificationRecipient(
        user_id=int(notification["recipient_user_id"]),
        role=str(notification["recipient_role"]),
        sucursal_id=_recipient_token_scope_sucursal_id(notification),
        email=str(notification["recipient_email"]) if notification.get("recipient_email") else None,
        name=str(notification["recipient_name"]) if notification.get("recipient_name") else None,
    )
    tokens = _list_active_tokens_for_recipient(recipient)
    if not tokens:
        return _update_notification_status(
            int(notification["id"]),
            delivery_status=DELIVERY_SKIPPED,
            error_code="NO_ACTIVE_TOKEN",
            error_message="No existe token FCM activo para el destinatario dentro del scope actual.",
            increment_retry=is_retry,
        )
    ready, error_detail = firebase_push_is_ready()
    if not ready:
        return _update_notification_status(
            int(notification["id"]),
            delivery_status=DELIVERY_FAILED,
            error_code="FCM_UNAVAILABLE",
            error_message=error_detail or "Firebase Admin SDK no está disponible",
            increment_retry=is_retry,
        )
    token_record = tokens[0]
    try:
        message_id, _delivery = send_push_to_device_token(
            token=str(token_record["fcm_token"]),
            title=str(notification["title"]),
            body=str(notification["body"]),
            data=json.loads(str(notification.get("data_json") or "{}")),
            prefer_visible_notification=str(notification.get("event_type")) in VISIBLE_NOTIFICATION_EVENT_TYPES,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falló envío FCM notification_id=%s", notification.get("id"))
        return _update_notification_status(
            int(notification["id"]),
            delivery_status=DELIVERY_FAILED,
            error_code=exc.__class__.__name__,
            error_message=str(exc),
            fcm_token_id=int(token_record["id"]),
            increment_retry=is_retry,
        )
    return _update_notification_status(
        int(notification["id"]),
        delivery_status=DELIVERY_RETRIED if is_retry else DELIVERY_SENT,
        error_code=None,
        error_message=None,
        fcm_token_id=int(token_record["id"]),
        fcm_message_id=message_id,
        sent_at=datetime.now(timezone.utc),
        increment_retry=is_retry,
    )


def notify_event(
    *,
    event_type: str,
    event_source: str,
    entity_type: str,
    entity_id: int | None,
    recipients: list[NotificationRecipient],
    data: Mapping[str, object] | None = None,
    sucursal_id: int | None = None,
    channel: str = "push_fcm",
    title: str | None = None,
    body: str | None = None,
    event_version: str | None = None,
) -> list[dict[str, object]]:
    ensure_system_notifications_schema()
    tenant_id, _tenant_slug = _tenant_metadata()
    resolved_title, resolved_body = _event_title_body(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
    )
    title = title or resolved_title
    body = body or resolved_body
    version = _event_version(data, event_version)
    results: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    for recipient in recipients:
        key = (recipient.role, recipient.user_id)
        if key in seen:
            continue
        seen.add(key)
        notification = _insert_notification_record(
            recipient=recipient,
            event_type=event_type,
            event_source=event_source,
            entity_type=entity_type,
            entity_id=entity_id,
            sucursal_id=sucursal_id if sucursal_id is not None else recipient.sucursal_id,
            title=title,
            body=body,
            data=data,
            channel=channel,
            idempotency_key=build_idempotency_key(
                tenant_id=tenant_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                recipient_user_id=recipient.user_id,
                event_version=version,
            ),
        )
        if notification["delivery_status"] == DELIVERY_PENDING:
            notification = send_push_notification(notification)
        results.append(notification)
    return results


def _list_tenant_users_by_role(connection, role: str, *, sucursal_id: int | None = None) -> list[NotificationRecipient]:
    params: dict[str, object] = {"role": role}
    where = ["role = :role", "estado = 'activo'"]
    if sucursal_id is not None:
        where.append("sucursal_id = :sucursal_id")
        params["sucursal_id"] = sucursal_id
    rows = connection.execute(
        text(
            f"""
            SELECT id, email, full_name, sucursal_id
            FROM usuarios_tenant
            WHERE {' AND '.join(where)}
            ORDER BY full_name ASC, id ASC
            """
        ),
        params,
    ).mappings().all()
    return [
        NotificationRecipient(
            user_id=int(row["id"]),
            role=role,
            sucursal_id=int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
            email=str(row["email"]) if row.get("email") else None,
            name=str(row["full_name"]) if row.get("full_name") else None,
        )
        for row in rows
    ]


def _list_tenant_users_by_role_for_sucursales(
    connection,
    role: str,
    sucursal_ids: list[int] | None,
) -> list[NotificationRecipient]:
    if not sucursal_ids:
        return _list_tenant_users_by_role(connection, role)
    recipients: list[NotificationRecipient] = []
    for sucursal_id in sorted(set(int(value) for value in sucursal_ids)):
        recipients.extend(_list_tenant_users_by_role(connection, role, sucursal_id=sucursal_id))
    return recipients


def _get_client_recipient(connection, client_id: int | None) -> NotificationRecipient | None:
    if client_id is None:
        return None
    row = connection.execute(
        text("SELECT id, email, full_name FROM clients WHERE id = :id LIMIT 1"),
        {"id": client_id},
    ).mappings().first()
    if not row:
        return None
    return NotificationRecipient(
        user_id=int(row["id"]),
        role=ROLE_CLIENTE,
        email=str(row["email"]) if row.get("email") else None,
        name=str(row["full_name"]) if row.get("full_name") else None,
    )


def _list_available_technician_recipients(connection, sucursal_id: int | None) -> list[NotificationRecipient]:
    if sucursal_id is None:
        rows = connection.execute(
            text(
                """
                SELECT u.id AS usuario_tenant_id, u.email, u.full_name, t.sucursal_id
                FROM technicians t
                JOIN usuarios_tenant u
                  ON u.id = t.usuario_tenant_id
                WHERE t.status = 'disponible'
                  AND u.role = :role
                  AND u.estado = 'activo'
                ORDER BY u.full_name ASC, u.id ASC
                """
            ),
            {"role": ROLE_TECNICO},
        ).mappings().all()
    else:
        rows = connection.execute(
            text(
                """
                SELECT u.id AS usuario_tenant_id, u.email, u.full_name, t.sucursal_id
                FROM technicians t
                JOIN usuarios_tenant u
                  ON u.id = t.usuario_tenant_id
                WHERE t.sucursal_id = :sucursal_id
                  AND t.status = 'disponible'
                  AND u.role = :role
                  AND u.estado = 'activo'
                ORDER BY u.full_name ASC, u.id ASC
                """
            ),
            {"sucursal_id": sucursal_id, "role": ROLE_TECNICO},
        ).mappings().all()
    return [
        NotificationRecipient(
            user_id=int(row["usuario_tenant_id"]),
            role=ROLE_TECNICO,
            sucursal_id=int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
            email=str(row["email"]) if row.get("email") else None,
            name=str(row["full_name"]) if row.get("full_name") else None,
        )
        for row in rows
    ]


def _list_available_technician_recipients_for_sucursales(
    connection,
    sucursal_ids: list[int] | None,
) -> list[NotificationRecipient]:
    if not sucursal_ids:
        return _list_available_technician_recipients(connection, None)
    recipients: list[NotificationRecipient] = []
    for sucursal_id in sorted(set(int(value) for value in sucursal_ids)):
        recipients.extend(_list_available_technician_recipients(connection, sucursal_id))
    return recipients


def _get_assigned_technician_recipient(connection, technician_id: int | None) -> NotificationRecipient | None:
    if technician_id is None:
        return None
    row = connection.execute(
        text(
            """
            SELECT t.id, t.sucursal_id, u.id AS usuario_tenant_id, u.email, u.full_name
            FROM technicians t
            JOIN usuarios_tenant u
              ON u.id = t.usuario_tenant_id
            WHERE t.id = :technician_id
              AND u.role = :role
              AND u.estado = 'activo'
            LIMIT 1
            """
        ),
        {"technician_id": technician_id, "role": ROLE_TECNICO},
    ).mappings().first()
    if not row:
        return None
    return NotificationRecipient(
        user_id=int(row["usuario_tenant_id"]),
        role=ROLE_TECNICO,
        sucursal_id=int(row["sucursal_id"]) if row.get("sucursal_id") is not None else None,
        email=str(row["email"]) if row.get("email") else None,
        name=str(row["full_name"]) if row.get("full_name") else None,
    )


def notify_emergency_event(
    event_type: str,
    report: Mapping[str, object],
    *,
    event_source: str = "emergencies",
    extra_data: Mapping[str, object] | None = None,
    event_version: str | None = None,
) -> list[dict[str, object]]:
    ensure_system_notifications_schema()
    client_id = int(report["client_id"]) if report.get("client_id") is not None else None
    sucursal_id = int(report["sucursal_id"]) if report.get("sucursal_id") is not None else None
    assigned_technician_id = (
        int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None
    )
    entity_id = int(report["id"]) if report.get("id") is not None else None

    data = {
        "emergency_id": entity_id,
        "status": report.get("emergency_status"),
        "status_label": report.get("emergency_status"),
        "problem_type": report.get("problem_type_standardized") or report.get("problem_type"),
        "incident_description": report.get("description") or report.get("problem_type_standardized") or report.get("problem_type"),
        "workshop_id": report.get("nearest_workshop_id"),
        "workshop_name": report.get("nearest_workshop_name"),
        "technician_id": assigned_technician_id,
        "technician_name": report.get("assigned_technician_name"),
        "client_id": client_id,
    }
    if extra_data:
        data.update(dict(extra_data))
    matching_sucursal_ids = [
        int(value)
        for value in data.get("matching_sucursal_ids", [])
        if value is not None
    ] if isinstance(data.get("matching_sucursal_ids"), list) else []

    recipients: list[NotificationRecipient] = []
    with engine.connect() as connection:
        if event_type == "EMERGENCY_REGISTERED":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role_for_sucursales(connection, ROLE_ADMIN_SUCURSAL, matching_sucursal_ids or ([sucursal_id] if sucursal_id is not None else [])))
            recipients.extend(_list_available_technician_recipients_for_sucursales(connection, matching_sucursal_ids or ([sucursal_id] if sucursal_id is not None else [])))
            client_recipient = _get_client_recipient(connection, client_id)
            if client_recipient:
                recipients.append(client_recipient)
        elif event_type in {"REQUEST_ACCEPTED", "REQUEST_REJECTED", "SERVICE_STARTED", "SERVICE_FINISHED"}:
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
            client_recipient = _get_client_recipient(connection, client_id)
            if client_recipient:
                recipients.append(client_recipient)
        elif event_type == "TECHNICIAN_ASSIGNED":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
            client_recipient = _get_client_recipient(connection, client_id)
            technician_recipient = _get_assigned_technician_recipient(connection, assigned_technician_id)
            if client_recipient:
                recipients.append(client_recipient)
            if technician_recipient:
                recipients.append(technician_recipient)
        elif event_type in {"TECHNICIAN_ON_THE_WAY", "TECHNICIAN_ARRIVED"}:
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
            client_recipient = _get_client_recipient(connection, client_id)
            if client_recipient:
                recipients.append(client_recipient)
        elif event_type == "EMERGENCY_STATUS_CHANGED":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
            client_recipient = _get_client_recipient(connection, client_id)
            technician_recipient = _get_assigned_technician_recipient(connection, assigned_technician_id)
            if client_recipient:
                recipients.append(client_recipient)
            if technician_recipient:
                recipients.append(technician_recipient)
        elif event_type == "SERVICE_CANCELLED":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
            client_recipient = _get_client_recipient(connection, client_id)
            technician_recipient = _get_assigned_technician_recipient(connection, assigned_technician_id)
            if client_recipient:
                recipients.append(client_recipient)
            if technician_recipient:
                recipients.append(technician_recipient)

    return notify_event(
        event_type=event_type,
        event_source=event_source,
        entity_type="emergency",
        entity_id=entity_id,
        recipients=recipients,
        data=data,
        sucursal_id=sucursal_id,
        event_version=event_version,
    )


def notify_quotation_event(
    event_type: str,
    *,
    quotation_id: int,
    client_id: int | None = None,
    sucursal_id: int | None = None,
    workshop_id: int | None = None,
    workshop_name: str | None = None,
    offer_id: int | None = None,
    emergency_id: int | None = None,
    price: float | None = None,
    event_source: str = "quotations",
) -> list[dict[str, object]]:
    ensure_system_notifications_schema()
    price_label = f"Bs. {price:.2f}" if price is not None else None
    data = {
        "quotation_id": quotation_id,
        "offer_id": offer_id,
        "emergency_id": emergency_id,
        "workshop_id": workshop_id,
        "workshop_name": workshop_name,
        "client_id": client_id,
        "price": price,
        "price_label": price_label,
        "status_label": event_type.replace("_", " ").title(),
    }
    recipients: list[NotificationRecipient] = []
    with engine.connect() as connection:
        if event_type == "REQUEST_SENT_TO_WORKSHOPS":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))
        elif event_type == "QUOTATION_RECEIVED":
            client_recipient = _get_client_recipient(connection, client_id)
            if client_recipient:
                recipients.append(client_recipient)
        elif event_type == "QUOTATION_ACCEPTED":
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_SUPERADMIN_TENANT))
            recipients.extend(_list_tenant_users_by_role(connection, ROLE_ADMIN_SUCURSAL, sucursal_id=sucursal_id))

    return notify_event(
        event_type=event_type,
        event_source=event_source,
        entity_type="quotation_request",
        entity_id=quotation_id,
        recipients=recipients,
        data=data,
        sucursal_id=sucursal_id,
        event_version=str(offer_id or workshop_id or "default"),
    )


def _scope_clause(current_user: TokenPayload) -> tuple[str, dict[str, object]]:
    role = normalize_role(current_user.role)
    if role == ROLE_SUPERADMIN_GLOBAL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    if role == ROLE_SUPERADMIN_TENANT:
        return "1=1", {}
    if role == ROLE_ADMIN_SUCURSAL:
        return "sucursal_id = :scope_sucursal_id", {"scope_sucursal_id": current_user.sucursal_id}
    return (
        "recipient_user_id = :scope_user_id AND recipient_role = :scope_role",
        {
            "scope_user_id": current_user.user_id,
            "scope_role": role,
        },
    )


def list_notifications(
    *,
    current_user: TokenPayload,
    page: int,
    page_size: int,
    filters: Mapping[str, object],
) -> tuple[list[dict[str, object]], int]:
    ensure_system_notifications_schema()
    base_scope, params = _scope_clause(current_user)
    where = [base_scope]
    allowed_filters = {
        "recipient_user_id": "recipient_user_id = CAST(:recipient_user_id AS BIGINT)",
        "recipient_role": "recipient_role = :recipient_role",
        "event_type": "event_type = :event_type",
        "delivery_status": "delivery_status = :delivery_status",
        "read_status": "read_status = :read_status",
        "entity_type": "entity_type = :entity_type",
        "entity_id": "entity_id = CAST(:entity_id AS BIGINT)",
        "fecha_inicio": "created_at >= CAST(:fecha_inicio AS TIMESTAMPTZ)",
        "fecha_fin": "created_at <= CAST(:fecha_fin AS TIMESTAMPTZ)",
    }
    for key, clause in allowed_filters.items():
        value = filters.get(key)
        if value is None or value == "":
            continue
        where.append(clause)
        params[key] = value
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    sql_where = " AND ".join(where)
    with engine.connect() as connection:
        total = int(
            connection.execute(
                text(f"SELECT COUNT(*) FROM system_notifications WHERE {sql_where}"),
                params,
            ).scalar_one()
        )
        rows = connection.execute(
            text(
                f"""
                SELECT *
                FROM system_notifications
                WHERE {sql_where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
    return [dict(row) for row in rows], total


def get_notification_detail(notification_id: int, current_user: TokenPayload) -> dict[str, object]:
    ensure_system_notifications_schema()
    base_scope, params = _scope_clause(current_user)
    params["notification_id"] = notification_id
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT *
                FROM system_notifications
                WHERE id = :notification_id
                  AND {base_scope}
                LIMIT 1
                """
            ),
            params,
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    return dict(row)


def mark_as_read(notification_id: int, current_user: TokenPayload) -> dict[str, object]:
    _ = get_notification_detail(notification_id, current_user)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                UPDATE system_notifications
                SET read_status = 'read',
                    read_at = COALESCE(read_at, NOW())
                WHERE id = :notification_id
                RETURNING *
                """
            ),
            {"notification_id": notification_id},
        ).mappings().first()
    return dict(row)


def retry_failed_notification(notification_id: int, current_user: TokenPayload) -> dict[str, object]:
    notification = get_notification_detail(notification_id, current_user)
    if str(notification.get("delivery_status")) != DELIVERY_FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reenviar notificaciones fallidas.",
        )
    return send_push_notification(notification, is_retry=True)


def summarize_notifications(current_user: TokenPayload, filters: Mapping[str, object]) -> dict[str, object]:
    rows, total = list_notifications(current_user=current_user, page=1, page_size=5000, filters=filters)
    by_event: dict[str, int] = {}
    sent = failed = pending = skipped = read = unread = retried = 0
    for row in rows:
        by_event[str(row.get("event_type") or "UNKNOWN")] = by_event.get(str(row.get("event_type") or "UNKNOWN"), 0) + 1
        status_value = str(row.get("delivery_status") or "")
        read_value = str(row.get("read_status") or "")
        if status_value == DELIVERY_SENT:
            sent += 1
        elif status_value == DELIVERY_FAILED:
            failed += 1
        elif status_value == DELIVERY_PENDING:
            pending += 1
        elif status_value == DELIVERY_SKIPPED:
            skipped += 1
        elif status_value == DELIVERY_RETRIED:
            retried += 1
        if read_value == READ_READ:
            read += 1
        else:
            unread += 1
    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "pending": pending,
        "skipped": skipped,
        "retried": retried,
        "read": read,
        "unread": unread,
        "by_event_type": by_event,
    }


def audit_existing_push_tables() -> dict[str, object]:
    ensure_system_notifications_schema()
    with engine.connect() as connection:
        notification_count = int(connection.execute(text("SELECT COUNT(*) FROM notifications")).scalar_one())
        system_notification_count = int(connection.execute(text("SELECT COUNT(*) FROM system_notifications")).scalar_one())
    return {
        "legacy_notifications_table": "notifications",
        "legacy_notification_rows": notification_count,
        "system_notifications_table": "system_notifications",
        "system_notification_rows": system_notification_count,
    }
