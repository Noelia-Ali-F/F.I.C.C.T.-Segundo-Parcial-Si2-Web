import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError, OperationalError

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
    emergency_has_candidate_for_sucursal,
    get_client_by_id,
    get_emergency_workshop_candidate,
    get_emergency_report_by_id,
    get_emergency_report_by_local_id,
    get_latest_emergency_tracking_point,
    get_sucursal_by_id,
    get_technician_by_workshop,
    get_workshop_by_id,
    get_workshop_by_sucursal,
    list_emergency_reports,
    list_emergency_reports_by_tenant,
    list_emergency_status_history,
    list_technicians_by_workshop,
    list_workshop_registrations,
    mark_emergency_candidate_winner,
    reassign_emergency_report_to_workshop,
    upsert_emergency_workshop_candidates,
    update_emergency_status,
)
from app.realtime import emit_realtime_events
from app.realtime_types import RealtimeEmitEvent
from app.services.notification_service import notify_emergency_event
from app.tenant_context import clear_engine, get_engine, get_tenant, set_context

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
EMERGENCY_STATUS_ALIASES = {
    "solicitud_aceptada": "activo",
    "solicitud_rechazada": "solicitud_cancelada",
    "taller_asignado": "auxilio_asignado",
    "buscando_taller": "en_revision",
    "tecnico_llego": "tecnico_en_sitio",
    "finalizado": "servicio_finalizado",
    "cancelado": "solicitud_cancelada",
}
EMERGENCY_TIMELINE_NOTIFICATION_STATUSES = set(EMERGENCY_STATUS_NOTIFICATION_LABELS)
EMERGENCY_STATUS_REALTIME_EVENT_TYPES = {
    "auxilio_en_camino": "technician_on_the_way",
    "tecnico_en_sitio": "technician_on_site",
    "servicio_en_proceso": "service_started",
    "servicio_finalizado": "service_finished",
}
EMERGENCY_CANDIDATE_STATUS_PENDING = "PENDIENTE"
EMERGENCY_CANDIDATE_STATUS_WINNER = "GANADORA"
EMERGENCY_CANDIDATE_STATUS_ACCEPTED_BY_OTHER = "ACEPTADA_POR_OTRA_SUCURSAL"
EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE = "Esta solicitud ya fue aceptada por otra sucursal"

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


class OfflineSyncContractError(Exception):
    def __init__(self, *, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self.payload = payload
        super().__init__(str(payload.get("message") or payload.get("error_code") or "offline_sync_error"))


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
    workshop_candidate_status: str | None = None
    workshop_candidate_message: str | None = None
    can_accept: bool = False


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
    source: str | None = None
    heading: float | None = None
    speed: float | None = None
    accuracy: float | None = None
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
    tenant_id: int | None = None
    tenant_slug: str | None = None
    sucursal_id: int | None = None
    nearest_workshop_id: int | None = None
    nearest_workshop_distance_meters: float | None = None
    client: EmergencyTrackingActorResponse
    workshop: EmergencyTrackingActorResponse
    technician: EmergencyTrackingActorResponse
    route: EmergencyTrackingRouteResponse
    status: str


class EmergencyRoutingCandidateResponse(BaseModel):
    workshop_id: int
    workshop_name: str
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    specialty: str | None = None
    specialties: list[str] = Field(default_factory=list)
    zone: str | None = None
    latitude: float
    longitude: float
    distance_meters: float
    specialty_match: bool = True


class EmergencyRoutingPreviewResponse(BaseModel):
    problem_type: str
    problem_type_standardized: str | None = None
    total_matching_sucursales: int
    nearest_workshop_id: int | None = None
    nearest_workshop_name: str | None = None
    nearest_sucursal_id: int | None = None
    nearest_sucursal_nombre: str | None = None
    nearest_workshop_distance_meters: float | None = None
    candidates: list[EmergencyRoutingCandidateResponse] = Field(default_factory=list)


class EmergencyTrackingLocationRequest(BaseModel):
    technician_id: int | None = Field(default=None, ge=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: str | None = Field(default="system", max_length=50)
    heading: float | None = Field(default=None, ge=0, le=360)
    speed: float | None = Field(default=None, ge=0)
    accuracy: float | None = Field(default=None, ge=0)


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
    tenant_id, tenant_slug = _emergency_realtime_scope(report)
    payload: dict[str, object] = {
        "emergency_id": int(report["id"]),
        "status": report.get("emergency_status"),
        "client_id": int(report["client_id"]) if report.get("client_id") is not None else None,
        "assigned_technician_id": (
            int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None
        ),
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug,
        "nearest_workshop_id": (
            int(report["nearest_workshop_id"]) if report.get("nearest_workshop_id") is not None else None
        ),
        "nearest_workshop_distance_meters": (
            float(report["nearest_workshop_distance_meters"])
            if report.get("nearest_workshop_distance_meters") is not None
            else None
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
    if normalized_status is not None:
        normalized_status = EMERGENCY_STATUS_ALIASES.get(normalized_status, normalized_status)
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


def _resolve_workshop_coordinates(workshop: dict[str, object]) -> tuple[float | None, float | None]:
    workshop_latitude = workshop.get("latitude")
    workshop_longitude = workshop.get("longitude")
    if workshop_latitude is not None and workshop_longitude is not None:
        return float(workshop_latitude), float(workshop_longitude)
    sucursal_id = workshop.get("sucursal_id")
    if sucursal_id is None:
        return None, None
    sucursal = get_sucursal_by_id(int(sucursal_id))
    if not sucursal:
        return None, None
    latitude = sucursal.get("latitud")
    longitude = sucursal.get("longitud")
    if latitude is None or longitude is None:
        return None, None
    return float(latitude), float(longitude)


def find_matching_workshops_for_emergency(
    *,
    problem_type: str,
    problem_type_standardized: str | None,
    latitude: float,
    longitude: float,
    excluded_workshop_id: int | None = None,
) -> list[EmergencyRoutingCandidateResponse]:
    target_specialty = normalize_optional_text(problem_type_standardized or problem_type)
    candidates: list[EmergencyRoutingCandidateResponse] = []
    for workshop in list_workshop_registrations():
        if excluded_workshop_id is not None and int(workshop["id"]) == excluded_workshop_id:
            continue
        if str(workshop.get("approval_status")) != "activo":
            continue
        if str(workshop.get("availability_status") or "disponible") == "fuera_de_servicio":
            continue
        if not workshop_matches_any_emergency_specialty(workshop, target_specialty):
            continue
        workshop_latitude, workshop_longitude = _resolve_workshop_coordinates(workshop)
        if workshop_latitude is None or workshop_longitude is None:
            continue
        distance_meters = calculate_distance_meters(
            float(latitude),
            float(longitude),
            float(workshop_latitude),
            float(workshop_longitude),
        )
        sucursal_id = int(workshop["sucursal_id"]) if workshop.get("sucursal_id") is not None else None
        sucursal = get_sucursal_by_id(sucursal_id) if sucursal_id is not None else None
        specialties = [
            normalize_optional_text(str(value))
            for value in (workshop.get("specialties") or [])
            if normalize_optional_text(str(value)) is not None
        ]
        primary_specialty = normalize_optional_text(str(workshop.get("specialty"))) if workshop.get("specialty") is not None else None
        if primary_specialty and primary_specialty not in specialties:
            specialties.insert(0, primary_specialty)
        candidates.append(
            EmergencyRoutingCandidateResponse(
                workshop_id=int(workshop["id"]),
                workshop_name=str(workshop.get("workshop_name") or "Taller"),
                sucursal_id=sucursal_id,
                sucursal_nombre=normalize_optional_text(str(sucursal.get("nombre"))) if sucursal and sucursal.get("nombre") is not None else None,
                specialty=primary_specialty,
                specialties=[value for value in specialties if value is not None],
                zone=normalize_optional_text(str(workshop.get("zone"))) if workshop.get("zone") is not None else None,
                latitude=workshop_latitude,
                longitude=workshop_longitude,
                distance_meters=distance_meters,
                specialty_match=True,
            )
        )
    candidates.sort(key=lambda item: (item.distance_meters, item.workshop_id))
    return candidates


def build_emergency_routing_preview(
    *,
    problem_type: str,
    description: str | None,
    latitude: float,
    longitude: float,
) -> EmergencyRoutingPreviewResponse:
    normalized_problem_type = normalize_problem_type(problem_type)
    standardized_problem_type = determine_standardized_problem_type(
        normalized_problem_type,
        description,
        None,
        None,
    )
    candidates = find_matching_workshops_for_emergency(
        problem_type=normalized_problem_type,
        problem_type_standardized=standardized_problem_type,
        latitude=latitude,
        longitude=longitude,
    )
    nearest = candidates[0] if candidates else None
    return EmergencyRoutingPreviewResponse(
        problem_type=normalized_problem_type,
        problem_type_standardized=standardized_problem_type,
        total_matching_sucursales=len({item.sucursal_id for item in candidates if item.sucursal_id is not None}),
        nearest_workshop_id=nearest.workshop_id if nearest is not None else None,
        nearest_workshop_name=nearest.workshop_name if nearest is not None else None,
        nearest_sucursal_id=nearest.sucursal_id if nearest is not None else None,
        nearest_sucursal_nombre=nearest.sucursal_nombre if nearest is not None else None,
        nearest_workshop_distance_meters=nearest.distance_meters if nearest is not None else None,
        candidates=candidates,
    )


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
    tracking_source = (
        normalize_optional_text(str(latest_tracking_point.get("source")))
        if latest_tracking_point and latest_tracking_point.get("source") is not None
        else "workshop_base"
    )
    tracking_heading = float(latest_tracking_point["heading"]) if latest_tracking_point and latest_tracking_point.get("heading") is not None else None
    tracking_speed = float(latest_tracking_point["speed"]) if latest_tracking_point and latest_tracking_point.get("speed") is not None else None
    tracking_accuracy = float(latest_tracking_point["accuracy"]) if latest_tracking_point and latest_tracking_point.get("accuracy") is not None else None
    tenant = get_tenant()
    tenant_id = int(tenant["id"]) if tenant and tenant.get("id") is not None else None
    tenant_slug = str(tenant["slug"]) if tenant and tenant.get("slug") else None

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
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        sucursal_id=int(report["sucursal_id"]) if report.get("sucursal_id") is not None else None,
        nearest_workshop_id=workshop_id,
        nearest_workshop_distance_meters=(
            float(report["nearest_workshop_distance_meters"])
            if report.get("nearest_workshop_distance_meters") is not None
            else None
        ),
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
            source=tracking_source,
            heading=tracking_heading,
            speed=tracking_speed,
            accuracy=tracking_accuracy,
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
    report_sucursal_id = report.get("sucursal_id")
    if role == ROLE_ADMIN_SUCURSAL and scoped_sucursal_id is not None and report_sucursal_id is None:
        return
    if (
        scoped_sucursal_id is not None
        and report_sucursal_id != scoped_sucursal_id
        and not emergency_has_candidate_for_sucursal(int(report["id"]), int(scoped_sucursal_id))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")


def _resolve_candidate_scope(
    workshop_id: int | None,
    current_user: TokenPayload | None,
) -> tuple[int | None, int | None]:
    resolved_workshop_id = workshop_id
    resolved_sucursal_id = _scoped_sucursal_id(current_user)
    if resolved_workshop_id is None and resolved_sucursal_id is not None:
        workshop = get_workshop_by_sucursal(int(resolved_sucursal_id))
        if workshop and workshop.get("id") is not None:
            resolved_workshop_id = int(workshop["id"])
    return resolved_workshop_id, resolved_sucursal_id


def _decorate_report_for_candidate_scope(
    report: dict[str, object],
    *,
    workshop_id: int | None,
    current_user: TokenPayload | None,
) -> dict[str, object]:
    report_copy = dict(report)
    resolved_workshop_id, resolved_sucursal_id = _resolve_candidate_scope(workshop_id, current_user)
    candidate = get_emergency_workshop_candidate(
        int(report_copy["id"]),
        workshop_id=resolved_workshop_id,
        sucursal_id=resolved_sucursal_id,
    )
    candidate_status = str(candidate.get("candidate_status")) if candidate and candidate.get("candidate_status") is not None else None
    candidate_message = str(candidate.get("candidate_message")) if candidate and candidate.get("candidate_message") is not None else None
    can_accept = False
    if resolved_workshop_id is not None and candidate_status is not None:
        can_accept = candidate_status == EMERGENCY_CANDIDATE_STATUS_PENDING and str(report_copy.get("emergency_status") or "") in {
            "pendiente",
            "solicitud_recibida",
            "en_revision",
        }
    report_copy["workshop_candidate_status"] = candidate_status
    report_copy["workshop_candidate_message"] = candidate_message
    report_copy["can_accept"] = can_accept
    return report_copy


def _ensure_workshop_is_current_assignee(report: Mapping[str, object], workshop_id: int | None) -> None:
    if workshop_id is None:
        return
    if report.get("nearest_workshop_id") == workshop_id:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE,
    )


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


def _resolve_emergency_creation_client_id(
    current_user: TokenPayload,
    requested_client_id: int | None,
) -> int | None:
    role = normalize_role(current_user.role)
    if role == ROLE_SUPERADMIN_GLOBAL:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    if role == ROLE_CLIENTE:
        if requested_client_id is not None and requested_client_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CLIENT_ID_AJENO_NO_PERMITIDO")
        return current_user.user_id
    if role in {ROLE_SUPERADMIN_TENANT, ROLE_ADMIN_SUCURSAL}:
        if requested_client_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="client_id es requerido")
        return requested_client_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROL_NO_AUTORIZADO_PARA_CREAR_EMERGENCIA")


def _log_emergency_creation_actor(current_user: TokenPayload) -> None:
    if not settings.app_debug:
        return
    logger.info(
        "DEV emergency create actor user_id=%s role=%s normalized_role=%s tenant_id=%s tenant_slug=%s sucursal_id=%s technician_id=%s",
        current_user.user_id,
        current_user.role,
        normalize_role(current_user.role),
        current_user.tenant_id,
        current_user.tenant_slug,
        current_user.sucursal_id,
        current_user.technician_id,
    )


def _client_exists_in_tenant_or_legacy(client_id: int) -> bool:
    try:
        ensure_client_exists(client_id)
        return True
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND or exc.detail != "Cliente no encontrado":
            raise

    tenant = get_tenant()
    tenant_engine = get_engine()
    clear_engine()
    try:
        return get_client_by_id(client_id) is not None
    finally:
        if tenant is not None:
            set_context(tenant_engine, tenant)


def _ensure_client_exists_with_legacy_fallback(client_id: int) -> None:
    if not _client_exists_in_tenant_or_legacy(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


def _offline_sync_error_payload(
    *,
    error_code: str,
    message: str,
    local_id: str | None = None,
    duplicated: bool | None = None,
    emergency_id: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "error_code": error_code,
        "message": message,
    }
    if local_id is not None:
        payload["local_id"] = local_id
    if duplicated is not None:
        payload["duplicated"] = duplicated
    if emergency_id is not None:
        payload["emergency_id"] = emergency_id
    return payload


def _effective_workshop_scope(
    workshop_id: int | None,
    current_user: TokenPayload | None,
) -> int | None:
    role = normalize_role(current_user.role) if current_user is not None else None
    if role in {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO}:
        return workshop_id
    return None


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
    broadcast_to_all_sucursales: bool = False,
) -> tuple[EmergencyReportResponse, bool]:
    # Deduplication: if local_id already exists return the existing report (is_duplicate=True)
    if local_id is not None:
        try:
            existing = get_emergency_report_by_local_id(local_id)
        except OperationalError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
        if existing is not None:
            if client_id is not None and existing.get("client_id") not in {None, client_id}:
                raise OfflineSyncContractError(
                    status_code=status.HTTP_409_CONFLICT,
                    payload=_offline_sync_error_payload(
                        error_code="LOCAL_ID_YA_EXISTE_PARA_OTRO_CLIENTE",
                        message="El local_id ya fue sincronizado por otro cliente del mismo tenant",
                        local_id=local_id,
                        duplicated=False,
                        emergency_id=int(existing["id"]) if existing.get("id") is not None else None,
                    ),
                )
            normalize_emergency_media_fields(existing)
            return EmergencyReportResponse.model_validate(existing), True
    if client_id is not None:
        _ensure_client_exists_with_legacy_fallback(client_id)
    valid_photos = [photo for photo in photos if photo.filename]
    if len(valid_photos) > MAX_EMERGENCY_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se permiten como maximo {MAX_EMERGENCY_PHOTOS} fotos por emergencia",
        )

    photo_paths: list[str] = []
    photo_urls: list[str] = []
    audio_path: str | None = None
    matching_sucursal_ids: list[int] = []
    matching_workshop_ids: list[int] = []
    selected_workshop = get_workshop_by_id(nearest_workshop_id) if nearest_workshop_id is not None else None
    if nearest_workshop_id is not None and selected_workshop is None:
        raise OfflineSyncContractError(
            status_code=status.HTTP_404_NOT_FOUND,
            payload=_offline_sync_error_payload(
                error_code="WORKSHOP_NO_ENCONTRADO_EN_TENANT",
                message="El taller indicado no existe dentro del tenant activo",
            ),
        )
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
        routing_candidates: list[EmergencyRoutingCandidateResponse] = []
        selected_candidate: EmergencyRoutingCandidateResponse | None = None
        if latitude is not None and longitude is not None:
            routing_candidates = find_matching_workshops_for_emergency(
                problem_type=normalized_problem_type,
                problem_type_standardized=standardized_problem_type,
                latitude=float(latitude),
                longitude=float(longitude),
            )
            matching_sucursal_ids = sorted(
                {
                    int(candidate.sucursal_id)
                    for candidate in routing_candidates
                    if candidate.sucursal_id is not None
                }
            )
            matching_workshop_ids = sorted({candidate.workshop_id for candidate in routing_candidates})
        target_specialty = normalize_optional_text(standardized_problem_type or normalized_problem_type)
        selected_workshop_matches_target = (
            selected_workshop is not None
            and workshop_matches_any_emergency_specialty(
                {
                    **selected_workshop,
                    "specialties": [selected_workshop.get("specialty")] if selected_workshop.get("specialty") else [],
                },
                target_specialty,
            )
        )
        if routing_candidates:
            if selected_workshop is None or not selected_workshop_matches_target:
                selected_candidate = routing_candidates[0]
                selected_workshop = get_workshop_by_id(selected_candidate.workshop_id)
                nearest_workshop_id = selected_candidate.workshop_id
            else:
                selected_candidate = next(
                    (candidate for candidate in routing_candidates if candidate.workshop_id == int(selected_workshop["id"])),
                    None,
                )
        if broadcast_to_all_sucursales and selected_workshop is None:
            raise OfflineSyncContractError(
                status_code=status.HTTP_404_NOT_FOUND,
                payload=_offline_sync_error_payload(
                    error_code="NO_HAY_SUCURSALES_COMPATIBLES",
                    message="No hay sucursales activas que atiendan este tipo de emergencia",
                ),
            )
        sucursal_id = None if broadcast_to_all_sucursales else (
            int(selected_workshop["sucursal_id"]) if selected_workshop and selected_workshop.get("sucursal_id") is not None else None
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
                "nearest_workshop_name": (
                    normalize_optional_text(str(selected_workshop.get("workshop_name")))
                    if selected_workshop and selected_workshop.get("workshop_name") is not None
                    else normalize_optional_text(nearest_workshop_name)
                ),
                "nearest_workshop_specialty": (
                    normalize_optional_text(str(selected_workshop.get("specialty")))
                    if selected_workshop and selected_workshop.get("specialty") is not None
                    else normalize_optional_text(nearest_workshop_specialty)
                ),
                "nearest_workshop_zone": (
                    normalize_optional_text(str(selected_workshop.get("zone")))
                    if selected_workshop and selected_workshop.get("zone") is not None
                    else normalize_optional_text(nearest_workshop_zone)
                ),
                "nearest_workshop_distance_meters": (
                    selected_candidate.distance_meters if selected_candidate is not None else nearest_workshop_distance_meters
                ),
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
    except IntegrityError as exc:
        cleanup_uploaded_files(*photo_paths, audio_path)
        if local_id is not None:
            existing = get_emergency_report_by_local_id(local_id)
            if existing is not None:
                if client_id is not None and existing.get("client_id") not in {None, client_id}:
                    raise OfflineSyncContractError(
                        status_code=status.HTTP_409_CONFLICT,
                        payload=_offline_sync_error_payload(
                            error_code="LOCAL_ID_YA_EXISTE_PARA_OTRO_CLIENTE",
                            message="El local_id ya fue sincronizado por otro cliente del mismo tenant",
                            local_id=local_id,
                            duplicated=False,
                            emergency_id=int(existing["id"]) if existing.get("id") is not None else None,
                        ),
                    ) from exc
                normalize_emergency_media_fields(existing)
                return EmergencyReportResponse.model_validate(existing), True
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMERGENCIA_DUPLICADA") from exc
    except OperationalError as exc:
        cleanup_uploaded_files(*photo_paths, audio_path)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    normalize_emergency_media_fields(created)
    try:
        notify_emergency_event(
            "EMERGENCY_REGISTERED",
            created,
            extra_data={
                "matching_sucursal_ids": matching_sucursal_ids,
                "matching_workshop_ids": matching_workshop_ids,
            },
            event_version=str(created.get("created_at") or created.get("id") or "registered"),
        )
    except Exception:
        logger.exception("No se pudo registrar/enviar notificación EMERGENCY_REGISTERED")
    candidate_rows: list[dict[str, object]] = []
    if routing_candidates:
        candidate_rows = [
            {
                "workshop_id": candidate.workshop_id,
                "sucursal_id": candidate.sucursal_id,
                "candidate_status": EMERGENCY_CANDIDATE_STATUS_PENDING,
                "candidate_message": None,
            }
            for candidate in routing_candidates
        ]
    elif selected_workshop is not None and selected_workshop.get("id") is not None:
        candidate_rows = [
            {
                "workshop_id": int(selected_workshop["id"]),
                "sucursal_id": (
                    int(selected_workshop["sucursal_id"])
                    if selected_workshop.get("sucursal_id") is not None
                    else None
                ),
                "candidate_status": EMERGENCY_CANDIDATE_STATUS_PENDING,
                "candidate_message": None,
            }
        ]
    upsert_emergency_workshop_candidates(int(created["id"]), candidate_rows)
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
    current_user: TokenPayload | None = None,
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
    return [
        EmergencyReportListResponse.model_validate(
            _decorate_report_for_candidate_scope(
                row,
                workshop_id=nearest_workshop_id,
                current_user=current_user,
            )
        )
        for row in rows
    ]


def get_emergency_report_detail_service(
    report_id: int,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> EmergencyReportResponse:
    scoped_workshop_id = _effective_workshop_scope(workshop_id, current_user)
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=scoped_workshop_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
    _ensure_report_scope(report, current_user)
    normalize_emergency_media_fields(report)
    return EmergencyReportResponse.model_validate(
        _decorate_report_for_candidate_scope(
            report,
            workshop_id=workshop_id,
            current_user=current_user,
        )
    )


def get_emergency_timeline_service(
    report_id: int,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> EmergencyTimelineResponse:
    scoped_workshop_id = _effective_workshop_scope(workshop_id, current_user)
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=scoped_workshop_id)
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
    scoped_workshop_id = _effective_workshop_scope(workshop_id, current_user)
    try:
        current_report = get_emergency_report_by_id(report_id, nearest_workshop_id=scoped_workshop_id)
        if not current_report and scoped_workshop_id is not None:
            fallback_report = get_emergency_report_by_id(report_id, nearest_workshop_id=None)
            if fallback_report and fallback_report.get("sucursal_id") is None:
                current_report = fallback_report
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
    update_workshop_scope = scoped_workshop_id
    if update_workshop_scope is None and current_report.get("nearest_workshop_id") is not None:
        update_workshop_scope = int(current_report["nearest_workshop_id"])
    if require_workshop_for_active and validated_status == "activo" and update_workshop_scope is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo un taller puede cambiar una emergencia a activo",
        )
    if validated_status == "activo" and scoped_workshop_id is not None:
        candidate = get_emergency_workshop_candidate(report_id, workshop_id=scoped_workshop_id)
        candidate_status = str(candidate.get("candidate_status")) if candidate and candidate.get("candidate_status") is not None else None
        if candidate is None and current_report.get("nearest_workshop_id") != scoped_workshop_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada o no pertenece al taller indicado")
        if (
            candidate_status == EMERGENCY_CANDIDATE_STATUS_ACCEPTED_BY_OTHER
            or (
                current_report.get("sucursal_id") is not None
                and current_report.get("nearest_workshop_id") != scoped_workshop_id
            )
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE)
    if validated_status != "activo":
        _ensure_workshop_is_current_assignee(current_report, scoped_workshop_id)
    inferred_role, inferred_user_id = changed_by_context(
        workshop_id=scoped_workshop_id,
        fallback_role="admin",
    )
    if scoped_workshop_id is None:
        user_role, user_id = _infer_actor_from_current_user(current_user)
        inferred_role = user_role or inferred_role
        inferred_user_id = user_id if user_id is not None else inferred_user_id
    changed_by_role = normalize_optional_text(changed_by_role) or inferred_role
    changed_by_user_id = changed_by_user_id if changed_by_user_id is not None else inferred_user_id
    if (
        validated_status == "activo"
        and scoped_workshop_id is not None
        and current_report.get("sucursal_id") is None
    ):
        workshop = get_workshop_by_id(scoped_workshop_id)
        if not workshop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
        try:
            updated = reassign_emergency_report_to_workshop(
                report_id,
                nearest_workshop_id=scoped_workshop_id,
                nearest_workshop_name=str(workshop.get("workshop_name") or ""),
                nearest_workshop_specialty=normalize_optional_text(str(workshop.get("specialty") or "")),
                nearest_workshop_zone=normalize_optional_text(str(workshop.get("zone") or "")),
                nearest_workshop_distance_meters=(
                    float(current_report["nearest_workshop_distance_meters"])
                    if current_report.get("nearest_workshop_distance_meters") is not None
                    else None
                ),
                sucursal_id=int(workshop["sucursal_id"]) if workshop.get("sucursal_id") is not None else None,
                emergency_status=validated_status,
                previous_status=str(current_report.get("emergency_status") or ""),
                changed_by_role=changed_by_role,
                changed_by_user_id=changed_by_user_id,
                observation=normalize_optional_text(observation),
            )
        except OperationalError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o no pertenece al taller indicado",
            )
        mark_emergency_candidate_winner(
            report_id,
            winner_workshop_id=scoped_workshop_id,
            loser_message=EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE,
        )
        normalize_emergency_media_fields(updated)
        return EmergencyReportResponse.model_validate(
            _decorate_report_for_candidate_scope(
                updated,
                workshop_id=workshop_id,
                current_user=current_user,
            )
        )
    try:
        updated = update_emergency_status(
            report_id,
            validated_status,
            nearest_workshop_id=update_workshop_scope,
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
    if validated_status == "activo" and scoped_workshop_id is not None:
        candidate = get_emergency_workshop_candidate(report_id, workshop_id=scoped_workshop_id)
        if candidate and str(candidate.get("candidate_status")) == EMERGENCY_CANDIDATE_STATUS_ACCEPTED_BY_OTHER:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE)
        mark_emergency_candidate_winner(
            report_id,
            winner_workshop_id=scoped_workshop_id,
            loser_message=EMERGENCY_ACCEPTED_BY_OTHER_MESSAGE,
        )
    normalize_emergency_media_fields(updated)
    return EmergencyReportResponse.model_validate(
        _decorate_report_for_candidate_scope(
            updated,
            workshop_id=workshop_id,
            current_user=current_user,
        )
    )


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
        try:
            notify_emergency_event(
                "REQUEST_ACCEPTED",
                updated.model_dump(),
                event_version=f"accepted:{payload.emergency_status}",
            )
        except Exception:
            logger.exception("No se pudo registrar/enviar notificación REQUEST_ACCEPTED para emergencia %s", report_id)
    _emit_emergency_status_realtime_events(updated.model_dump())
    return updated


def update_emergency_timeline_status_service(
    report_id: int,
    payload: EmergencyTimelineStatusUpdate,
    workshop_id: int | None,
    current_user: TokenPayload,
) -> EmergencyTimelineResponse:
    normalized_requested_status = validate_supported_emergency_status(payload.estado)
    if normalize_role(current_user.role) == ROLE_TECNICO and normalized_requested_status not in {
        "auxilio_en_camino",
        "tecnico_en_sitio",
        "servicio_en_proceso",
        "servicio_finalizado",
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ESTADO_NO_PERMITIDO_PARA_TECNICO")
    updated = change_emergency_status_service(
        report_id,
        normalized_requested_status,
        workshop_id,
        current_user,
        observation=payload.observacion,
        latitud_llegada=payload.latitud_llegada,
        longitud_llegada=payload.longitud_llegada,
    )
    normalized_status = normalized_requested_status
    event_type = {
        "auxilio_en_camino": "TECHNICIAN_ON_THE_WAY",
        "tecnico_en_sitio": "TECHNICIAN_ARRIVED",
        "servicio_en_proceso": "SERVICE_STARTED",
        "servicio_finalizado": "SERVICE_FINISHED",
        "solicitud_cancelada": "SERVICE_CANCELLED",
    }.get(normalized_status, "EMERGENCY_STATUS_CHANGED")
    try:
        notify_emergency_event(
            event_type,
            updated.model_dump(),
            extra_data={
                "status": normalized_status,
                "status_label": EMERGENCY_STATUS_NOTIFICATION_LABELS.get(normalized_status, normalized_status),
            },
            event_version=normalized_status,
        )
    except Exception:
        logger.exception(
            "No se pudo registrar/enviar notificación %s para emergencia %s",
            event_type,
            report_id,
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
    _ensure_workshop_is_current_assignee(report, effective_workshop_id)

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
            try:
                notify_emergency_event(
                    "REQUEST_REJECTED",
                    updated.model_dump(),
                    extra_data={
                        "status": "solicitud_cancelada",
                        "status_label": "Solicitud rechazada",
                        "rejection_reason": rejection_reason,
                    },
                    event_version=rejection_reason,
                )
            except Exception:
                logger.exception(
                    "No se pudo registrar/enviar notificación REQUEST_REJECTED para emergencia %s",
                    report_id,
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
    _ensure_workshop_is_current_assignee(report, workshop_id)
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
    try:
        notify_emergency_event(
            "TECHNICIAN_ASSIGNED",
            updated_report,
            extra_data=push_data,
            event_version=f"technician:{payload.technician_id}",
        )
    except Exception:
        logger.exception(
            "No se pudo registrar/enviar notificación TECHNICIAN_ASSIGNED para emergencia %s",
            report_id,
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
    scoped_workshop_id = _effective_workshop_scope(workshop_id, current_user)
    try:
        report = get_emergency_report_by_id(report_id, nearest_workshop_id=scoped_workshop_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergencia no encontrada o no pertenece al taller indicado",
            )
        _ensure_report_scope(report, current_user)
        role = normalize_role(current_user.role)
        if role not in {ROLE_TECNICO, ROLE_ADMIN_SUCURSAL, ROLE_SUPERADMIN_TENANT}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ROL_NO_AUTORIZADO_PARA_REPORTAR_UBICACION",
            )
        effective_technician_id = get_effective_technician_id(current_user) if role == ROLE_TECNICO else None
        resolved_technician_id = payload.technician_id
        if role == ROLE_TECNICO:
            resolved_technician_id = effective_technician_id
        if role == ROLE_TECNICO and payload.technician_id is not None and payload.technician_id != effective_technician_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TECNICO_NO_PUEDE_REPORTAR_UBICACION_DE_OTRO_USUARIO",
            )
        assigned_technician_id = int(report["assigned_technician_id"]) if report.get("assigned_technician_id") is not None else None
        if assigned_technician_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La emergencia no tiene un tecnico asignado para reportar tracking",
            )
        if resolved_technician_id is None:
            resolved_technician_id = assigned_technician_id
        if assigned_technician_id != resolved_technician_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La ubicacion no corresponde al tecnico asignado a esta emergencia",
            )
        tracking_point = create_emergency_tracking_point(
            {
                "emergency_id": report_id,
                "technician_id": resolved_technician_id,
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "source": normalize_optional_text(payload.source) or "system",
                "heading": payload.heading,
                "speed": payload.speed,
                "accuracy": payload.accuracy,
            }
        )
        refreshed_report = get_emergency_report_by_id(report_id, nearest_workshop_id=scoped_workshop_id)
        if not refreshed_report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergencia no encontrada")
        tracking_response = build_emergency_tracking_response(refreshed_report)
        _emit_emergency_realtime_events(
            "tracking_location_updated",
            refreshed_report,
            include_technician=False,
            payload={
                "technician_id": resolved_technician_id,
                "tracking_latitude": payload.latitude,
                "tracking_longitude": payload.longitude,
                "tracking_source": normalize_optional_text(payload.source) or "system",
                "tracking_heading": payload.heading,
                "tracking_speed": payload.speed,
                "tracking_accuracy": payload.accuracy,
                "tracking_updated_at": tracking_point.get("created_at"),
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
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyReportResponse:
    _log_emergency_creation_actor(current_user)
    effective_client_id = _resolve_emergency_creation_client_id(current_user, client_id)
    _ensure_workshop_scope(nearest_workshop_id, current_user)
    broadcast_to_all_sucursales = normalize_role(current_user.role) == ROLE_CLIENTE
    try:
        report, is_duplicate = register_emergency_service(
            local_id=local_id,
            client_id=effective_client_id,
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
            broadcast_to_all_sucursales=broadcast_to_all_sucursales,
        )
    except OfflineSyncContractError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    if is_duplicate:
        http_response.status_code = status.HTTP_200_OK
    return report


@router.get(
    f"{settings.api_prefix}/emergencias/routing-preview",
    response_model=EmergencyRoutingPreviewResponse,
)
def get_emergency_routing_preview(
    problem_type: str = Query(min_length=2, max_length=120),
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    description: str | None = Query(default=None, max_length=4000),
    current_user: TokenPayload = Depends(get_current_user),
) -> EmergencyRoutingPreviewResponse:
    _log_emergency_creation_actor(current_user)
    return build_emergency_routing_preview(
        problem_type=problem_type,
        description=description,
        latitude=latitude,
        longitude=longitude,
    )


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
        current_user,
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
