import asyncio
import logging
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.db import (
    create_quotation_request_history,
    create_quotation_offer,
    create_quotation_request,
    create_quotation_request_workshop,
    get_active_quotation_request_by_emergency,
    get_contracted_service,
    get_emergency_report_by_id,
    get_quotation_offer_by_request_and_workshop,
    get_quotation_offer_by_id,
    get_quotation_request_by_id,
    get_quotation_request_workshop,
    get_workshop_by_id,
    list_contracted_services,
    list_contracted_services_by_tenant,
    list_quotation_offers_by_request,
    list_quotation_offers_by_tenant,
    list_quotation_offers_by_workshop,
    list_quotation_request_history,
    list_quotation_requests_by_client,
    list_quotation_requests_by_tenant,
    list_quotation_requests_by_workshop,
    list_rejected_offers_for_request,
    list_workshop_registrations,
    quotation_request_visible_in_sucursal,
    select_quotation_offer,
    update_quotation_offer,
    update_quotation_request_status,
)
from app.realtime import emit_realtime_events
from app.realtime_types import RealtimeEmitEvent
from app.services.notification_service import notify_quotation_event
from app.tenant_context import get_tenant
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    TokenPayload,
    calculate_distance_meters,
    get_current_user,
    normalize_optional_text,
    normalize_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["quotations"])

QUOTATION_VALID_STATUSES = {
    "abierto",
    "en_evaluacion",
    "con_propuestas",
    "seleccionado",
    "cancelado",
    "expirado",
}

BRANCH_SCOPED_ROLES = {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO}


# ── Pydantic models ────────────────────────────────────────────────────────────

class QuotationRequestCreate(BaseModel):
    emergency_id: int = Field(ge=1)
    client_id: int | None = Field(default=None, ge=1)
    max_workshops: int = Field(default=5, ge=1, le=20)
    expires_hours: int = Field(default=24, ge=1, le=168)


class SelectOfferRequest(BaseModel):
    offer_id: int = Field(ge=1)


class QuotationOfferCreate(BaseModel):
    workshop_id: int = Field(ge=1)
    price: float = Field(ge=0)
    service_description: str = Field(min_length=3, max_length=4000)
    workshop_rating: float | None = Field(default=None, ge=0, le=5)
    spare_parts: str | None = Field(default=None, max_length=4000)
    labor_detail: str | None = Field(default=None, max_length=4000)
    labor_cost: float | None = Field(default=None, ge=0)
    spare_parts_cost: float | None = Field(default=None, ge=0)
    estimated_service_time: str | None = Field(default=None, max_length=80)
    estimated_arrival_time: str | None = Field(default=None, max_length=80)
    warranty: str | None = Field(default=None, max_length=255)
    validity_days: int | None = Field(default=None, ge=1, le=365)
    observations: str | None = Field(default=None, max_length=4000)
    condiciones_servicio: str | None = Field(default=None, max_length=4000)


class QuotationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    emergency_id: int | None = None
    client_id: int | None = None
    status: str
    requested_workshops_count: int
    received_offers_count: int
    selected_offer_id: int | None = None
    requested_at: datetime
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class QuotationRequestWithInvitationResponse(QuotationRequestResponse):
    workshop_invitation_status: str | None = None
    notified_at: datetime | None = None
    client_name: str | None = None
    client_phone: str | None = None
    workshop_names: str | None = None
    visible_workshops_count: int | None = None
    selected_workshop_name: str | None = None
    selected_offer_price: float | None = None


class QuotationOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_request_id: int
    workshop_id: int
    workshop_name: str | None = None
    workshop_rating: float | None = None
    price: float | None = None
    service_description: str | None = None
    spare_parts: str | None = None
    labor_detail: str | None = None
    labor_cost: float | None = None
    spare_parts_cost: float | None = None
    estimated_service_time: str | None = None
    estimated_arrival_time: str | None = None
    warranty: str | None = None
    validity_days: int | None = None
    observations: str | None = None
    condiciones_servicio: str | None = None
    status: str
    created_at: datetime
    expires_at: datetime | None = None


class QuotationOfferHistorialResponse(QuotationOfferResponse):
    emergency_id: int | None = None
    request_status: str | None = None
    request_client_id: int | None = None
    client_name: str | None = None


class QuotationRequestDetailResponse(BaseModel):
    request: QuotationRequestResponse
    workshops_invited: int


class QuotationRequestHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_request_id: int
    event_type: str
    detail: str | None = None
    actor_role: str | None = None
    actor_user_id: int | None = None
    created_at: datetime


class ContractedServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Offer data
    id: int
    quotation_request_id: int
    workshop_id: int
    price: float | None = None
    service_description: str | None = None
    spare_parts: str | None = None
    labor_detail: str | None = None
    labor_cost: float | None = None
    spare_parts_cost: float | None = None
    estimated_service_time: str | None = None
    estimated_arrival_time: str | None = None
    warranty: str | None = None
    validity_days: int | None = None
    observations: str | None = None
    condiciones_servicio: str | None = None
    status: str
    offer_created_at: datetime | None = None
    offer_expires_at: datetime | None = None
    # Request data
    emergency_id: int | None = None
    client_id: int | None = None
    requested_at: datetime | None = None
    request_expires_at: datetime | None = None
    # Emergency data
    vehicle_name: str | None = None
    vehicle_plate: str | None = None
    problem_type: str | None = None
    address: str | None = None
    zone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    emergency_description: str | None = None
    emergency_status: str | None = None
    emergency_created_at: datetime | None = None
    hora_llegada: datetime | None = None
    latitud_llegada: float | None = None
    longitud_llegada: float | None = None
    # Client data
    client_name: str | None = None
    client_phone: str | None = None
    workshop_name: str | None = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_compatible_workshops(
    emergency: Mapping[str, object],
    max_workshops: int,
) -> list[dict[str, object]]:
    target_specialty = normalize_optional_text(
        str(emergency.get("problem_type_standardized") or emergency.get("problem_type") or "")
    )
    emergency_latitude = emergency.get("latitude")
    emergency_longitude = emergency.get("longitude")

    candidates: list[tuple[bool, float, dict[str, object]]] = []
    for workshop in list_workshop_registrations():
        if str(workshop.get("approval_status")) != "activo":
            continue
        if str(workshop.get("availability_status") or "disponible") != "disponible":
            continue
        workshop_latitude = workshop.get("latitude")
        workshop_longitude = workshop.get("longitude")
        if workshop_latitude is None or workshop_longitude is None:
            continue
        distance = (
            calculate_distance_meters(
                float(emergency_latitude),
                float(emergency_longitude),
                float(workshop_latitude),
                float(workshop_longitude),
            )
            if emergency_latitude is not None and emergency_longitude is not None
            else 0.0
        )
        specialties = [
            normalize_optional_text(str(value))
            for value in (workshop.get("specialties") or [])
            if normalize_optional_text(str(value)) is not None
        ]
        primary_specialty = normalize_optional_text(str(workshop.get("specialty"))) if workshop.get("specialty") else None
        if primary_specialty and primary_specialty not in specialties:
            specialties.insert(0, primary_specialty)
        specialty_match = (
            target_specialty is not None
            and any(specialty.casefold() == target_specialty.casefold() for specialty in specialties)
        )
        candidates.append((specialty_match, distance, workshop))

    candidates.sort(key=lambda item: (not item[0], item[1], int(item[2]["id"])))
    return [w for _, _, w in candidates[:max_workshops]]


def _get_request_or_404(quotation_id: int) -> dict[str, object]:
    try:
        record = get_quotation_request_by_id(quotation_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de cotización no encontrada")
    return record


def _ensure_workshop_scope(workshop_id: int, current_user: TokenPayload | None) -> None:
    if current_user is None or current_user.role not in BRANCH_SCOPED_ROLES:
        return
    workshop = get_workshop_by_id(workshop_id)
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if workshop.get("sucursal_id") != current_user.sucursal_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")


def _ensure_client_quotation_request_role(current_user: TokenPayload) -> str:
    role = _ensure_non_global_quotation_access(current_user)
    if role != ROLE_CLIENTE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO_CLIENTE_PUEDE_SOLICITAR_COTIZACION")
    return role


def _ensure_workshop_management_role(current_user: TokenPayload) -> str:
    role = _ensure_non_global_quotation_access(current_user)
    if role not in {ROLE_ADMIN_SUCURSAL, ROLE_SUPERADMIN_TENANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_GESTIONAR_COTIZACIONES")
    return role


def _ensure_non_global_quotation_access(current_user: TokenPayload) -> str:
    role = normalize_role(current_user.role)
    if role == ROLE_SUPERADMIN_GLOBAL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    return role


def _ensure_client_owner_scope(client_id: int, current_user: TokenPayload) -> str:
    role = _ensure_non_global_quotation_access(current_user)
    if role == ROLE_CLIENTE and client_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENT_ID_AJENO_NO_PERMITIDO")
    return role


def _ensure_quotation_request_scope(record: Mapping[str, object], current_user: TokenPayload) -> str:
    role = _ensure_non_global_quotation_access(current_user)
    record_client_id = int(record["client_id"]) if record.get("client_id") is not None else None
    if role == ROLE_CLIENTE:
        if record_client_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de cotización no encontrada")
        return role
    if role == ROLE_ADMIN_SUCURSAL:
        quotation_id = int(record["id"])
        if current_user.sucursal_id is None or not quotation_request_visible_in_sucursal(quotation_id, int(current_user.sucursal_id)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de cotización no encontrada")
        return role
    if role != ROLE_SUPERADMIN_TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_ESTA_CONSULTA")
    return role


def _tenant_quotation_scope(current_user: TokenPayload) -> tuple[int, int | None]:
    role = _ensure_non_global_quotation_access(current_user)
    if role == ROLE_SUPERADMIN_TENANT:
        if current_user.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TENANT_NO_RESUELTO")
        return int(current_user.tenant_id), None
    if role == ROLE_ADMIN_SUCURSAL:
        if current_user.tenant_id is None or current_user.sucursal_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SUCURSAL_NO_RESUELTA")
        return int(current_user.tenant_id), int(current_user.sucursal_id)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_ESTA_CONSULTA")


def _quotation_realtime_scope() -> tuple[int | None, str | None]:
    tenant = get_tenant()
    tenant_id = int(tenant["id"]) if tenant and tenant.get("id") is not None else None
    tenant_slug = str(tenant["slug"]) if tenant and tenant.get("slug") else None
    return tenant_id, tenant_slug


def _emit_quotation_realtime_events(
    event_type: str,
    request_record: Mapping[str, object],
    *,
    client_id: int | None = None,
    sucursal_ids: set[int] | None = None,
    payload: Mapping[str, object] | None = None,
) -> None:
    tenant_id, tenant_slug = _quotation_realtime_scope()
    if tenant_id is None or not tenant_slug:
        logger.warning("WS quotation event skipped event_type=%s quotation_id=%s tenant scope missing", event_type, request_record.get("id"))
        return

    quotation_id = int(request_record["id"])
    event_payload: dict[str, object] = {
        "quotation_id": quotation_id,
        "emergency_id": int(request_record["emergency_id"]) if request_record.get("emergency_id") is not None else None,
        "client_id": int(request_record["client_id"]) if request_record.get("client_id") is not None else None,
        "status": request_record.get("status"),
        "selected_offer_id": int(request_record["selected_offer_id"]) if request_record.get("selected_offer_id") is not None else None,
    }
    if payload:
        event_payload.update(payload)

    events: list[RealtimeEmitEvent] = [
        RealtimeEmitEvent(
            type=event_type,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            entity_type="quotation_request",
            entity_id=quotation_id,
            payload=event_payload,
        )
    ]

    for sucursal_id in sorted(sucursal_ids or set()):
        events.append(
            RealtimeEmitEvent(
                type=event_type,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                sucursal_id=sucursal_id,
                role_target=ROLE_ADMIN_SUCURSAL,
                entity_type="quotation_request",
                entity_id=quotation_id,
                payload=event_payload,
            )
        )

    effective_client_id = client_id if client_id is not None else (
        int(request_record["client_id"]) if request_record.get("client_id") is not None else None
    )
    if effective_client_id is not None:
        events.append(
            RealtimeEmitEvent(
                type=event_type,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                user_id=effective_client_id,
                role_target=ROLE_CLIENTE,
                entity_type="quotation_request",
                entity_id=quotation_id,
                payload=event_payload,
            )
        )

    try:
        asyncio.run(emit_realtime_events(events))
    except Exception:
        logger.exception("WS quotation emit failed event_type=%s quotation_id=%s", event_type, quotation_id)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    f"{settings.api_prefix}/cotizaciones/solicitar",
    response_model=QuotationRequestDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def solicitar_cotizacion(
    payload: QuotationRequestCreate,
    current_user: TokenPayload = Depends(get_current_user),
) -> QuotationRequestDetailResponse:
    _ensure_client_quotation_request_role(current_user)
    try:
        emergency = get_emergency_report_by_id(payload.emergency_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    client_id = int(emergency["client_id"]) if emergency.get("client_id") is not None else current_user.user_id
    emergency_client_id = int(emergency["client_id"]) if emergency.get("client_id") is not None else None
    if payload.client_id is not None and payload.client_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENT_ID_AJENO_NO_PERMITIDO")
    if emergency_client_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    try:
        existing_active = get_active_quotation_request_by_emergency(payload.emergency_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if existing_active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una solicitud de cotización activa para esta emergencia",
        )

    try:
        compatible_workshops = _find_compatible_workshops(emergency, payload.max_workshops)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_hours)

    try:
        quotation = create_quotation_request({
            "emergency_id": payload.emergency_id,
            "client_id": client_id,
            "requested_workshops_count": len(compatible_workshops),
            "expires_at": expires_at,
        })
        for workshop in compatible_workshops:
            create_quotation_request_workshop({
                "quotation_request_id": quotation["id"],
                "workshop_id": int(workshop["id"]),
            })
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    invited_sucursal_ids: set[int] = set()
    for workshop in compatible_workshops:
        if workshop.get("sucursal_id") is not None:
            invited_sucursal_ids.add(int(workshop["sucursal_id"]))
        try:
            notify_quotation_event(
                "REQUEST_SENT_TO_WORKSHOPS",
                quotation_id=int(quotation["id"]),
                workshop_id=int(workshop["id"]),
                workshop_name=str(workshop.get("workshop_name") or workshop.get("name") or ""),
                emergency_id=payload.emergency_id,
                sucursal_id=int(workshop["sucursal_id"]) if workshop.get("sucursal_id") is not None else None,
            )
        except Exception:
            logger.exception("No se pudo registrar/enviar REQUEST_SENT_TO_WORKSHOPS al taller %s", workshop["id"])

    _emit_quotation_realtime_events(
        "quotation_requested",
        quotation,
        client_id=client_id,
        sucursal_ids=invited_sucursal_ids,
        payload={"requested_workshops_count": len(compatible_workshops)},
    )

    return QuotationRequestDetailResponse(
        request=QuotationRequestResponse.model_validate(quotation),
        workshops_invited=len(compatible_workshops),
    )


@router.get(
    f"{settings.api_prefix}/cotizaciones/cliente/{{client_id}}",
    response_model=list[QuotationRequestResponse],
)
def listar_cotizaciones_cliente(
    client_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationRequestResponse]:
    _ensure_client_owner_scope(client_id, current_user)
    try:
        rows = list_quotation_requests_by_client(client_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationRequestResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/taller/{{workshop_id}}",
    response_model=list[QuotationRequestWithInvitationResponse],
)
def listar_cotizaciones_taller(
    workshop_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationRequestWithInvitationResponse]:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(workshop_id, current_user)
    try:
        rows = list_quotation_requests_by_workshop(workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationRequestWithInvitationResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/tenant/solicitudes",
    response_model=list[QuotationRequestWithInvitationResponse],
)
def listar_cotizaciones_tenant(
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationRequestWithInvitationResponse]:
    tenant_id, sucursal_id = _tenant_quotation_scope(current_user)
    try:
        rows = list_quotation_requests_by_tenant(tenant_id, sucursal_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationRequestWithInvitationResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/taller/{{workshop_id}}/historial",
    response_model=list[QuotationOfferHistorialResponse],
)
def historial_ofertas_taller(
    workshop_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationOfferHistorialResponse]:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(workshop_id, current_user)
    try:
        rows = list_quotation_offers_by_workshop(workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationOfferHistorialResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/tenant/historial",
    response_model=list[QuotationOfferHistorialResponse],
)
def historial_ofertas_tenant(
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationOfferHistorialResponse]:
    tenant_id, sucursal_id = _tenant_quotation_scope(current_user)
    try:
        rows = list_quotation_offers_by_tenant(tenant_id, sucursal_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationOfferHistorialResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}",
    response_model=QuotationRequestResponse,
)
def obtener_cotizacion(
    quotation_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> QuotationRequestResponse:
    record = _get_request_or_404(quotation_id)
    _ensure_quotation_request_scope(record, current_user)
    return QuotationRequestResponse.model_validate(record)


@router.get(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}/propuestas",
    response_model=list[QuotationOfferResponse],
)
def listar_propuestas(
    quotation_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationOfferResponse]:
    record = _get_request_or_404(quotation_id)
    _ensure_quotation_request_scope(record, current_user)
    try:
        rows = list_quotation_offers_by_request(quotation_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationOfferResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}/historial",
    response_model=list[QuotationRequestHistoryResponse],
)
def listar_historial_cotizacion(
    quotation_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[QuotationRequestHistoryResponse]:
    record = _get_request_or_404(quotation_id)
    _ensure_quotation_request_scope(record, current_user)
    try:
        rows = list_quotation_request_history(quotation_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [QuotationRequestHistoryResponse.model_validate(row) for row in rows]


@router.post(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}/propuestas",
    response_model=QuotationOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_propuesta(
    quotation_id: int,
    payload: QuotationOfferCreate,
    current_user: TokenPayload = Depends(get_current_user),
) -> QuotationOfferResponse:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(payload.workshop_id, current_user)
    record = _get_request_or_404(quotation_id)
    request_expires_at = record.get("expires_at")
    now = datetime.now(timezone.utc)
    if isinstance(request_expires_at, datetime) and request_expires_at <= now:
        try:
            update_quotation_request_status(quotation_id, "expirado")
            create_quotation_request_history(
                {
                    "quotation_request_id": quotation_id,
                    "event_type": "solicitud_expirada",
                    "detail": "La solicitud expiró antes del registro de una nueva cotización",
                    "actor_role": "system",
                    "actor_user_id": None,
                }
            )
        except OperationalError:
            logger.exception("No se pudo marcar como expirada la solicitud %s", quotation_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud de cotización ya expiró y no admite nuevas propuestas",
        )
    if str(record.get("status")) in {"seleccionado", "cancelado", "expirado"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede agregar propuestas a una solicitud en estado '{record['status']}'",
        )
    try:
        workshop = get_workshop_by_id(payload.workshop_id)
        invitation = get_quotation_request_workshop(quotation_id, payload.workshop_id)
        existing_offer = get_quotation_offer_by_request_and_workshop(quotation_id, payload.workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller no fue invitado a esta solicitud de cotización",
        )
    if existing_offer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El taller ya registró una cotización para esta solicitud",
        )
    validity_days = payload.validity_days or 3
    expires_at = now + timedelta(days=validity_days)
    if isinstance(request_expires_at, datetime) and expires_at > request_expires_at:
        expires_at = request_expires_at
    try:
        offer = create_quotation_offer(
            quotation_id,
            {
                "workshop_id": payload.workshop_id,
                "workshop_rating": payload.workshop_rating,
                "price": payload.price,
                "service_description": normalize_optional_text(payload.service_description),
                "spare_parts": normalize_optional_text(payload.spare_parts),
                "labor_detail": normalize_optional_text(payload.labor_detail),
                "labor_cost": payload.labor_cost,
                "spare_parts_cost": payload.spare_parts_cost,
                "estimated_service_time": normalize_optional_text(payload.estimated_service_time),
                "estimated_arrival_time": normalize_optional_text(payload.estimated_arrival_time),
                "warranty": normalize_optional_text(payload.warranty),
                "validity_days": validity_days,
                "observations": normalize_optional_text(payload.observations),
                "condiciones_servicio": normalize_optional_text(payload.condiciones_servicio),
                "expires_at": expires_at,
            },
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cotización registrada por este taller para la solicitud indicada",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    client_id_raw = record.get("client_id")
    workshop_label = str(offer.get("workshop_name") or payload.workshop_id)
    try:
        notify_quotation_event(
            "QUOTATION_RECEIVED",
            quotation_id=quotation_id,
            client_id=int(client_id_raw) if client_id_raw is not None else None,
            offer_id=int(offer["id"]) if offer.get("id") is not None else None,
            emergency_id=int(record["emergency_id"]) if record.get("emergency_id") is not None else None,
            workshop_name=workshop_label,
            price=float(offer["price"]) if offer.get("price") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo registrar/enviar QUOTATION_RECEIVED para quotation %s", quotation_id)

    offer_sucursal_id = int(workshop["sucursal_id"]) if workshop.get("sucursal_id") is not None else None
    _emit_quotation_realtime_events(
        "quotation_submitted",
        record,
        sucursal_ids={offer_sucursal_id} if offer_sucursal_id is not None else None,
        payload={
            "offer_id": int(offer["id"]) if offer.get("id") is not None else None,
            "workshop_id": payload.workshop_id,
            "sucursal_id": offer_sucursal_id,
            "price": float(offer["price"]) if offer.get("price") is not None else None,
        },
    )

    return QuotationOfferResponse.model_validate(offer)


@router.put(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}/propuestas/{{offer_id}}",
    response_model=QuotationOfferResponse,
)
def actualizar_propuesta(
    quotation_id: int,
    offer_id: int,
    payload: QuotationOfferCreate,
    current_user: TokenPayload = Depends(get_current_user),
) -> QuotationOfferResponse:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(payload.workshop_id, current_user)
    record = _get_request_or_404(quotation_id)
    request_expires_at = record.get("expires_at")
    now = datetime.now(timezone.utc)
    if str(record.get("status")) in {"seleccionado", "cancelado", "expirado"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede actualizar una propuesta para una solicitud en estado '{record['status']}'",
        )
    try:
        workshop = get_workshop_by_id(payload.workshop_id)
        invitation = get_quotation_request_workshop(quotation_id, payload.workshop_id)
        existing_offer = get_quotation_offer_by_request_and_workshop(quotation_id, payload.workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller no fue invitado a esta solicitud de cotización",
        )
    if not existing_offer or int(existing_offer["id"]) != offer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cotización indicada no pertenece a esta solicitud o a este taller",
        )
    if str(existing_offer.get("status")) in {"aceptada", "rechazada", "expirado"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede actualizar una cotización en estado '{existing_offer['status']}'",
        )
    validity_days = payload.validity_days or 3
    expires_at = now + timedelta(days=validity_days)
    if isinstance(request_expires_at, datetime) and expires_at > request_expires_at:
        expires_at = request_expires_at
    try:
        offer = update_quotation_offer(
            quotation_id,
            offer_id,
            {
                "workshop_id": payload.workshop_id,
                "workshop_rating": payload.workshop_rating,
                "price": payload.price,
                "service_description": normalize_optional_text(payload.service_description),
                "spare_parts": normalize_optional_text(payload.spare_parts),
                "labor_detail": normalize_optional_text(payload.labor_detail),
                "labor_cost": payload.labor_cost,
                "spare_parts_cost": payload.spare_parts_cost,
                "estimated_service_time": normalize_optional_text(payload.estimated_service_time),
                "estimated_arrival_time": normalize_optional_text(payload.estimated_arrival_time),
                "warranty": normalize_optional_text(payload.warranty),
                "validity_days": validity_days,
                "observations": normalize_optional_text(payload.observations),
                "condiciones_servicio": normalize_optional_text(payload.condiciones_servicio),
                "expires_at": expires_at,
            },
        )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se pudo actualizar la cotización")

    client_id_raw = record.get("client_id")
    workshop_label = str(offer.get("workshop_name") or payload.workshop_id)
    try:
        notify_quotation_event(
            "QUOTATION_RECEIVED",
            quotation_id=quotation_id,
            client_id=int(client_id_raw) if client_id_raw is not None else None,
            offer_id=offer_id,
            emergency_id=int(record["emergency_id"]) if record.get("emergency_id") is not None else None,
            workshop_name=workshop_label,
            price=float(offer["price"]) if offer.get("price") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo registrar/enviar QUOTATION_RECEIVED para actualización quotation %s", quotation_id)

    offer_sucursal_id = int(workshop["sucursal_id"]) if workshop.get("sucursal_id") is not None else None
    _emit_quotation_realtime_events(
        "quotation_submitted",
        record,
        sucursal_ids={offer_sucursal_id} if offer_sucursal_id is not None else None,
        payload={
            "offer_id": int(offer["id"]) if offer.get("id") is not None else offer_id,
            "workshop_id": payload.workshop_id,
            "sucursal_id": offer_sucursal_id,
            "price": float(offer["price"]) if offer.get("price") is not None else None,
        },
    )

    return QuotationOfferResponse.model_validate(offer)


@router.post(
    f"{settings.api_prefix}/cotizaciones/{{quotation_id}}/seleccionar-propuesta",
    response_model=QuotationRequestResponse,
)
def seleccionar_propuesta(
    quotation_id: int,
    payload: SelectOfferRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> QuotationRequestResponse:
    record = _get_request_or_404(quotation_id)
    role = _ensure_quotation_request_scope(record, current_user)
    if role != ROLE_CLIENTE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO_CLIENTE_PUEDE_SELECCIONAR_PROPUESTA")
    if str(record.get("status")) == "seleccionado":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una propuesta seleccionada para esta solicitud")
    if str(record.get("status")) in {"cancelado", "expirado"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"No se puede seleccionar una propuesta en estado '{record['status']}'")
    try:
        offer = get_quotation_offer_by_id(payload.offer_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not offer or int(offer["quotation_request_id"]) != quotation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propuesta no encontrada para esta solicitud")
    try:
        updated = select_quotation_offer(quotation_id, payload.offer_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo seleccionar la propuesta, verifique el estado de la solicitud")

    emergency_id = int(record["emergency_id"]) if record.get("emergency_id") is not None else None
    winning_workshop_id = int(offer["workshop_id"])

    # Historial: taller seleccionado
    try:
        create_quotation_request_history({
            "quotation_request_id": quotation_id,
            "event_type": "taller_seleccionado",
            "detail": f"El taller #{winning_workshop_id} fue seleccionado (oferta #{payload.offer_id})",
            "actor_role": "client",
            "actor_user_id": updated.get("client_id"),
        })
    except Exception:
        logger.exception("No se pudo registrar historial taller_seleccionado para quotation %s", quotation_id)

    try:
        notify_quotation_event(
            "QUOTATION_ACCEPTED",
            quotation_id=quotation_id,
            workshop_id=winning_workshop_id,
            emergency_id=emergency_id,
            sucursal_id=int(offer["sucursal_id"]) if offer.get("sucursal_id") is not None else None,
            workshop_name=str(offer.get("workshop_name") or winning_workshop_id),
            price=float(offer["price"]) if offer.get("price") is not None else None,
            offer_id=int(offer["id"]) if offer.get("id") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo registrar/enviar QUOTATION_ACCEPTED para quotation %s", quotation_id)

    accepted_sucursal_id = int(offer["sucursal_id"]) if offer.get("sucursal_id") is not None else None
    _emit_quotation_realtime_events(
        "quotation_accepted",
        updated,
        sucursal_ids={accepted_sucursal_id} if accepted_sucursal_id is not None else None,
        payload={
            "offer_id": int(offer["id"]) if offer.get("id") is not None else None,
            "workshop_id": winning_workshop_id,
            "sucursal_id": accepted_sucursal_id,
            "price": float(offer["price"]) if offer.get("price") is not None else None,
        },
    )

    return QuotationRequestResponse.model_validate(updated)


@router.get(
    f"{settings.api_prefix}/cotizaciones/taller/{{workshop_id}}/servicios-contratados",
    response_model=list[ContractedServiceResponse],
)
def listar_servicios_contratados(
    workshop_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ContractedServiceResponse]:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(workshop_id, current_user)
    try:
        rows = list_contracted_services(workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [ContractedServiceResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/tenant/servicios-contratados",
    response_model=list[ContractedServiceResponse],
)
def listar_servicios_contratados_tenant(
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ContractedServiceResponse]:
    tenant_id, sucursal_id = _tenant_quotation_scope(current_user)
    try:
        rows = list_contracted_services_by_tenant(tenant_id, sucursal_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [ContractedServiceResponse.model_validate(row) for row in rows]


@router.get(
    f"{settings.api_prefix}/cotizaciones/taller/{{workshop_id}}/servicios-contratados/{{offer_id}}",
    response_model=ContractedServiceResponse,
)
def obtener_servicio_contratado(
    workshop_id: int,
    offer_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> ContractedServiceResponse:
    _ensure_workshop_management_role(current_user)
    _ensure_workshop_scope(workshop_id, current_user)
    try:
        row = get_contracted_service(offer_id, workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio contratado no encontrado")
    return ContractedServiceResponse.model_validate(row)
