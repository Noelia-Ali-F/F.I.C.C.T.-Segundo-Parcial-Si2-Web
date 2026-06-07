import logging
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.db import (
    create_notification,
    create_quotation_request_history,
    create_quotation_offer,
    create_quotation_request,
    create_quotation_request_workshop,
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
    send_quotation_offer_not_selected,
    send_quotation_offer_received,
    send_quotation_offer_selected,
    send_quotation_request_sent,
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
    role = _ensure_non_global_quotation_access(current_user)
    try:
        emergency = get_emergency_report_by_id(payload.emergency_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not emergency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")

    client_id = payload.client_id or (int(emergency["client_id"]) if emergency.get("client_id") is not None else None)
    emergency_client_id = int(emergency["client_id"]) if emergency.get("client_id") is not None else None
    if role == ROLE_CLIENTE:
        if client_id != current_user.user_id or emergency_client_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENT_ID_AJENO_NO_PERMITIDO")

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

    # FCM: notificar a cada taller invitado
    for workshop in compatible_workshops:
        try:
            send_quotation_request_sent(
                workshop_id=int(workshop["id"]),
                quotation_id=int(quotation["id"]),
                emergency_id=payload.emergency_id,
                status="abierto",
            )
        except Exception:
            logger.exception("No se pudo enviar FCM quotation_request_sent al taller %s", workshop["id"])

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
    _ensure_non_global_quotation_access(current_user)
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
    _ensure_non_global_quotation_access(current_user)
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
    _ensure_non_global_quotation_access(current_user)
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

    # Notificación en BD + FCM al cliente
    client_id_raw = record.get("client_id")
    workshop_label = str(offer.get("workshop_name") or payload.workshop_id)
    price_label = f"Bs. {offer['price']:.2f}" if offer.get("price") is not None else "—"
    if client_id_raw is not None:
        try:
            import json as _json
            create_notification({
                "user_id": int(client_id_raw),
                "title": "Nueva cotización recibida",
                "message": f"Un taller ha enviado una propuesta para tu emergencia. Precio: {price_label}",
                "payload_json": _json.dumps({
                    "quotation_id": quotation_id,
                    "offer_id": offer["id"],
                    "workshop_name": workshop_label,
                    "price": str(offer.get("price") or ""),
                }),
            })
        except Exception:
            logger.exception("No se pudo guardar notificación en BD para quotation %s", quotation_id)
    try:
        send_quotation_offer_received(
            client_id=int(client_id_raw) if client_id_raw is not None else None,
            quotation_id=quotation_id,
            emergency_id=int(record["emergency_id"]) if record.get("emergency_id") is not None else None,
            workshop_name=workshop_label,
            price=float(offer["price"]) if offer.get("price") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo enviar FCM quotation_offer_received para quotation %s", quotation_id)

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
    _ensure_non_global_quotation_access(current_user)
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
    price_label = f"Bs. {offer['price']:.2f}" if offer.get("price") is not None else "—"
    if client_id_raw is not None:
        try:
            import json as _json
            create_notification({
                "user_id": int(client_id_raw),
                "title": "Cotización actualizada",
                "message": f"Un taller actualizó su propuesta para tu emergencia. Precio: {price_label}",
                "payload_json": _json.dumps({
                    "quotation_id": quotation_id,
                    "offer_id": offer_id,
                    "workshop_name": workshop_label,
                    "price": str(offer.get("price") or ""),
                }),
            })
        except Exception:
            logger.exception("No se pudo guardar notificación en BD para actualización quotation %s", quotation_id)
    try:
        send_quotation_offer_received(
            client_id=int(client_id_raw) if client_id_raw is not None else None,
            quotation_id=quotation_id,
            emergency_id=int(record["emergency_id"]) if record.get("emergency_id") is not None else None,
            workshop_name=workshop_label,
            price=float(offer["price"]) if offer.get("price") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo enviar FCM quotation_offer_received para actualización quotation %s", quotation_id)

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

    # FCM: notificar al taller ganador que su propuesta fue seleccionada
    try:
        send_quotation_offer_selected(
            workshop_id=winning_workshop_id,
            quotation_id=quotation_id,
            emergency_id=emergency_id,
            price=float(offer["price"]) if offer.get("price") is not None else None,
        )
    except Exception:
        logger.exception("No se pudo enviar FCM quotation_offer_selected para quotation %s", quotation_id)

    # FCM: notificar a los talleres rechazados
    try:
        rejected = list_rejected_offers_for_request(quotation_id)
        for rejected_offer in rejected:
            rejected_workshop_id = int(rejected_offer["workshop_id"])
            if rejected_workshop_id != winning_workshop_id:
                try:
                    send_quotation_offer_not_selected(
                        workshop_id=rejected_workshop_id,
                        quotation_id=quotation_id,
                        emergency_id=emergency_id,
                    )
                except Exception:
                    logger.exception(
                        "No se pudo enviar FCM quotation_offer_not_selected a workshop %s quotation %s",
                        rejected_workshop_id, quotation_id,
                    )
    except Exception:
        logger.exception("No se pudo notificar talleres rechazados para quotation %s", quotation_id)

    return QuotationRequestResponse.model_validate(updated)


@router.get(
    f"{settings.api_prefix}/cotizaciones/taller/{{workshop_id}}/servicios-contratados",
    response_model=list[ContractedServiceResponse],
)
def listar_servicios_contratados(
    workshop_id: int,
    current_user: TokenPayload = Depends(get_current_user),
) -> list[ContractedServiceResponse]:
    _ensure_non_global_quotation_access(current_user)
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
    _ensure_non_global_quotation_access(current_user)
    _ensure_workshop_scope(workshop_id, current_user)
    try:
        row = get_contracted_service(offer_id, workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio contratado no encontrado")
    return ContractedServiceResponse.model_validate(row)
