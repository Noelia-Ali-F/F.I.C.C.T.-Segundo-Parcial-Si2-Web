from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import (
    get_workshop_by_id,
    list_clients,
    list_emergency_reports,
    list_emergency_status_history,
    list_technicians,
    list_technicians_by_workshop,
    list_workshop_registrations,
)

router = APIRouter(tags=["dashboard"])

LEGACY_TO_TIMELINE_STATUS_MAP = {
    "pendiente": "solicitud_recibida",
    "activo": "auxilio_asignado",
    "rechazado": "solicitud_cancelada",
}

STATUS_LABELS = {
    "solicitud_recibida": "Solicitud recibida",
    "en_revision": "En revisión",
    "auxilio_asignado": "Auxilio asignado",
    "auxilio_en_camino": "Auxilio en camino",
    "servicio_en_proceso": "Servicio en proceso",
    "servicio_finalizado": "Servicio finalizado",
    "solicitud_cancelada": "Solicitud cancelada",
}

STATUS_ORDER = [
    "solicitud_recibida",
    "en_revision",
    "auxilio_asignado",
    "auxilio_en_camino",
    "servicio_en_proceso",
    "servicio_finalizado",
    "solicitud_cancelada",
]

PENDING_STATUSES = {"solicitud_recibida", "en_revision"}
ACTIVE_STATUSES = {"auxilio_asignado", "auxilio_en_camino", "servicio_en_proceso"}
COMPLETED_STATUSES = {"servicio_finalizado"}
CANCELLED_STATUSES = {"solicitud_cancelada"}


class DashboardKpiResponse(BaseModel):
    label: str
    value: str
    detail: str
    trend: str
    tone: str


class DashboardStatusBreakdownItemResponse(BaseModel):
    status: str
    label: str
    count: int


class DashboardMetricSummaryResponse(BaseModel):
    label: str
    value: str
    detail: str


class DashboardTenantRankingItemResponse(BaseModel):
    workshop_id: int | None = None
    workshop_name: str
    total_requests: int
    active_requests: int
    completed_requests: int
    cancelled_requests: int
    technicians_available: int


class DashboardZoneBreakdownItemResponse(BaseModel):
    zone: str
    count: int


class DashboardRecentEmergencyItemResponse(BaseModel):
    emergency_id: int
    code: str
    client_name: str
    vehicle_name: str
    status: str
    status_label: str
    workshop_name: str | None = None
    created_at: datetime


class DashboardOperationalOverviewResponse(BaseModel):
    scope: str
    workshop_id: int | None = None
    workshop_name: str | None = None
    generated_at: datetime
    kpis: list[DashboardKpiResponse] = Field(default_factory=list)
    summary: list[DashboardMetricSummaryResponse] = Field(default_factory=list)
    status_breakdown: list[DashboardStatusBreakdownItemResponse] = Field(default_factory=list)
    tenant_ranking: list[DashboardTenantRankingItemResponse] = Field(default_factory=list)
    zone_breakdown: list[DashboardZoneBreakdownItemResponse] = Field(default_factory=list)
    recent_emergencies: list[DashboardRecentEmergencyItemResponse] = Field(default_factory=list)


def normalize_status(raw_status: str | None) -> str:
    if not raw_status:
        return "solicitud_recibida"
    return LEGACY_TO_TIMELINE_STATUS_MAP.get(raw_status, raw_status)


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def to_aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def minutes_between(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    delta_minutes = (end - start).total_seconds() / 60
    return delta_minutes if delta_minutes >= 0 else None


def average_value(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def format_minutes(value: float | None) -> str:
    if value is None:
        return "Sin datos"
    return f"{round(value)} min"


def format_currency(value: int | float | None) -> str:
    amount = float(value or 0)
    return f"Bs {amount:,.0f}"


def build_dashboard_operational_overview(workshop_id: int | None) -> DashboardOperationalOverviewResponse:
    try:
        workshop = get_workshop_by_id(workshop_id) if workshop_id is not None else None
        if workshop_id is not None and not workshop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

        reports = list_emergency_reports(nearest_workshop_id=workshop_id)
        technicians = list_technicians_by_workshop(workshop_id) if workshop_id is not None else list_technicians()
        workshops = list_workshop_registrations()
        clients = [] if workshop_id is not None else list_clients()
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    now_utc = datetime.now(timezone.utc)
    today_utc = now_utc.date()
    status_counts = {status_name: 0 for status_name in STATUS_ORDER}
    zone_counts: dict[str, int] = defaultdict(int)
    first_action_minutes: list[float] = []
    assignment_minutes: list[float] = []
    resolution_minutes: list[float] = []
    total_revenue = 0
    total_today = 0
    recent_emergencies: list[DashboardRecentEmergencyItemResponse] = []

    for report in reports:
        normalized = normalize_status(str(report.get("emergency_status")) if report.get("emergency_status") is not None else None)
        status_counts[normalized] = status_counts.get(normalized, 0) + 1

        created_at = to_aware_datetime(report.get("created_at"))
        if created_at and created_at.date() == today_utc:
            total_today += 1

        zone_value = str(report.get("zone") or report.get("nearest_workshop_zone") or "Sin zona")
        zone_counts[zone_value] += 1

        if normalized in COMPLETED_STATUSES:
            total_revenue += int(report.get("price") or 0)

        history_rows = list_emergency_status_history(int(report["id"]))
        first_action_at: datetime | None = None
        assignment_at: datetime | None = None
        resolution_at: datetime | None = None

        for history_row in history_rows:
            history_status = normalize_status(str(history_row.get("new_status")) if history_row.get("new_status") is not None else None)
            history_created_at = to_aware_datetime(history_row.get("created_at"))
            if history_status != "solicitud_recibida" and first_action_at is None:
                first_action_at = history_created_at
            if history_status == "auxilio_asignado" and assignment_at is None:
                assignment_at = history_created_at
            if history_status == "servicio_finalizado" and resolution_at is None:
                resolution_at = history_created_at

        first_action_delta = minutes_between(created_at, first_action_at)
        assignment_delta = minutes_between(created_at, assignment_at)
        resolution_delta = minutes_between(created_at, resolution_at)
        if first_action_delta is not None:
            first_action_minutes.append(first_action_delta)
        if assignment_delta is not None:
            assignment_minutes.append(assignment_delta)
        if resolution_delta is not None:
            resolution_minutes.append(resolution_delta)

    available_technicians = sum(1 for technician in technicians if technician.get("status") == "disponible")
    busy_technicians = sum(1 for technician in technicians if technician.get("status") == "ocupado")
    out_of_service_technicians = sum(1 for technician in technicians if technician.get("status") == "fuera_de_servicio")
    pending_count = sum(status_counts.get(item, 0) for item in PENDING_STATUSES)
    active_count = sum(status_counts.get(item, 0) for item in ACTIVE_STATUSES)
    completed_count = sum(status_counts.get(item, 0) for item in COMPLETED_STATUSES)
    cancelled_count = sum(status_counts.get(item, 0) for item in CANCELLED_STATUSES)
    active_workshops = [current_workshop for current_workshop in workshops if current_workshop.get("approval_status") == "activo"]
    active_clients = sum(1 for client in clients if client.get("status") == "active")
    unique_zones = len({str(workshop_item.get("zone")).strip() for workshop_item in active_workshops if workshop_item.get("zone")})

    status_breakdown = [
        DashboardStatusBreakdownItemResponse(status=status_name, label=status_label(status_name), count=status_counts.get(status_name, 0))
        for status_name in STATUS_ORDER
    ]

    zone_breakdown = [
        DashboardZoneBreakdownItemResponse(zone=zone_name, count=count)
        for zone_name, count in sorted(zone_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    ]

    for report in reports[:6]:
        normalized = normalize_status(str(report.get("emergency_status")) if report.get("emergency_status") is not None else None)
        recent_emergencies.append(
            DashboardRecentEmergencyItemResponse(
                emergency_id=int(report["id"]),
                code=f"EMG-{int(report['id']):06d}",
                client_name=str(report.get("client_name") or f"Cliente #{report.get('client_id') or 'N/A'}"),
                vehicle_name=str(report.get("vehicle_name") or "Vehículo no registrado"),
                status=normalized,
                status_label=status_label(normalized),
                workshop_name=str(report.get("nearest_workshop_name")) if report.get("nearest_workshop_name") else None,
                created_at=to_aware_datetime(report.get("created_at")) or now_utc,
            )
        )

    avg_first_action = average_value(first_action_minutes)
    avg_assignment = average_value(assignment_minutes)
    avg_resolution = average_value(resolution_minutes)

    if workshop_id is not None:
        kpis = [
            DashboardKpiResponse(
                label="Solicitudes hoy",
                value=str(total_today),
                detail="Emergencias registradas hoy para este taller tenant.",
                trend="Tenant",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Pendientes",
                value=str(pending_count),
                detail="Solicitudes pendientes o en revisión dentro del taller.",
                trend="Backlog",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="En operación",
                value=str(active_count),
                detail="Servicios ya aceptados y actualmente en atención.",
                trend="Live",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Finalizadas",
                value=str(completed_count),
                detail="Servicios cerrados correctamente por el tenant.",
                trend="Cierre",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Técnicos disponibles",
                value=str(available_technicians),
                detail="Personal listo para tomar nuevas solicitudes del taller.",
                trend="Equipo",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Facturación",
                value=format_currency(total_revenue),
                detail="Monto acumulado de servicios finalizados del taller.",
                trend="Bs",
                tone="gold",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio entre solicitud recibida y primera acción registrada.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de asignación",
                value=format_minutes(avg_assignment),
                detail="Promedio hasta dejar el auxilio asignado dentro del flujo.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio hasta servicio finalizado para este tenant.",
            ),
            DashboardMetricSummaryResponse(
                label="Estado del equipo",
                value=f"{busy_technicians} ocupados / {available_technicians} libres",
                detail=f"{out_of_service_technicians} técnicos fuera de servicio en este momento.",
            ),
        ]
        tenant_ranking: list[DashboardTenantRankingItemResponse] = []
        overview_scope = "workshop"
        overview_workshop_name = str(workshop.get("workshop_name")) if workshop else None
    else:
        technicians_by_workshop: dict[int, list[dict[str, object]]] = defaultdict(list)
        for technician in technicians:
            workshop_key = int(technician["workshop_id"]) if technician.get("workshop_id") is not None else 0
            technicians_by_workshop[workshop_key].append(technician)

        reports_by_workshop: dict[int, list[dict[str, object]]] = defaultdict(list)
        for report in reports:
            workshop_key = int(report["nearest_workshop_id"]) if report.get("nearest_workshop_id") is not None else 0
            reports_by_workshop[workshop_key].append(report)

        tenant_ranking = []
        for workshop_item in active_workshops:
            workshop_key = int(workshop_item["id"])
            workshop_reports = reports_by_workshop.get(workshop_key, [])
            workshop_statuses = [normalize_status(str(item.get("emergency_status")) if item.get("emergency_status") is not None else None) for item in workshop_reports]
            workshop_active = sum(1 for current_status in workshop_statuses if current_status in ACTIVE_STATUSES)
            workshop_completed = sum(1 for current_status in workshop_statuses if current_status in COMPLETED_STATUSES)
            workshop_cancelled = sum(1 for current_status in workshop_statuses if current_status in CANCELLED_STATUSES)
            workshop_available = sum(
                1 for technician in technicians_by_workshop.get(workshop_key, []) if technician.get("status") == "disponible"
            )
            tenant_ranking.append(
                DashboardTenantRankingItemResponse(
                    workshop_id=workshop_key,
                    workshop_name=str(workshop_item.get("workshop_name") or f"Taller #{workshop_key}"),
                    total_requests=len(workshop_reports),
                    active_requests=workshop_active,
                    completed_requests=workshop_completed,
                    cancelled_requests=workshop_cancelled,
                    technicians_available=workshop_available,
                )
            )

        tenant_ranking.sort(
            key=lambda item: (-item.total_requests, -item.completed_requests, item.cancelled_requests, item.workshop_name.lower())
        )
        kpis = [
            DashboardKpiResponse(
                label="Talleres activos",
                value=str(len(active_workshops)),
                detail="Tenants habilitados para operar dentro del sistema.",
                trend="MT",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Solicitudes hoy",
                value=str(total_today),
                detail="Emergencias registradas hoy en toda la plataforma.",
                trend="Global",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Finalizadas",
                value=str(completed_count),
                detail="Servicios cerrados por todos los talleres del sistema.",
                trend="Cierre",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Canceladas",
                value=str(cancelled_count),
                detail="Solicitudes canceladas o rechazadas a nivel global.",
                trend="Riesgo",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Técnicos disponibles",
                value=str(available_technicians),
                detail="Capacidad operativa disponible entre todos los tenants.",
                trend="Equipo",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Cobertura",
                value=f"{unique_zones} zonas",
                detail="Zonas activas cubiertas por talleres aprobados.",
                trend="Mapa",
                tone="gold",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio global entre el registro y la primera acción operativa.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de asignación",
                value=format_minutes(avg_assignment),
                detail="Promedio global hasta dejar el auxilio asignado.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio global hasta servicio finalizado.",
            ),
            DashboardMetricSummaryResponse(
                label="Clientes activos",
                value=str(active_clients),
                detail="Usuarios con acceso móvil habilitado dentro del sistema.",
            ),
        ]
        overview_scope = "global"
        overview_workshop_name = None

    return DashboardOperationalOverviewResponse(
        scope=overview_scope,
        workshop_id=workshop_id,
        workshop_name=overview_workshop_name,
        generated_at=now_utc,
        kpis=kpis,
        summary=summary,
        status_breakdown=status_breakdown,
        tenant_ranking=tenant_ranking[:6],
        zone_breakdown=zone_breakdown,
        recent_emergencies=recent_emergencies,
    )


@router.get(
    f"{settings.api_prefix}/dashboard/operational-overview",
    response_model=DashboardOperationalOverviewResponse,
)
def get_dashboard_operational_overview(
    workshop_id: int | None = Query(default=None, ge=1),
) -> DashboardOperationalOverviewResponse:
    return build_dashboard_operational_overview(workshop_id)
