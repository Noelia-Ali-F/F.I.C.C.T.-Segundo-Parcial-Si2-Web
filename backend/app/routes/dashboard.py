from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import (
    get_workshop_by_id,
    list_clients,
    list_clients_by_tenant,
    list_emergency_reports,
    list_emergency_reports_by_tenant,
    list_emergency_status_history,
    list_technicians,
    list_technicians_by_tenant,
    list_technicians_by_workshop,
    list_workshop_registrations,
    list_workshops_by_tenant,
)
from app.saas_master import get_master_engine
from app.tenant_context import get_engine as get_current_engine
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    TokenPayload,
    get_effective_technician_id,
    get_current_user_optional,
    get_tenant_id_for_query,
    normalize_role,
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
SLA_ASIGNACION_MINUTOS = 10
SLA_LLEGADA_MINUTOS = 30
ACTIVE_TECHNICIAN_STATUSES = {"disponible", "ocupado"}


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


class DashboardIncidentTypeBreakdownItemResponse(BaseModel):
    incident_type: str
    label: str
    count: int


class DashboardEfficiencyRankingItemResponse(BaseModel):
    workshop_id: int | None = None
    workshop_name: str
    completed_services: int
    avg_assignment_minutes: float | None = None
    avg_arrival_minutes: float | None = None
    avg_resolution_minutes: float | None = None
    sla_compliance_percent: float | None = None


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
    analytics_summary: list[DashboardMetricSummaryResponse] = Field(default_factory=list)
    incident_type_breakdown: list[DashboardIncidentTypeBreakdownItemResponse] = Field(default_factory=list)
    efficiency_ranking: list[DashboardEfficiencyRankingItemResponse] = Field(default_factory=list)
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


def format_percent(value: float | None) -> str:
    if value is None:
        return "No disponible"
    return f"{round(value, 1):.1f}%"


def is_active_technician(technician: dict[str, object]) -> bool:
    return str(technician.get("status") or "").strip().lower() in ACTIVE_TECHNICIAN_STATUSES


def normalize_incident_type(report: dict[str, object]) -> tuple[str, str]:
    raw_type = str(
        report.get("problem_type_standardized")
        or report.get("photo_problem_type_standardized")
        or report.get("problem_type")
        or "Otro"
    ).strip()
    normalized = raw_type.casefold()
    if "bater" in normalized:
        return "bateria", "Batería"
    if "neum" in normalized or "llanta" in normalized:
        return "llanta", "Llanta"
    if "motor" in normalized:
        return "motor", "Motor"
    if "accidente" in normalized or "choque" in normalized or "colisi" in normalized:
        return "choque", "Choque"
    return "otros", "Otros"


def _table_exists(connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _load_tenant_quotation_metrics(
    *,
    role: str,
    current_user: TokenPayload | None,
    sucursal_id: int | None,
) -> dict[str, int]:
    if current_user is None or current_user.tenant_id is None:
        return {
            "quotation_requests_count": 0,
            "quotation_offers_count": 0,
            "accepted_offers_count": 0,
        }

    try:
        with get_current_engine().connect() as connection:
            if not _table_exists(connection, "quotation_requests") or not _table_exists(connection, "quotation_offers"):
                return {
                    "quotation_requests_count": 0,
                    "quotation_offers_count": 0,
                    "accepted_offers_count": 0,
                }

            if role == ROLE_CLIENTE:
                request_count = connection.execute(
                    text("SELECT COUNT(*) FROM quotation_requests WHERE client_id = :client_id"),
                    {"client_id": current_user.user_id},
                ).scalar() or 0
                offer_row = connection.execute(
                    text(
                        """
                        SELECT
                            COUNT(*) AS quotation_offers_count,
                            COUNT(*) FILTER (
                                WHERE qo.status IN ('aceptada', 'seleccionada', 'selected')
                            ) AS accepted_offers_count
                        FROM quotation_offers qo
                        JOIN quotation_requests qr ON qr.id = qo.quotation_request_id
                        WHERE qr.client_id = :client_id
                        """
                    ),
                    {"client_id": current_user.user_id},
                ).mappings().one()
                return {
                    "quotation_requests_count": int(request_count),
                    "quotation_offers_count": int(offer_row.get("quotation_offers_count") or 0),
                    "accepted_offers_count": int(offer_row.get("accepted_offers_count") or 0),
                }

            if role == ROLE_ADMIN_SUCURSAL and sucursal_id is not None and _table_exists(connection, "quotation_request_workshops"):
                request_count = connection.execute(
                    text(
                        """
                        SELECT COUNT(DISTINCT qr.id)
                        FROM quotation_requests qr
                        JOIN quotation_request_workshops qrw ON qrw.quotation_request_id = qr.id
                        JOIN workshop_registrations wr ON wr.id = qrw.workshop_id
                        WHERE wr.sucursal_id = :sucursal_id
                        """
                    ),
                    {"sucursal_id": sucursal_id},
                ).scalar() or 0
                offer_row = connection.execute(
                    text(
                        """
                        SELECT
                            COUNT(*) AS quotation_offers_count,
                            COUNT(*) FILTER (
                                WHERE qo.status IN ('aceptada', 'seleccionada', 'selected')
                            ) AS accepted_offers_count
                        FROM quotation_offers qo
                        JOIN workshop_registrations wr ON wr.id = qo.workshop_id
                        WHERE wr.sucursal_id = :sucursal_id
                        """
                    ),
                    {"sucursal_id": sucursal_id},
                ).mappings().one()
                return {
                    "quotation_requests_count": int(request_count),
                    "quotation_offers_count": int(offer_row.get("quotation_offers_count") or 0),
                    "accepted_offers_count": int(offer_row.get("accepted_offers_count") or 0),
                }

            request_count = connection.execute(text("SELECT COUNT(*) FROM quotation_requests")).scalar() or 0
            offer_row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS quotation_offers_count,
                        COUNT(*) FILTER (
                            WHERE status IN ('aceptada', 'seleccionada', 'selected')
                        ) AS accepted_offers_count
                    FROM quotation_offers
                    """
                )
            ).mappings().one()
            return {
                "quotation_requests_count": int(request_count),
                "quotation_offers_count": int(offer_row.get("quotation_offers_count") or 0),
                "accepted_offers_count": int(offer_row.get("accepted_offers_count") or 0),
            }
    except OperationalError:
        return {
            "quotation_requests_count": 0,
            "quotation_offers_count": 0,
            "accepted_offers_count": 0,
        }


def _build_global_saas_overview() -> DashboardOperationalOverviewResponse:
    try:
        with get_master_engine().connect() as connection:
            metrics_row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_tenants,
                        COUNT(*) FILTER (WHERE estado = 'activo') AS tenants_activos,
                        COUNT(*) FILTER (WHERE estado = 'inactivo') AS tenants_inactivos,
                        COUNT(*) FILTER (WHERE estado = 'suspendido') AS tenants_suspendidos,
                        COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS altas_recientes_7d
                    FROM saas_tenants
                    """
                )
            ).mappings().one()
            subscriptions_row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE estado = 'activo'
                            AND (fecha_fin IS NULL OR fecha_fin > NOW())
                        ) AS suscripciones_activas,
                        COALESCE(SUM(monto), 0) AS ingresos_plataforma
                    FROM suscripciones
                    """
                )
            ).mappings().one()
            plans_row = connection.execute(
                text("SELECT COUNT(*) AS total_planes_activos FROM planes WHERE estado = 'activo'")
            ).mappings().one()
            plan_rows = connection.execute(
                text(
                    """
                    SELECT
                        COALESCE(p.nombre, 'Sin plan') AS plan_nombre,
                        COUNT(*) AS total
                    FROM saas_tenants st
                    LEFT JOIN planes p ON p.id = st.plan_id
                    GROUP BY COALESCE(p.nombre, 'Sin plan')
                    ORDER BY total DESC, plan_nombre ASC
                    """
                )
            ).mappings().all()
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    now_utc = datetime.now(timezone.utc)
    total_tenants = int(metrics_row.get("total_tenants") or 0)
    tenants_activos = int(metrics_row.get("tenants_activos") or 0)
    tenants_inactivos = int(metrics_row.get("tenants_inactivos") or 0)
    tenants_suspendidos = int(metrics_row.get("tenants_suspendidos") or 0)
    altas_recientes = int(metrics_row.get("altas_recientes_7d") or 0)
    suscripciones_activas = int(subscriptions_row.get("suscripciones_activas") or 0)
    ingresos_plataforma = float(subscriptions_row.get("ingresos_plataforma") or 0)
    total_planes = int(plans_row.get("total_planes_activos") or 0)

    kpis = [
        DashboardKpiResponse(
            label="Total tenants",
            value=str(total_tenants),
            detail="Empresas registradas en saas_master.",
            trend="SaaS",
            tone="gold",
        ),
        DashboardKpiResponse(
            label="Tenants activos",
            value=str(tenants_activos),
            detail="Tenants con estado operativo activo.",
            trend="Live",
            tone="teal",
        ),
        DashboardKpiResponse(
            label="Tenants inactivos",
            value=str(tenants_inactivos),
            detail="Tenants deshabilitados explícitamente.",
            trend="Estado",
            tone="blue",
        ),
        DashboardKpiResponse(
            label="Suscripciones activas",
            value=str(suscripciones_activas),
            detail="Suscripciones vigentes registradas en saas_master.",
            trend="MRR",
            tone="blue",
        ),
        DashboardKpiResponse(
            label="Ingresos plataforma",
            value=format_currency(ingresos_plataforma),
            detail="Suma real del campo monto en suscripciones.",
            trend="Bs",
            tone="gold",
        ),
        DashboardKpiResponse(
            label="Planes activos",
            value=str(total_planes),
            detail="Planes habilitados actualmente en el catálogo SaaS.",
            trend="Catálogo",
            tone="teal",
        ),
    ]
    summary = [
        DashboardMetricSummaryResponse(
            label="Altas recientes",
            value=str(altas_recientes),
            detail="Tenants creados durante los últimos 7 días.",
        ),
        DashboardMetricSummaryResponse(
            label="Suspendidos",
            value=str(tenants_suspendidos),
            detail="Tenants bloqueados temporalmente por estado suspendido.",
        ),
        DashboardMetricSummaryResponse(
            label="Tenants con plan",
            value=str(sum(int(row.get("total") or 0) for row in plan_rows if row.get("plan_nombre") != "Sin plan")),
            detail="Empresas que ya tienen un plan asociado en saas_master.",
        ),
    ]
    status_breakdown = [
        DashboardStatusBreakdownItemResponse(status="auxilio_asignado", label="Activos", count=tenants_activos),
        DashboardStatusBreakdownItemResponse(status="solicitud_cancelada", label="Inactivos", count=tenants_inactivos),
        DashboardStatusBreakdownItemResponse(status="en_revision", label="Suspendidos", count=tenants_suspendidos),
    ]
    zone_breakdown = [
        DashboardZoneBreakdownItemResponse(
            zone=str(row.get("plan_nombre") or "Sin plan"),
            count=int(row.get("total") or 0),
        )
        for row in plan_rows[:6]
    ]
    return DashboardOperationalOverviewResponse(
        scope="global_saas",
        workshop_id=None,
        workshop_name=None,
        generated_at=now_utc,
        kpis=kpis,
        summary=summary,
        status_breakdown=status_breakdown,
        tenant_ranking=[],
        zone_breakdown=zone_breakdown,
        analytics_summary=[],
        incident_type_breakdown=[],
        efficiency_ranking=[],
        recent_emergencies=[],
    )


def build_dashboard_operational_overview(
    workshop_id: int | None,
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
    current_user: TokenPayload | None = None,
) -> DashboardOperationalOverviewResponse:
    role = normalize_role(current_user.role) if current_user is not None else ""
    if role == ROLE_SUPERADMIN_GLOBAL and workshop_id is None:
        return _build_global_saas_overview()

    report_client_id = current_user.user_id if role == ROLE_CLIENTE and current_user is not None else None
    report_technician_id = get_effective_technician_id(current_user) if role == ROLE_TECNICO and current_user is not None else None
    try:
        workshop = get_workshop_by_id(workshop_id) if workshop_id is not None else None
        if workshop_id is not None and not workshop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")

        if workshop_id is not None:
            reports = list_emergency_reports(nearest_workshop_id=workshop_id)
            technicians = list_technicians_by_workshop(workshop_id)
        elif tenant_id is not None:
            reports = list_emergency_reports_by_tenant(
                tenant_id=tenant_id,
                sucursal_id=sucursal_id,
                client_id=report_client_id,
                technician_id=report_technician_id,
            )
            technicians = list_technicians_by_tenant(tenant_id, sucursal_id)
        else:
            reports = list_emergency_reports()
            technicians = list_technicians()

        if tenant_id is not None and workshop_id is None:
            workshops = list_workshops_by_tenant(tenant_id, sucursal_id)
            clients = list_clients_by_tenant(tenant_id) if role in {ROLE_SUPERADMIN_TENANT, ROLE_ADMIN_SUCURSAL} else []
        else:
            workshops = list_workshop_registrations()
            clients = [] if workshop_id is not None else list_clients()
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    now_utc = datetime.now(timezone.utc)
    today_utc = now_utc.date()
    status_counts = {status_name: 0 for status_name in STATUS_ORDER}
    zone_counts: dict[str, int] = defaultdict(int)
    incident_type_counts: dict[tuple[str, str], int] = defaultdict(int)
    first_action_minutes: list[float] = []
    assignment_minutes: list[float] = []
    arrival_minutes: list[float] = []
    resolution_minutes: list[float] = []
    workshop_assignment_minutes: dict[int, list[float]] = defaultdict(list)
    workshop_arrival_minutes: dict[int, list[float]] = defaultdict(list)
    workshop_resolution_minutes: dict[int, list[float]] = defaultdict(list)
    workshop_completed_counts: dict[int, int] = defaultdict(int)
    workshop_sla_evaluable_counts: dict[int, int] = defaultdict(int)
    workshop_sla_compliant_counts: dict[int, int] = defaultdict(int)
    sla_evaluable_services = 0
    sla_compliant_services = 0
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
        incident_type_key = normalize_incident_type(report)
        incident_type_counts[incident_type_key] += 1

        if normalized in COMPLETED_STATUSES:
            total_revenue += int(report.get("price") or 0)

        history_rows = list_emergency_status_history(int(report["id"]))
        first_action_at: datetime | None = None
        assignment_at: datetime | None = None
        arrival_at: datetime | None = None
        resolution_at: datetime | None = None

        for history_row in history_rows:
            history_status = normalize_status(str(history_row.get("new_status")) if history_row.get("new_status") is not None else None)
            history_created_at = to_aware_datetime(history_row.get("created_at"))
            if history_status != "solicitud_recibida" and first_action_at is None:
                first_action_at = history_created_at
            if history_status == "auxilio_asignado" and assignment_at is None:
                assignment_at = history_created_at
            if history_status == "tecnico_en_sitio" and arrival_at is None:
                arrival_at = history_created_at
            if history_status == "servicio_finalizado" and resolution_at is None:
                resolution_at = history_created_at

        if arrival_at is None:
            arrival_at = to_aware_datetime(report.get("hora_llegada"))

        first_action_delta = minutes_between(created_at, first_action_at)
        assignment_delta = minutes_between(created_at, assignment_at)
        arrival_delta = minutes_between(assignment_at, arrival_at)
        resolution_delta = minutes_between(created_at, resolution_at)
        workshop_key = int(report["nearest_workshop_id"]) if report.get("nearest_workshop_id") is not None else 0
        if first_action_delta is not None:
            first_action_minutes.append(first_action_delta)
        if assignment_delta is not None:
            assignment_minutes.append(assignment_delta)
            if workshop_key:
                workshop_assignment_minutes[workshop_key].append(assignment_delta)
        if arrival_delta is not None:
            arrival_minutes.append(arrival_delta)
            if workshop_key:
                workshop_arrival_minutes[workshop_key].append(arrival_delta)
        if resolution_delta is not None:
            resolution_minutes.append(resolution_delta)
            if workshop_key:
                workshop_resolution_minutes[workshop_key].append(resolution_delta)
        if normalized in COMPLETED_STATUSES and workshop_key:
            workshop_completed_counts[workshop_key] += 1
        if assignment_delta is not None and arrival_delta is not None:
            sla_evaluable_services += 1
            if workshop_key:
                workshop_sla_evaluable_counts[workshop_key] += 1
            if assignment_delta <= SLA_ASIGNACION_MINUTOS and arrival_delta <= SLA_LLEGADA_MINUTOS:
                sla_compliant_services += 1
                if workshop_key:
                    workshop_sla_compliant_counts[workshop_key] += 1

    active_technicians = sum(1 for technician in technicians if is_active_technician(technician))
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
    incident_type_breakdown = [
        DashboardIncidentTypeBreakdownItemResponse(
            incident_type=incident_type,
            label=label,
            count=count,
        )
        for (incident_type, label), count in sorted(
            incident_type_counts.items(),
            key=lambda item: (-item[1], item[0][1]),
        )
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
    avg_arrival = average_value(arrival_minutes)
    avg_resolution = average_value(resolution_minutes)
    sla_compliance_percent = (
        (sla_compliant_services / sla_evaluable_services) * 100
        if sla_evaluable_services > 0
        else None
    )
    quotation_metrics = _load_tenant_quotation_metrics(role=role, current_user=current_user, sucursal_id=sucursal_id)
    analytics_summary = [
        DashboardMetricSummaryResponse(
            label="Tiempo promedio de asignación",
            value=format_minutes(avg_assignment),
            detail="Desde el registro de la emergencia hasta el estado de auxilio asignado.",
        ),
        DashboardMetricSummaryResponse(
            label="Tiempo promedio de llegada",
            value=format_minutes(avg_arrival),
            detail="Desde la asignación hasta el estado técnico en sitio o llegada registrada.",
        ),
        DashboardMetricSummaryResponse(
            label="Casos cancelados",
            value=str(cancelled_count),
            detail="Emergencias canceladas, rechazadas o no atendidas dentro del scope actual.",
        ),
        DashboardMetricSummaryResponse(
            label="Cumplimiento SLA",
            value=format_percent(sla_compliance_percent),
            detail=(
                f"{sla_compliant_services}/{sla_evaluable_services} servicios dentro de "
                f"{SLA_ASIGNACION_MINUTOS} min de asignación y {SLA_LLEGADA_MINUTOS} min de llegada."
                if sla_evaluable_services > 0
                else "No hay suficientes eventos reales de asignación y llegada para evaluar SLA."
            ),
        ),
    ]
    workshop_name_lookup = {
        int(workshop_item["id"]): str(workshop_item.get("workshop_name") or f"Taller #{int(workshop_item['id'])}")
        for workshop_item in active_workshops
        if workshop_item.get("id") is not None
    }
    efficiency_candidates: list[DashboardEfficiencyRankingItemResponse] = []
    for workshop_key, workshop_name in workshop_name_lookup.items():
        avg_workshop_assignment = average_value(workshop_assignment_minutes.get(workshop_key, []))
        avg_workshop_arrival = average_value(workshop_arrival_minutes.get(workshop_key, []))
        avg_workshop_resolution = average_value(workshop_resolution_minutes.get(workshop_key, []))
        if (
            avg_workshop_assignment is None
            and avg_workshop_arrival is None
            and avg_workshop_resolution is None
        ):
            continue
        evaluable = workshop_sla_evaluable_counts.get(workshop_key, 0)
        compliant = workshop_sla_compliant_counts.get(workshop_key, 0)
        efficiency_candidates.append(
            DashboardEfficiencyRankingItemResponse(
                workshop_id=workshop_key,
                workshop_name=workshop_name,
                completed_services=workshop_completed_counts.get(workshop_key, 0),
                avg_assignment_minutes=avg_workshop_assignment,
                avg_arrival_minutes=avg_workshop_arrival,
                avg_resolution_minutes=avg_workshop_resolution,
                sla_compliance_percent=((compliant / evaluable) * 100) if evaluable > 0 else None,
            )
        )
    efficiency_candidates.sort(
        key=lambda item: (
            float("inf") if item.avg_assignment_minutes is None else item.avg_assignment_minutes,
            float("inf") if item.avg_arrival_minutes is None else item.avg_arrival_minutes,
            float("inf") if item.avg_resolution_minutes is None else item.avg_resolution_minutes,
            -item.completed_services,
            item.workshop_name.lower(),
        )
    )
    efficiency_ranking = efficiency_candidates[:6]

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
    elif role == ROLE_CLIENTE:
        kpis = [
            DashboardKpiResponse(
                label="Mis solicitudes",
                value=str(len(reports)),
                detail="Solicitudes de emergencia registradas con tu cuenta.",
                trend="Cliente",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Activas",
                value=str(active_count),
                detail="Solicitudes que todavía están en atención o seguimiento.",
                trend="Live",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Finalizadas",
                value=str(completed_count),
                detail="Servicios ya concluidos para tu cuenta.",
                trend="Cierre",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Cotizaciones recibidas",
                value=str(quotation_metrics["quotation_offers_count"]),
                detail="Propuestas reales asociadas a tus solicitudes.",
                trend="Ofertas",
                tone="blue",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio entre tu solicitud y la primera acción registrada.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio hasta servicio finalizado en tus atenciones.",
            ),
            DashboardMetricSummaryResponse(
                label="Cotizaciones activas",
                value=str(quotation_metrics["quotation_requests_count"]),
                detail="Solicitudes de cotización abiertas o históricas registradas para tu cuenta.",
            ),
        ]
        tenant_ranking = []
        overview_scope = "client"
        overview_workshop_name = None
    elif role == ROLE_TECNICO:
        own_branch_technicians = [technician for technician in technicians if technician.get("sucursal_id") == sucursal_id] if sucursal_id is not None else technicians
        own_active = sum(1 for technician in own_branch_technicians if is_active_technician(technician))
        kpis = [
            DashboardKpiResponse(
                label="Servicios asignados",
                value=str(len(reports)),
                detail="Emergencias asignadas directamente a tu usuario técnico.",
                trend="Técnico",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Activos",
                value=str(active_count),
                detail="Servicios que sigues atendiendo en este momento.",
                trend="Live",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Finalizados",
                value=str(completed_count),
                detail="Servicios cerrados correctamente por tu flujo.",
                trend="Cierre",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Equipo activo",
                value=str(own_active),
                detail="Técnicos activos dentro de tu sucursal actual.",
                trend="Equipo",
                tone="blue",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio entre asignación y primera acción visible del servicio.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio hasta servicio finalizado en tus asignaciones.",
            ),
            DashboardMetricSummaryResponse(
                label="Pendientes",
                value=str(pending_count),
                detail="Servicios aún pendientes o recién recibidos dentro de tu vista técnica.",
            ),
        ]
        tenant_ranking = []
        overview_scope = "technician"
        overview_workshop_name = None
    elif role == ROLE_ADMIN_SUCURSAL:
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
            tenant_ranking.append(
                DashboardTenantRankingItemResponse(
                    workshop_id=workshop_key,
                    workshop_name=str(workshop_item.get("workshop_name") or f"Taller #{workshop_key}"),
                    total_requests=len(workshop_reports),
                    active_requests=sum(1 for current_status in workshop_statuses if current_status in ACTIVE_STATUSES),
                    completed_requests=sum(1 for current_status in workshop_statuses if current_status in COMPLETED_STATUSES),
                    cancelled_requests=sum(1 for current_status in workshop_statuses if current_status in CANCELLED_STATUSES),
                    technicians_available=sum(
                        1 for technician in technicians_by_workshop.get(workshop_key, []) if technician.get("status") == "disponible"
                    ),
                )
            )
        tenant_ranking.sort(
            key=lambda item: (-item.total_requests, -item.completed_requests, item.cancelled_requests, item.workshop_name.lower())
        )
        kpis = [
            DashboardKpiResponse(
                label="Emergencias sucursal",
                value=str(len(reports)),
                detail="Emergencias reales filtradas por tu sucursal.",
                trend="Sucursal",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Pendientes",
                value=str(pending_count),
                detail="Solicitudes pendientes o en revisión dentro de tu sucursal.",
                trend="Backlog",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Finalizadas",
                value=str(completed_count),
                detail="Servicios finalizados por la sucursal.",
                trend="Cierre",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Técnicos sucursal",
                value=str(active_technicians),
                detail="Técnicos activos y visibles para tu sucursal.",
                trend="Equipo",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Cotizaciones sucursal",
                value=str(quotation_metrics["quotation_requests_count"]),
                detail="Solicitudes de cotización vinculadas a talleres de la sucursal.",
                trend="Cotizar",
                tone="teal",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio operativo de la sucursal hasta la primera acción.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio de cierre para servicios de la sucursal.",
            ),
            DashboardMetricSummaryResponse(
                label="Comisiones/Pagos",
                value="No disponible",
                detail="No existe una tabla real consolidada de pagos/comisiones en esta versión.",
            ),
        ]
        overview_scope = "sucursal"
        overview_workshop_name = None
    elif role == ROLE_SUPERADMIN_TENANT:
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
            workshop_available = sum(
                1 for technician in technicians_by_workshop.get(workshop_key, []) if technician.get("status") == "disponible"
            )
            tenant_ranking.append(
                DashboardTenantRankingItemResponse(
                    workshop_id=workshop_key,
                    workshop_name=str(workshop_item.get("workshop_name") or f"Taller #{workshop_key}"),
                    total_requests=len(workshop_reports),
                    active_requests=sum(1 for current_status in workshop_statuses if current_status in ACTIVE_STATUSES),
                    completed_requests=sum(1 for current_status in workshop_statuses if current_status in COMPLETED_STATUSES),
                    cancelled_requests=sum(1 for current_status in workshop_statuses if current_status in CANCELLED_STATUSES),
                    technicians_available=workshop_available,
                )
            )
        tenant_ranking.sort(
            key=lambda item: (-item.total_requests, -item.completed_requests, item.cancelled_requests, item.workshop_name.lower())
        )
        kpis = [
            DashboardKpiResponse(
                label="Emergencias tenant",
                value=str(len(reports)),
                detail="Emergencias totales registradas dentro de tu tenant.",
                trend="Tenant",
                tone="gold",
            ),
            DashboardKpiResponse(
                label="Sucursales activas",
                value=str(len(active_workshops)),
                detail="Talleres o sucursales operando dentro del tenant.",
                trend="Red",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Finalizadas",
                value=str(completed_count),
                detail="Servicios finalizados dentro del tenant.",
                trend="Cierre",
                tone="teal",
            ),
            DashboardKpiResponse(
                label="Técnicos activos",
                value=str(active_technicians),
                detail="Técnicos activos registrados en el tenant.",
                trend="Equipo",
                tone="blue",
            ),
            DashboardKpiResponse(
                label="Cotizaciones generadas",
                value=str(quotation_metrics["quotation_requests_count"]),
                detail="Solicitudes de cotización registradas en la base real del tenant.",
                trend="Cotizar",
                tone="teal",
            ),
        ]
        summary = [
            DashboardMetricSummaryResponse(
                label="Tiempo primera gestión",
                value=format_minutes(avg_first_action),
                detail="Promedio entre registro y primera acción en todo el tenant.",
            ),
            DashboardMetricSummaryResponse(
                label="Tiempo de resolución",
                value=format_minutes(avg_resolution),
                detail="Promedio hasta servicio finalizado para el tenant.",
            ),
            DashboardMetricSummaryResponse(
                label="Comisiones/Pagos",
                value="No disponible",
                detail="No existe fuente real consolidada de pagos/comisiones por tenant todavía.",
            ),
        ]
        overview_scope = "tenant"
        overview_workshop_name = None
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
        analytics_summary=analytics_summary,
        incident_type_breakdown=incident_type_breakdown,
        efficiency_ranking=efficiency_ranking,
        recent_emergencies=recent_emergencies,
    )


@router.get(
    f"{settings.api_prefix}/dashboard/operational-overview",
    response_model=DashboardOperationalOverviewResponse,
)
def get_dashboard_operational_overview(
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> DashboardOperationalOverviewResponse:
    role = normalize_role(current_user.role) if current_user is not None else ""
    tenant_id = get_tenant_id_for_query(current_user)
    sucursal_id = (
        current_user.sucursal_id
        if current_user is not None and role in {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO}
        else None
    )
    if workshop_id is not None and role in {ROLE_TECNICO, ROLE_CLIENTE}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_WORKSHOP_SCOPE")
    if workshop_id is not None and current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL:
        workshop = get_workshop_by_id(workshop_id)
        if workshop and workshop.get("sucursal_id") != sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    return build_dashboard_operational_overview(workshop_id, tenant_id, sucursal_id, current_user)
