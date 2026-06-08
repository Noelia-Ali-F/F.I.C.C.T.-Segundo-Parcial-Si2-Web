from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.services.notification_service import (
    get_notification_detail,
    list_notifications,
    mark_as_read,
    retry_failed_notification,
    summarize_notifications,
)
from app.utils import TokenPayload, get_current_user

router = APIRouter(tags=["notifications"])


class NotificationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int | None = None
    tenant_slug: str | None = None
    sucursal_id: int | None = None
    recipient_user_id: int
    recipient_role: str
    recipient_email: str | None = None
    recipient_name: str | None = None
    event_type: str
    event_source: str
    entity_type: str
    entity_id: int | None = None
    title: str
    body: str
    data_json: str | None = None
    channel: str
    delivery_status: str
    read_status: str
    error_code: str | None = None
    error_message: str | None = None
    fcm_token_id: int | None = None
    fcm_message_id: str | None = None
    retry_count: int
    idempotency_key: str
    created_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    failed_at: datetime | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationRecordResponse]
    total: int
    page: int
    page_size: int


class NotificationSummaryResponse(BaseModel):
    total: int
    sent: int
    failed: int
    pending: int
    skipped: int
    retried: int
    read: int
    unread: int
    by_event_type: dict[str, int] = Field(default_factory=dict)


def _filters(
    *,
    fecha_inicio: datetime | None,
    fecha_fin: datetime | None,
    recipient_user_id: int | None,
    recipient_role: str | None,
    event_type: str | None,
    delivery_status: str | None,
    read_status: str | None,
    entity_type: str | None,
    entity_id: int | None,
) -> dict[str, object]:
    return {
        "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio is not None else None,
        "fecha_fin": fecha_fin.isoformat() if fecha_fin is not None else None,
        "recipient_user_id": recipient_user_id,
        "recipient_role": recipient_role,
        "event_type": event_type,
        "delivery_status": delivery_status,
        "read_status": read_status,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }


@router.get(
    f"{settings.api_prefix}/notificaciones",
    response_model=NotificationListResponse,
)
def listar_notificaciones(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    fecha_inicio: datetime | None = Query(default=None),
    fecha_fin: datetime | None = Query(default=None),
    recipient_user_id: int | None = Query(default=None, ge=1),
    recipient_role: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    delivery_status: str | None = Query(default=None),
    read_status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> NotificationListResponse:
    rows, total = list_notifications(
        current_user=current_user,
        page=page,
        page_size=page_size,
        filters=_filters(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            event_type=event_type,
            delivery_status=delivery_status,
            read_status=read_status,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
    )
    return NotificationListResponse(
        items=[NotificationRecordResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    f"{settings.api_prefix}/notificaciones/resumen",
    response_model=NotificationSummaryResponse,
)
def resumen_notificaciones(
    fecha_inicio: datetime | None = Query(default=None),
    fecha_fin: datetime | None = Query(default=None),
    recipient_user_id: int | None = Query(default=None, ge=1),
    recipient_role: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    delivery_status: str | None = Query(default=None),
    read_status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> NotificationSummaryResponse:
    summary = summarize_notifications(
        current_user=current_user,
        filters=_filters(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            event_type=event_type,
            delivery_status=delivery_status,
            read_status=read_status,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
    )
    return NotificationSummaryResponse.model_validate(summary)


@router.get(
    f"{settings.api_prefix}/notificaciones/{{notification_id}}",
    response_model=NotificationRecordResponse,
)
def obtener_notificacion(
    notification_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> NotificationRecordResponse:
    return NotificationRecordResponse.model_validate(
        get_notification_detail(notification_id, current_user)
    )


@router.patch(
    f"{settings.api_prefix}/notificaciones/{{notification_id}}/read",
    response_model=NotificationRecordResponse,
)
def marcar_notificacion_leida(
    notification_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> NotificationRecordResponse:
    return NotificationRecordResponse.model_validate(
        mark_as_read(notification_id, current_user)
    )


@router.post(
    f"{settings.api_prefix}/notificaciones/{{notification_id}}/reenviar",
    response_model=NotificationRecordResponse,
)
def reenviar_notificacion(
    notification_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> NotificationRecordResponse:
    return NotificationRecordResponse.model_validate(
        retry_failed_notification(notification_id, current_user)
    )
