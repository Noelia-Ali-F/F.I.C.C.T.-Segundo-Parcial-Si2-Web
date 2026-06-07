import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError

from app.utils import (
    EMERGENCY_STATUS_NOTIFICATION_LABELS,
    MAX_EMERGENCY_PHOTOS,
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    TokenPayload,
    add_coordinate_pair,
    calculate_distance_meters,
    classify_emergency_photos,
    cleanup_uploaded_files,
    compact_push_text,
    determine_standardized_problem_type,
    emergency_incident_label,
    ensure_client_exists,
    get_effective_technician_id,
    get_current_user,
    get_tenant_id_for_query,
    normalize_emergency_media_fields,
    normalize_optional_text,
    normalize_plate,
    normalize_problem_type,
    normalize_role,
    resolve_emergency_price,
    save_emergency_audio,
    send_emergency_reassigned_notification,
    save_emergency_photo,
    send_emergency_rejected_notification,
    send_emergency_status_update_notification,
    send_push_to_client,
    transcribe_emergency_audio,
)
from app.config import settings
from app.db import (
    assign_emergency_technician,
    clear_emergency_assignment,
    create_emergency_report,
    create_emergency_tracking_point,
    create_emergency_status_history,
    delete_emergency_report,
    get_emergency_report_by_id,
    get_emergency_report_by_local_id,
    get_latest_emergency_tracking_point,
    get_technician_by_workshop,
    get_workshop_by_id,
    list_emergency_reports,
    list_emergency_reports_by_tenant,
    list_emergency_status_history,
    list_technicians_by_workshop,
    list_workshop_registrations,
    reassign_emergency_report_to_workshop,
    update_emergency_status,
)
from app.realtime import emit_realtime_events
from app.realtime_types import RealtimeEmitEvent
from app.tenant_context import get_tenant

logger = logging.getLogger(__name__)
LEGACY_EMERGENCY_STATUSES = {"pendiente", "activo", "rechazado"}
TIMELINE_EMERGENCY_STATUSES = {
    "solicitud_recibida",
    "en_revision",
    "auxilio_asignado",
    "auxilio_en_camino",
    "tecnico_en_sitio",
    "servicio_en_proceso",
    "servicio_finalizado",
    "solicitud_cancelada",
}
SUPPORTED_EMERGENCY_STATUSES = LEGACY_EMERGENCY_STATUSES | TIMELINE_EMERGENCY_STATUSES
EMERGENCY_TIMELINE_NOTIFICATION_STATUSES = set(EMERGENCY_STATUS_NOTIFICATION_LABELS)
EMERGENCY_STATUS_REALTIME_EVENT_TYPES = {
    "auxilio_en_camino": "technician_on_the_way",
    "tecnico_en_sitio": "technician_on_site",
    "servicio_en_proceso": "service_started",
    "servicio_finalizado": "service_finished",
}

# =========================================================
# ARCHIVO DE RUTAS DE EMERGENCIAS
# Aqui esta todo lo relacionado con las emergencias reportadas por clientes.
# Este archivo contiene:
# - modelos de respuesta y actualizacion de emergencias
# - logica para registrar emergencias con fotos y audio
# - logica para cambiar estado de la emergencia
# - logica para asignar un tecnico a una emergencia
# - controladores HTTP del modulo emergencias
# Palabras clave para buscar despues:
# EMERGENCIAS, EMERGENCIES, ASIGNAR TECNICO, ESTADO EMERGENCIA, AUDIO, FOTOS
# =========================================================
router = APIRouter(tags=["emergencies"])


class EmergencyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    local_id: str | None = None
    client_id: int | None = None
    client_name: str | None = None
    vehicle_name: str
    vehicle_plate: str
    problem_type: str
    price: int | None = None
    emergency_status: str | None = None
    problem_type_standardized: str | None = None
    photo_problem_type_standardized: str | None = None
    photo_classification_confidence: float | None = None
    photo_classification_error: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    zone: str | None = None
    sucursal_id: int | None = None
    nearest_workshop_id: int | None = None
    nearest_workshop_name: str | None = None
    nearest_workshop_specialty: str | None = None
    nearest_workshop_zone: str | None = None
    nearest_workshop_distance_meters: float | None = None
    audio_duration_seconds: float | None = None
    audio_transcript: str | None = None
    audio_transcript_status: str | None = None
    audio_transcript_error: str | None = None
    photo_paths: list[str] = Field(default_factory=list)
    photo_urls: list[str] = Field(default_factory=list)
    audio_path: str | None = None
    audio_url: str | None = None
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    hora_llegada: datetime | None = None
    latitud_llegada: float | None = None
    longitud_llegada: float | None = None
    created_at: datetime
    updated_at: datetime | None = None
    assignment_id: int | None = None
    assignment_status: str | None = None
    assigned_technician_id: int | None = None
    assigned_technician_name: str | None = None
    assigned_technician_phone: str | None = None
    assigned_technician_email: str | None = None
    assigned_technician_specialty: str | None = None


class EmergencyReportListResponse(EmergencyReportResponse):
    client_name: str | None = None


class EmergencyStatusUpdate(BaseModel):
    emergency_status: str = Field(pattern="^(activo|rechazado)$")


class EmergencyTechnicianAssignmentRequest(BaseModel):
    technician_id: int = Field(ge=1)


class EmergencyTimelineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    observation: str | None = None
    changed_by_role: str | None = None
    changed_by_user_id: int | None = None
    created_at: datetime


class EmergencyTimelineResponse(BaseModel):
    emergency_id: int
    current_status: str | None = None
    timeline: list[EmergencyTimelineItemResponse] = Field(default_factory=list)


class EmergencyTimelineStatusUpdate(BaseModel):
    estado: str = Field(min_length=3, max_length=50)
    observacion: str | None = Field(default=None, max_length=4000)
    latitud_llegada: float | None = Field(default=None)
    longitud_llegada: float | None = Field(default=None)


class EmergencyRejectRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=4000)
    changed_by_role: str | None = Field(default=None, max_length=50)
    changed_by_user_id: int | None = Field(default=None, ge=0)


class EmergencyRejectionResponse(BaseModel):
    emergency: EmergencyReportResponse
    timeline: EmergencyTimelineResponse


class AlternativeWorkshopCandidate(BaseModel):
    id: int
    workshop_name: str
    specialty: str | None = None
    zone: str | None = None
    latitude: float
    longitude: float
    distance_meters: float
    specialty_match: bool = False


class EmergencyTrackingActorResponse(BaseModel):
    id: int | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    last_location_at: datetime | None = None


class EmergencyTrackingRouteResponse(BaseModel):
    distance_meters: float
    distance_text: str
    duration_seconds: int
    duration_text: str
    polyline: list[list[float]] | None = None
    provider: str


class EmergencyTrackingResponse(BaseModel):
    emergency_id: int
    client: EmergencyTrackingActorResponse
    workshop: EmergencyTrackingActorResponse
    technician: EmergencyTrackingActorResponse
    route: EmergencyTrackingRouteResponse
    status: str


class EmergencyTrackingLocationRequest(BaseModel):
    technician_id: int = Field(ge=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: str | None = Field(default="system", max_length=50)


def _emergency_realtime_scope(report: Mapping[str, object]) -> tuple[int | None, str | None]:
    tenant = get_tenant()
    tenant_id = int(tenant["id"]) if tenant and tenant.get("id") is not None else None
    tenant_slug = str(tenant["slug"]) if tenant and tenant.get("slug") else None

    record_tenant = report.get("tenant_id")
    if tenant_id is None and record_tenant is not None:
        tenant_id = int(record_tenant)
    record_slug = report.get("tenant_slug")
    if tenant_slug is None and record_slug:
        tenant_slug = str(record_slug)

    return tenant_id, tenant_slug


def _build_emergency_event_payload(
    report: Mapping[str, object],
    *,
    extra_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "emergency_id": int(report["id"]),
        "status": report.get("emergency_status"),
        "client_id": int(report["client_id"]) if report.get("client_id") is not None else None,
        "assigned_technician_id": (
            int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None
        ),
        "nearest_workshop_id": (
            int(report["nearest_workshop_id"]) if report.get("nearest_workshop_id") is not None else None
        ),
        "sucursal_id": int(report["sucursal_id"]) if report.get("sucursal_id") is not None else None,
    }
    if extra_payload:
        payload.update(extra_payload)
    return payload


def _build_emergency_realtime_events(
    event_type: str,
    report: Mapping[str, object],
    *,
    include_client: bool = True,
    include_technician: bool = True,
    payload: Mapping[str, object] | None = None,
) -> list[RealtimeEmitEvent]:
    tenant_id, tenant_slug = _emergency_realtime_scope(report)
    if tenant_id is None or not tenant_slug:
        logger.warning(
            "WS emergency event skipped event_type=%s emergency_id=%s tenant scope missing",
            event_type,
            report.get("id"),
        )
        return []

    entity_id = int(report["id"])
    sucursal_id = int(report["sucursal_id"]) if report.get("sucursal_id") is not None else None
    client_id = int(report["client_id"]) if include_client and report.get("client_id") is not None else None
    technician_id = (
        int(report["assigned_technician_id"])
        if include_technician and report.get("assigned_technician_id") is not None
        else None
    )
    event_payload = _build_emergency_event_payload(report, extra_payload=payload)

    events = [
        RealtimeEmitEvent(
            type=event_type,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            entity_type="emergency",
            entity_id=entity_id,
            payload=event_payload,
        )
    ]

    if sucursal_id is not None:
        events.append(
            RealtimeEmitEvent(
                type=event_type,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                sucursal_id=sucursal_id,
                role_target=ROLE_ADMIN_SUCURSAL,
                entity_type="emergency",
                entity_id=entity_id,
                payload=event_payload,
            )
        )
    else:
        logger.warning("WS emergency event event_type=%s emergency_id=%s without sucursal_id", event_type, entity_id)

    if client_id is not None:
        events.append(
            RealtimeEmitEvent(
                type=event_type,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                user_id=client_id,
                role_target=ROLE_CLIENTE,
                entity_type="emergency",
                entity_id=entity_id,
                payload=event_payload,
            )
        )

    if technician_id is not None:
        events.append(
            RealtimeEmitEvent(
                type=event_type,
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                user_id=technician_id,
                role_target=ROLE_TECNICO,
                entity_type="emergency",
                entity_id=entity_id,
                payload=event_payload,
            )
        )

    return events


def _emit_emergency_realtime_events(
    event_type: str,
    report: Mapping[str, object],
    *,
    include_client: bool = True,
    include_technician: bool = True,
    payload: Mapping[str, object] | None = None,
) -> None:
    events = _build_emergency_realtime_events(
        event_type,
        report,
        include_client=include_client,
        include_technician=include_technician,
        payload=payload,
    )
    if not events:
        return
    try:
        asyncio.run(emit_realtime_events(events))
    except Exception:
        logger.exception(
            "WS emergency emit failed event_type=%s emergency_id=%s",
            event_type,
            report.get("id"),
        )


def _emit_emergency_status_realtime_events(report: Mapping[str, object]) -> None:
    _emit_emergency_realtime_events("emergency_status_updated", report)
    normalized_status = validate_supported_emergency_status(
        str(report.get("emergency_status")) if report.get("emergency_status") is not None else "pendiente"
    )
    specific_event_type = EMERGENCY_STATUS_REALTIME_EVENT_TYPES.get(normalized_status)
    if specific_event_type:
        _emit_emergency_realtime_events(specific_event_type, report)


def validate_supported_emergency_status(status_value: str) -> str:
    normalized_status = normalize_optional_text(status_value)
    if normalized_status is None or normalized_status not in SUPPORTED_EMERGENCY_STATUSES:
        allowed_values = ", ".join(sorted(SUPPORTED_EMERGENCY_STATUSES))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Estado invalido. Valores permitidos: {allowed_values}",
        )
    return normalized_status


def changed_by_context(*, workshop_id: int | None, fallback_role: str | None = None) -> tuple[str | None, int | None]:
    if workshop_id is not None:
        return "workshop", workshop_id
    return fallback_role, None


def _infer_actor_from_current_user(current_user: TokenPayload) -> tuple[str | None, int | None]:
    role = normalize_role(current_user.role)
    if role == ROLE_CLIENTE:
        return ROLE_CLIENTE, current_user.user_id
    if role == ROLE_TECNICO:
        return ROLE_TECNICO, current_user.user_id
    if role in {ROLE_ADMIN_SUCURSAL, ROLE_SUPERADMIN_TENANT, ROLE_SUPERADMIN_GLOBAL}:
        return role, current_user.user_id
    return None, None


def build_emergency_timeline_response(
    report: dict[str, object],
    timeline_rows: list[dict[str, object]],
) -> EmergencyTimelineResponse:
    return EmergencyTimelineResponse(
        emergency_id=int(report["id"]),
        current_status=str(report.get("emergency_status")) if report.get("emergency_status") is not None else None,
        timeline=[
            EmergencyTimelineItemResponse(
                status=str(item["new_status"]),
                observation=str(item["observation"]) if item.get("observation") is not None else None,
                changed_by_role=str(item["changed_by_role"]) if item.get("changed_by_role") is not None else None,
                changed_by_user_id=int(item["changed_by_user_id"]) if item.get("changed_by_user_id") is not None else None,
                created_at=item["created_at"],
            )
            for item in timeline_rows
        ],
    )


def workshop_matches_emergency_specialty(workshop_specialty: object, target_specialty: str | None) -> bool:
    normalized_workshop_specialty = normalize_optional_text(str(workshop_specialty)) if workshop_specialty is not None else None
    if target_specialty is None or normalized_workshop_specialty is None:
        return False
    return normalized_workshop_specialty.casefold() == target_specialty.casefold()


def workshop_matches_any_emergency_specialty(
    workshop: dict[str, object],
    target_specialty: str | None,
) -> bool:
    if target_specialty is None:
        return False

    specialties = [
        normalize_optional_text(str(value))
        for value in (workshop.get("specialties") or [])
        if normalize_optional_text(str(value)) is not None
    ]
    primary_specialty = normalize_optional_text(str(workshop.get("specialty"))) if workshop.get("specialty") is not None else None
    if primary_specialty and primary_specialty not in specialties:
        specialties.insert(0, primary_specialty)

    return any(specialty.casefold() == target_specialty.casefold() for specialty in specialties)


def format_distance_text(distance_meters: float) -> str:
    if distance_meters >= 1000:
        return f"{distance_meters / 1000:.1f} km"
    return f"{int(round(distance_meters))} m"


def format_duration_text(duration_seconds: int) -> str:
    if duration_seconds < 60:
        return "1 min"
    duration_minutes = max(1, round(duration_seconds / 60))
    if duration_minutes < 60:
        return f"{duration_minutes} min"
    hours = duration_minutes // 60
    minutes = duration_minutes % 60
    if minutes == 0:
        return f"{hours} h"
    return f"{hours} h {minutes} min"


def build_emergency_tracking_response(report: dict[str, object]) -> EmergencyTrackingResponse:
    client_latitude = report.get("latitude")
    client_longitude = report.get("longitude")
    if client_latitude is None or client_longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La emergencia no tiene coordenadas del cliente disponibles",
        )

    workshop_id = int(report["nearest_workshop_id"]) if report.get("nearest_workshop_id") is not None else None
    workshop = get_workshop_by_id(workshop_id) if workshop_id is not None else None
    if not workshop or workshop.get("latitude") is None or workshop.get("longitude") is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La emergencia no tiene coordenadas del taller asignado disponibles",
        )

    latest_tracking_point = get_latest_emergency_tracking_point(int(report["id"]))
    technician_latitude = float(latest_tracking_point["latitude"]) if latest_tracking_point and latest_tracking_point.get("latitude") is not None else float(workshop["latitude"])
    technician_longitude = float(latest_tracking_point["longitude"]) if latest_tracking_point and latest_tracking_point.get("longitude") is not None else float(workshop["longitude"])
    last_location_at = latest_tracking_point.get("created_at") if latest_tracking_point else None

    distance_meters = calculate_distance_meters(
        technician_latitude,
        technician_longitude,
        float(client_latitude),
        float(client_longitude),
    )
    average_speed_meters_per_second = 25_000 / 3_600
    duration_seconds = max(60, round(distance_meters / average_speed_meters_per_second))
    return EmergencyTrackingResponse(
        emergency_id=int(report["id"]),
        client=EmergencyTrackingActorResponse(
            latitude=float(client_latitude),
            longitude=float(client_longitude),
            address=normalize_optional_text(str(report.get("address"))) if report.get("address") is not None else None,
        ),
        workshop=EmergencyTrackingActorResponse(
            id=workshop_id,
            name=str(workshop["workshop_name"]),
            latitude=float(workshop["latitude"]),
            longitude=float(workshop["longitude"]),
        ),
        technician=EmergencyTrackingActorResponse(
            id=int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None,
            name=str(report["assigned_technician_name"]) if report.get("assigned_technician_name") is not None else None,
            latitude=technician_latitude,
            longitude=technician_longitude,
            last_location_at=last_location_at,
        ),
        route=EmergencyTrackingRouteResponse(
            distance_meters=distance_meters,
            distance_text=format_distance_text(distance_meters),
            duration_seconds=duration_seconds,
            duration_text=format_duration_text(duration_seconds),
            polyline=[
                [technician_latitude, technician_longitude],
                [float(client_latitude), float(client_longitude)],
            ],
            provider="haversine_fallback",
        ),
        status=str(report.get("emergency_status") or "pendiente"),
    )


BRANCH_SCOPED_ROLES = {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO}


def _scoped_sucursal_id(current_user: TokenPayload | None) -> int | None:
    if current_user is not None and current_user.role in BRANCH_SCOPED_ROLES:
        return current_user.sucursal_id
    return None


def _ensure_workshop_scope(workshop_id: int | None, current_user: TokenPayload | None) -> None:
    scoped_sucursal_id = _scoped_sucursal_id(current_user)
    if workshop_id is None or scoped_sucursal_id is None:
        return
    workshop = get_workshop_by_id(workshop_id)
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if workshop.get("sucursal_id") != scoped_sucursal_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")


def _ensure_report_scope(report: Mapping[str, object], current_user: TokenPayload | None) -> None:
    if current_user is None:
        return
    role = normalize_role(current_user.role)
    if role == ROLE_SUPERADMIN_GLOBAL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    if role == ROLE_CLIENTE:
        if report.get("client_id") != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
        return
    if role == ROLE_TECNICO:
        if report.get("assigned_technician_id") != get_effective_technician_id(current_user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
    scoped_sucursal_id = _scoped_sucursal_id(current_user)
    if scoped_sucursal_id is not None and report.get("sucursal_id") != scoped_sucursal_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")


def _resolve_emergency_list_scope(
    current_user: TokenPayload,
    requested_client_id: int | None,
) -> tuple[int | None, int | None]:
    role = normalize_role(current_user.role)
    if role == ROLE_SUPERADMIN_GLOBAL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    if role == ROLE_CLIENTE:
        if requested_client_id is not None and requested_client_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENT_ID_AJENO_NO_PERMITIDO")
        return current_user.user_id, None
    if role == ROLE_TECNICO:
        return requested_client_id, get_effective_technician_id(current_user)
    if role in {ROLE_ADMIN_SUCURSAL, ROLE_SUPERADMIN_TENANT}:
        return requested_client_id, None
    return requested_client_id, None


def find_alternative_workshop_for_emergency(
    report: dict[str, object],
    rejected_workshop_id: int | None,
) -> AlternativeWorkshopCandidate | None:
    if rejected_workshop_id is None:
        return None
    latitude = report.get("latitude")
    longitude = report.get("longitude")
    if latitude is None or longitude is None:
        return None

    target_specialty = normalize_optional_text(
        str(report.get("problem_type_standardized") or report.get("problem_type") or "")
    )
    candidates: list[AlternativeWorkshopCandidate] = []
    for workshop in list_workshop_registrations():
        if int(workshop["id"]) == rejected_workshop_id:
            continue
        if str(workshop.get("approval_status")) != "activo":
            continue
        workshop_latitude = workshop.get("latitude")
        workshop_longitude = workshop.get("longitude")
        if workshop_latitude is None or workshop_longitude is None:
            continue
        distance_meters = calculate_distance_meters(
            float(latitude),
            float(longitude),
            float(workshop_latitude),
            float(workshop_longitude),
        )
        candidates.append(
            AlternativeWorkshopCandidate(
                id=int(workshop["id"]),
                workshop_name=str(workshop["workshop_name"]),
                specialty=normalize_optional_text(str(workshop.get("specialty"))) if workshop.get("specialty") is not None else None,
                zone=normalize_optional_text(str(workshop.get("zone"))) if workshop.get("zone") is not None else None,
                latitude=float(workshop_latitude),
                longitude=float(workshop_longitude),
                distance_meters=distance_meters,
                specialty_match=workshop_matches_any_emergency_specialty(workshop, target_specialty),
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda item: (not item.specialty_match, item.distance_meters, item.id))
    return candidates[0]


def reassign_emergency_to_workshop(
    report_id: int,
    alternative_workshop: AlternativeWorkshopCandidate,
    *,
    changed_by_role: str | None,
    changed_by_user_id: int | None,
) -> EmergencyReportResponse:
    clear_emergency_assignment(report_id)
    observation = f"Solicitud reasignada automaticamente al taller {alternative_workshop.workshop_name}"
    alternative_workshop_record = get_workshop_by_id(alternative_workshop.id)
    alternative_sucursal_id = (
        int(alternative_workshop_record["sucursal_id"])
        if alternative_workshop_record and alternative_workshop_record.get("sucursal_id") is not None
        else None
    )
    updated = reassign_emergency_report_to_workshop(
        report_id,
        nearest_workshop_id=alternative_workshop.id,
        nearest_workshop_name=alternative_workshop.workshop_name,
        nearest_workshop_specialty=alternative_workshop.specialty,
        nearest_workshop_zone=alternative_workshop.zone,
        nearest_workshop_distance_meters=alternative_workshop.distance_meters,
        sucursal_id=alternative_sucursal_id,
        emergency_status="en_revision",
        previous_status="solicitud_cancelada",
        changed_by_role=changed_by_role,
        changed_by_user_id=changed_by_user_id,
        observation=observation,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada al intentar reasignar",
        )
    normalize_emergency_media_fields(updated)
    return EmergencyReportResponse.model_validate(updated)


"""
Aqui esta la logica de registro de emergencia que procesa
datos, fotos y audio para crear un nuevo reporte.
"""
def register_emergency_service(
    *,
    local_id: str | None,
    client_id: int | None,
    vehicle_name: str,
    vehicle_plate: str,
    problem_type: str,
    price: int | None,
    description: str | None,
    latitude: float | None,
    longitude: float | None,
    address: str | None,
    zone: str | None,
    nearest_workshop_id: int | None,
    nearest_workshop_name: str | None,
    nearest_workshop_specialty: str | None,
    nearest_workshop_zone: str | None,
    nearest_workshop_distance_meters: float | None,
    audio_duration_seconds: float | None,
    photos: list[UploadFile],
    audio: UploadFile | None,
) -> tuple[EmergencyReportResponse, bool]:
    # Deduplication: if local_id already exists return the existing report (is_duplicate=True)
    if local_id is not None:
        try:
            existing = get_emergency_report_by_local_id(local_id)
        except OperationalError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
        if existing is not None:
            normalize_emergency_media_fields(existing)
            return EmergencyReportResponse.model_validate(existing), True
    if client_id is not None:
        ensure_client_exists(client_id)
    valid_photos = [photo for photo in photos if photo.filename]
    if len(valid_photos) > MAX_EMERGENCY_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se permiten como maximo {MAX_EMERGENCY_PHOTOS} fotos por emergencia",
        )

    photo_paths: list[str] = []
    photo_urls: list[str] = []
    audio_path: str | None = None
    workshop = get_workshop_by_id(nearest_workshop_id) if nearest_workshop_id is not None else None
    sucursal_id = int(workshop["sucursal_id"]) if workshop and workshop.get("sucursal_id") is not None else None
    try:
        for photo in valid_photos:
            relative_path, public_url = save_emergency_photo(photo)
            photo_paths.append(relative_path)
            photo_urls.append(public_url)
        audio_path, audio_url = save_emergency_audio(audio)
        audio_transcript, audio_transcript_status, audio_transcript_error = transcribe_emergency_audio(audio_path)
        photo_problem_type_standardized, photo_classification_confidence, photo_classification_error = classify_emergency_photos(photo_paths)
        normalized_problem_type = normalize_problem_type(problem_type)
        standardized_problem_type = determine_standardized_problem_type(
            normalized_problem_type,
            description,
            audio_transcript,
            photo_problem_type_standardized,
        )
        created = create_emergency_report(
            {
                "local_id": local_id,
                "client_id": client_id,
                "vehicle_name": vehicle_name.strip(),
                "vehicle_plate": normalize_plate(vehicle_plate),
                "problem_type": normalized_problem_type,
                "price": resolve_emergency_price(price, standardized_problem_type),
                "emergency_status": "pendiente",
                "problem_type_standardized": standardized_problem_type,
                "photo_problem_type_standardized": photo_problem_type_standardized,
                "photo_classification_confidence": photo_classification_confidence,
                "photo_classification_error": normalize_optional_text(photo_classification_error),
                "description": normalize_optional_text(description),
                "latitude": latitude,
                "longitude": longitude,
                "address": normalize_optional_text(address),
                "zone": normalize_optional_text(zone),
                "nearest_workshop_id": nearest_workshop_id,
                "nearest_workshop_name": normalize_optional_text(nearest_workshop_name),
                "nearest_workshop_specialty": normalize_optional_text(nearest_workshop_specialty),
                "nearest_workshop_zone": normalize_optional_text(nearest_workshop_zone),
                "nearest_workshop_distance_meters": nearest_workshop_distance_meters,
                "sucursal_id": sucursal_id,
                "audio_duration_seconds": audio_duration_seconds,
                "audio_transcript": audio_transcript,
                "audio_transcript_status": audio_transcript_status,
                "audio_transcript_error": normalize_optional_text(audio_transcript_error),
                "photo_paths": json.dumps(photo_paths),
                "photo_urls": json.dumps(photo_urls),
                "audio_path": audio_path,
                "audio_url": audio_url,
                "rejection_reason": None,
                "rejected_at": None,
            },
            initial_history_status="solicitud_recibida",
            changed_by_role="client" if client_id is not None else None,
            changed_by_user_id=client_id,
        )
    except HTTPException:
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise
    except OperationalError as exc:
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    normalize_emergency_media_fields(created)
    _emit_emergency_realtime_events(
        "emergency_registered",
        created,
        include_technician=False,
    )
    return EmergencyReportResponse.model_validate(created), False


"""
Aqui esta la logica de listado de emergencias que consulta
los reportes registrados con filtros opcionales por taller, estado y tenant.
"""
def get_emergency_reports_service(
    nearest_workshop_id: int | None,
    emergency_status: str | None,
    client_id: int | None,
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
    technician_id: int | None = None,
) -> list[EmergencyReportListResponse]:
    validated_status = (
        validate_supported_emergency_status(emergency_status)
        if emergency_status is not None
        else None
    )
    try:
        if tenant_id is not None:
            rows = list_emergency_reports_by_tenant(
                nearest_workshop_id=nearest_workshop_id,
                tenant_id=tenant_id,
                emergency_status=validated_status,
                sucursal_id=sucursal_id,
                client_id=client_id,
                technician_id=technician_id,
            )
        else:
            rows = list_emergency_reports(
                nearest_workshop_id=nearest_workshop_id,
                emergency_status=validated_status,
                client_id=client_id,
                technician_id=technician_id,
            )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    for row in rows:
        normalize_emergency_media_fields(row)
    return [EmergencyReportListResponse.model_validate(row) for row in rows]


def get_emergency_report_detail_service(
    report_id: int,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> EmergencyReportResponse:
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
    _ensure_report_scope(report, current_user)
    normalize_emergency_media_fields(report)
    return EmergencyReportResponse.model_validate(report)


def get_emergency_timeline_service(
    report_id: int,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> EmergencyTimelineResponse:
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
        timeline_rows = list_emergency_status_history(report_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )
    _ensure_report_scope(report, current_user)
    return build_emergency_timeline_response(report, timeline_rows)


def change_emergency_status_service(
    report_id: int,
    next_status: str,
    workshop_id: int | None,
    current_user: TokenPayload,
    *,
    observation: str | None = None,
    require_workshop_for_active: bool = False,
    changed_by_role: str | None = None,
    changed_by_user_id: int | None = None,
    rejection_reason: str | None = None,
    rejected_at: datetime | None = None,
    clear_rejection_metadata: bool = False,
    latitud_llegada: float | None = None,
    longitud_llegada: float | None = None,
) -> EmergencyReportResponse:
    validated_status = validate_supported_emergency_status(next_status)
    if require_workshop_for_active and validated_status == "activo" and workshop_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo un taller puede cambiar una emergencia a activo",
        )
    try:
        current_report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not current_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )
    _ensure_report_scope(current_report, current_user)
    if normalize_role(current_user.role) == ROLE_CLIENTE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENTE_NO_PUEDE_ACTUALIZAR_ESTADO")
    inferred_role, inferred_user_id = changed_by_context(
        workshop_id=workshop_id,
        fallback_role="admin",
    )
    if workshop_id is None:
        user_role, user_id = _infer_actor_from_current_user(current_user)
        inferred_role = user_role or inferred_role
        inferred_user_id = user_id if user_id is not None else inferred_user_id
    changed_by_role = normalize_optional_text(changed_by_role) or inferred_role
    changed_by_user_id = changed_by_user_id if changed_by_user_id is not None else inferred_user_id
    try:
        updated = update_emergency_status(
            report_id,
            validated_status,
            nearest_workshop_id=workshop_id,
            changed_by_role=changed_by_role,
            changed_by_user_id=changed_by_user_id,
            observation=normalize_optional_text(observation),
            rejection_reason=normalize_optional_text(rejection_reason),
            rejected_at=rejected_at,
            clear_rejection_metadata=clear_rejection_metadata,
            latitud_llegada=latitud_llegada,
            longitud_llegada=longitud_llegada,
        )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )
    normalize_emergency_media_fields(updated)
    return EmergencyReportResponse.model_validate(updated)


"""
Aqui esta la logica de estado de emergencia que actualiza
si una emergencia pasa a activa o rechazada y notifica al cliente.
"""
def edit_emergency_status_service(
    report_id: int,
    payload: EmergencyStatusUpdate,
    workshop_id: int | None,
    current_user: TokenPayload,
) -> EmergencyReportResponse:
    if normalize_role(current_user.role) == ROLE_TECNICO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TECNICO_NO_PUEDE_ACEPTAR_O_RECHAZAR")
    updated = change_emergency_status_service(
        report_id,
        payload.emergency_status,
        workshop_id,
        current_user,
        require_workshop_for_active=True,
    )
    if payload.emergency_status == "activo":
        updated_payload = updated.model_dump()
        workshop_name = compact_push_text(updated_payload.get("nearest_workshop_name"), fallback="El taller", max_length=80)
        incident_label = emergency_incident_label(updated_payload)
        send_push_to_client(
            int(updated_payload["client_id"]) if updated_payload.get("client_id") is not None else None,
            "Emergencia aceptada",
            f"{workshop_name} acepto tu emergencia: {incident_label}",
            {
                "type": "emergency_accepted",
                "emergency_id": str(report_id),
                "workshop_id": str(workshop_id or updated_payload.get("nearest_workshop_id") or ""),
                "workshop_name": workshop_name,
                "incident_description": incident_label,
            },
        )
    _emit_emergency_status_realtime_events(updated.model_dump())
    return updated


def update_emergency_timeline_status_service(
    report_id: int,
    payload: EmergencyTimelineStatusUpdate,
    workshop_id: int | None,
    current_user: TokenPayload,
) -> EmergencyTimelineResponse:
    if normalize_role(current_user.role) == ROLE_TECNICO and payload.estado not in {
        "auxilio_en_camino",
        "tecnico_en_sitio",
        "servicio_en_proceso",
        "servicio_finalizado",
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ESTADO_NO_PERMITIDO_PARA_TECNICO")
    updated = change_emergency_status_service(
        report_id,
        payload.estado,
        workshop_id,
        current_user,
        observation=payload.observacion,
        latitud_llegada=payload.latitud_llegada,
        longitud_llegada=payload.longitud_llegada,
    )
    normalized_status = validate_supported_emergency_status(payload.estado)
    if normalized_status in EMERGENCY_TIMELINE_NOTIFICATION_STATUSES:
        updated_payload = updated.model_dump()
        send_emergency_status_update_notification(
            int(updated_payload["client_id"]) if updated_payload.get("client_id") is not None else None,
            report_id,
            normalized_status,
            EMERGENCY_STATUS_NOTIFICATION_LABELS[normalized_status],
        )
    _emit_emergency_status_realtime_events(updated.model_dump())
    return get_emergency_timeline_service(report_id, workshop_id)


def reject_emergency_service(
    report_id: int,
    payload: EmergencyRejectRequest,
    workshop_id: int | None,
    current_user: TokenPayload,
) -> EmergencyRejectionResponse:
    if normalize_role(current_user.role) in {ROLE_CLIENTE, ROLE_TECNICO}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_RECHAZAR")
    rejection_reason = normalize_optional_text(payload.motivo)
    if rejection_reason is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo del rechazo es obligatorio",
        )

    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )

    current_status = validate_supported_emergency_status(
        str(report.get("emergency_status")) if report.get("emergency_status") is not None else "pendiente"
    )
    effective_workshop_id = workshop_id
    if effective_workshop_id is None and report.get("nearest_workshop_id") is not None:
        effective_workshop_id = int(report["nearest_workshop_id"])
    if current_status in {"solicitud_cancelada", "rechazado"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud ya fue rechazada anteriormente",
        )
    if current_status == "servicio_finalizado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede rechazar una solicitud ya finalizada",
        )

    available_technicians = 0
    if effective_workshop_id is not None:
        try:
            available_technicians = sum(
                1
                for technician in list_technicians_by_workshop(effective_workshop_id)
                if str(technician.get("status")) == "disponible"
            )
        except OperationalError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
        logger.info(
            "Rechazo de emergencia %s en taller %s con %s tecnicos disponibles",
            report_id,
            effective_workshop_id,
            available_technicians,
        )

    updated = change_emergency_status_service(
        report_id,
        "solicitud_cancelada",
        workshop_id,
        current_user,
        observation=rejection_reason,
        changed_by_role=payload.changed_by_role,
        changed_by_user_id=payload.changed_by_user_id,
        rejection_reason=rejection_reason,
        rejected_at=datetime.now(timezone.utc),
    )
    history_actor_role = payload.changed_by_role or ("workshop" if effective_workshop_id is not None else "admin")
    history_actor_user_id = payload.changed_by_user_id if payload.changed_by_user_id is not None else effective_workshop_id
    alternative_workshop = None
    try:
        alternative_workshop = find_alternative_workshop_for_emergency(report, effective_workshop_id)
        if alternative_workshop is not None:
            updated = reassign_emergency_to_workshop(
                report_id,
                alternative_workshop,
                changed_by_role=history_actor_role,
                changed_by_user_id=history_actor_user_id,
            )
            send_emergency_reassigned_notification(
                updated.client_id,
                report_id,
                new_workshop_id=alternative_workshop.id,
                new_workshop_name=alternative_workshop.workshop_name,
            )
        else:
            clear_emergency_assignment(report_id)
            create_emergency_status_history(
                {
                    "emergency_id": report_id,
                    "previous_status": "solicitud_cancelada",
                    "new_status": "solicitud_cancelada",
                    "changed_by_role": history_actor_role,
                    "changed_by_user_id": history_actor_user_id,
                    "observation": "No se encontro taller alternativo disponible",
                }
            )
            refreshed_report = get_emergency_report_by_id(report_id)
            if refreshed_report is not None:
                normalize_emergency_media_fields(refreshed_report)
                updated = EmergencyReportResponse.model_validate(refreshed_report)
            send_emergency_rejected_notification(
                updated.client_id,
                report_id,
                rejection_reason,
            )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    timeline = get_emergency_timeline_service(
        report_id,
        alternative_workshop.id if alternative_workshop is not None else None,
    )
    _emit_emergency_realtime_events(
        "request_rejected",
        updated.model_dump(),
        include_technician=False,
        payload={"rejection_reason": updated.rejection_reason},
    )
    return EmergencyRejectionResponse(
        emergency=updated,
        timeline=timeline,
    )


"""
Aqui esta la logica de asignacion de tecnico que valida
la disponibilidad del tecnico y lo vincula a una emergencia activa.
"""
def assign_technician_to_emergency_service(
    report_id: int,
    payload: EmergencyTechnicianAssignmentRequest,
    workshop_id: int,
    current_user: TokenPayload,
) -> EmergencyReportListResponse:
    if normalize_role(current_user.role) in {ROLE_CLIENTE, ROLE_TECNICO}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_ASIGNAR")
    try:
        technician = get_technician_by_workshop(payload.technician_id, workshop_id)
        workshop_reports = list_emergency_reports(nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not technician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado para este taller")
    report = next((item for item in workshop_reports if int(item["id"]) == report_id), None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece a este taller",
        )
    _ensure_report_scope(report, current_user)
    if report.get("emergency_status") != "activo":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primero debes aceptar la emergencia para asignar un tecnico",
        )
    current_assigned_technician_id = report.get("assigned_technician_id")
    if str(technician.get("status")) != "disponible" and current_assigned_technician_id != payload.technician_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tecnico seleccionado no esta disponible")
    try:
        assign_emergency_technician(report_id, workshop_id, payload.technician_id)
        refreshed_reports = list_emergency_reports(nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    updated_report = next((item for item in refreshed_reports if int(item["id"]) == report_id), None)
    if not updated_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
    normalize_emergency_media_fields(updated_report)
    workshop_name = compact_push_text(updated_report.get("nearest_workshop_name"), fallback="El taller", max_length=80)
    technician_name = compact_push_text(
        updated_report.get("assigned_technician_name") or technician.get("full_name"),
        fallback="Tecnico asignado",
        max_length=80,
    )
    incident_label = emergency_incident_label(updated_report)
    try:
        workshop = get_workshop_by_id(workshop_id)
    except OperationalError:
        logger.exception("No se pudo consultar coordenadas del taller %s para push", workshop_id)
        workshop = None
    push_data = {
        "type": "technician_assigned",
        "emergency_id": str(report_id),
        "workshop_id": str(workshop_id),
        "technician_id": str(payload.technician_id),
        "workshop_name": workshop_name,
        "technician_name": technician_name,
        "incident_description": incident_label,
    }
    add_coordinate_pair(
        push_data,
        latitude_key="technician_latitude",
        longitude_key="technician_longitude",
        latitude=workshop.get("latitude") if workshop else None,
        longitude=workshop.get("longitude") if workshop else None,
    )
    send_push_to_client(
        int(updated_report["client_id"]) if updated_report.get("client_id") is not None else None,
        "Tecnico asignado",
        f"{technician_name} de {workshop_name} atendera: {incident_label}",
        push_data,
    )
    _emit_emergency_realtime_events(
        "technician_assigned",
        updated_report,
        payload={"assigned_technician_id": payload.technician_id},
    )
    return EmergencyReportListResponse.model_validate(updated_report)


def get_emergency_tracking_service(report_id: int, workshop_id: int | None) -> EmergencyTrackingResponse:
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o no pertenece al taller indicado",
            )
        return build_emergency_tracking_response(report)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc


def register_emergency_tracking_location_service(
    report_id: int,
    payload: EmergencyTrackingLocationRequest,
    workshop_id: int | None,
    current_user: TokenPayload,
) -> EmergencyTrackingResponse:
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o no pertenece al taller indicado",
            )
        _ensure_report_scope(report, current_user)
        if normalize_role(current_user.role) == ROLE_TECNICO and payload.technician_id != get_effective_technician_id(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TECNICO_NO_PUEDE_REPORTAR_UBICACION_DE_OTRO_USUARIO",
            )
        assigned_technician_id = int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None
        if assigned_technician_id is not None and assigned_technician_id != payload.technician_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La ubicacion no corresponde al tecnico asignado a esta emergencia",
            )
        create_emergency_tracking_point(
            {
                "emergency_id": report_id,
                "technician_id": payload.technician_id,
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "source": normalize_optional_text(payload.source) or "system",
            }
        )
        refreshed_report = get_emergency_report_by_id(report_id, nearest_workshop_id=workshop_id)
        if not refreshed_report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
        tracking_response = build_emergency_tracking_response(refreshed_report)
        _emit_emergency_realtime_events(
            "tracking_location_updated",
            refreshed_report,
            include_technician=False,
            payload={
                "technician_id": payload.technician_id,
                "tracking_latitude": payload.latitude,
                "tracking_longitude": payload.longitude,
                "tracking_source": normalize_optional_text(payload.source) or "system",
            },
        )
        return tracking_response
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc


"""
Aqui esta la logica de eliminacion de emergencia que verifica
el reporte y luego lo borra del sistema.
"""
def remove_emergency_report_service(report_id: int, workshop_id: int | None) -> None:
    try:
        deleted = delete_emergency_report(report_id, nearest_workshop_id=workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergencia no encontrada o no pertenece al taller indicado",
        )


# =========================================================
# CONTROLADORES HTTP DE EMERGENCIAS
# En esta seccion estan los endpoints principales del modulo emergencias.
# Aqui puedes encontrar:
# - POST para registrar una emergencia
# - GET para listar emergencias
# - PUT para cambiar el estado de una emergencia
# - PUT para asignar un tecnico a una emergencia
# - DELETE para eliminar una emergencia
# =========================================================
@router.post(
    f"{settings.api_prefix}/emergencias",
    response_model=EmergencyReportResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de registro de emergencia que guarda el reporte con fotos y audio.
def register_emergency(
    http_response: Response,
    local_id: str | None = Form(default=None, max_length=64),
    client_id: int | None = Form(default=None, ge=1),
    vehicle_name: str = Form(min_length=1, max_length=160),
    vehicle_plate: str = Form(min_length=3, max_length=40),
    problem_type: str = Form(min_length=2, max_length=120),
    price: int | None = Form(default=None, ge=0),
    description: str | None = Form(default=None, min_length=3, max_length=4000),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    address: str | None = Form(default=None, max_length=255),
    zone: str | None = Form(default=None, max_length=120),
    nearest_workshop_id: int | None = Form(default=None, ge=1),
    nearest_workshop_name: str | None = Form(default=None, max_length=160),
    nearest_workshop_specialty: str | None = Form(default=None, max_length=120),
    nearest_workshop_zone: str | None = Form(default=None, max_length=120),
    nearest_workshop_distance_meters: float | None = Form(default=None, ge=0),
    audio_duration_seconds: float | None = Form(default=None, ge=0),
    photos: list[UploadFile] = File(default=[]),
    audio: UploadFile | None = File(default=None),
) -> EmergencyReportResponse:
    report, is_duplicate = register_emergency_service(
        local_id=local_id,
        client_id=client_id,
        vehicle_name=vehicle_name,
        vehicle_plate=vehicle_plate,
        problem_type=problem_type,
        price=price,
        description=description,
        latitude=latitude,
        longitude=longitude,
        address=address,
        zone=zone,
        nearest_workshop_id=nearest_workshop_id,
        nearest_workshop_name=nearest_workshop_name,
        nearest_workshop_specialty=nearest_workshop_specialty,
        nearest_workshop_zone=nearest_workshop_zone,
        nearest_workshop_distance_meters=nearest_workshop_distance_meters,
        audio_duration_seconds=audio_duration_seconds,
        photos=photos,
        audio=audio,
    )
    if is_duplicate:
        http_response.status_code = status.HTTP_200_OK
    return report


@router.get(
    f"{settings.api_prefix}/emergencias",
    response_model=list[EmergencyReportListResponse],
)
# Aqui esta el controlador GET de listado de emergencias que obtiene los reportes registrados.
def get_emergency_reports(
    nearest_workshop_id: int | None = Query(default=None, ge=1),
    client_id: int | None = Query(default=None, ge=1),
    emergency_status: str | None = Query(default=None),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[EmergencyReportListResponse]:
    _ensure_workshop_scope(nearest_workshop_id, current_user)
    tenant_id = get_tenant_id_for_query(current_user)
    sucursal_id = _scoped_sucursal_id(current_user)
    effective_client_id, effective_technician_id = _resolve_emergency_list_scope(current_user, client_id)
    return get_emergency_reports_service(
        nearest_workshop_id,
        emergency_status,
        effective_client_id,
        tenant_id,
        sucursal_id,
        effective_technician_id,
    )


@router.get(
    f"{settings.api_prefix}/emergencias/{{report_id}}",
    response_model=EmergencyReportResponse,
)
def get_emergency_report_detail(
    report_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyReportResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return get_emergency_report_detail_service(report_id, workshop_id, current_user)


@router.get(
    f"{settings.api_prefix}/emergencias/{{report_id}}/timeline",
    response_model=EmergencyTimelineResponse,
)
def get_emergency_timeline(
    report_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyTimelineResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return get_emergency_timeline_service(report_id, workshop_id, current_user)


@router.get(
    f"{settings.api_prefix}/emergencias/{{report_id}}/tracking",
    response_model=EmergencyTrackingResponse,
)
def get_emergency_tracking(
    report_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyTrackingResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    report = get_emergency_report_detail_service(report_id, workshop_id, current_user)
    return build_emergency_tracking_response(report.model_dump())


@router.post(
    f"{settings.api_prefix}/emergencias/{{report_id}}/tracking/location",
    response_model=EmergencyTrackingResponse,
)
def register_emergency_tracking_location(
    report_id: int,
    payload: EmergencyTrackingLocationRequest,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyTrackingResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return register_emergency_tracking_location_service(report_id, payload, workshop_id, current_user)


@router.put(
    f"{settings.api_prefix}/emergencias/{{report_id}}/status",
    response_model=EmergencyReportResponse,
)
# Aqui esta el controlador PUT de estado de emergencia que cambia una emergencia a activa o rechazada.
def edit_emergency_status(
    report_id: int,
    payload: EmergencyStatusUpdate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyReportResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return edit_emergency_status_service(report_id, payload, workshop_id, current_user)


@router.patch(
    f"{settings.api_prefix}/emergencias/{{report_id}}/estado",
    response_model=EmergencyTimelineResponse,
)
def update_emergency_timeline_status(
    report_id: int,
    payload: EmergencyTimelineStatusUpdate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyTimelineResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return update_emergency_timeline_status_service(report_id, payload, workshop_id, current_user)


@router.patch(
    f"{settings.api_prefix}/emergencias/{{report_id}}/rechazar",
    response_model=EmergencyRejectionResponse,
)
def reject_emergency(
    report_id: int,
    payload: EmergencyRejectRequest,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyRejectionResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return reject_emergency_service(report_id, payload, workshop_id, current_user)


@router.put(
    f"{settings.api_prefix}/emergencias/{{report_id}}/technician-assignment",
    response_model=EmergencyReportListResponse,
)
# Aqui esta el controlador PUT de asignacion de tecnico que vincula un tecnico a una emergencia activa.
def assign_technician_to_emergency(
    report_id: int,
    payload: EmergencyTechnicianAssignmentRequest,
    workshop_id: int = Query(ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyReportListResponse:
    _ensure_workshop_scope(workshop_id, current_user)
    return assign_technician_to_emergency_service(report_id, payload, workshop_id, current_user)


@router.delete(
    f"{settings.api_prefix}/emergencias/{{report_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
# Aqui esta el controlador DELETE de eliminacion de emergencia que borra un reporte de emergencia.
def remove_emergency_report(
    report_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    _ensure_workshop_scope(workshop_id, current_user)
    remove_emergency_report_service(report_id, workshop_id)
