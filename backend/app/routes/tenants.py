from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import settings
from app.saas_master import (
    generate_unique_slug,
    get_tenant_by_id,
    list_all_tenants,
    toggle_tenant_estado,
    update_saas_tenant,
)
from app.tenant_manager import create_tenant_database, get_tenant_engine, init_tenant_schema
from app.utils import TokenPayload, require_superadmin_global

router = APIRouter(tags=["tenants"])


class TenantCreateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    descripcion: str | None = Field(default=None, max_length=1000)
    estado: str = Field(default="activo", pattern="^(activo|inactivo)$")


class TenantUpdateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    descripcion: str | None = Field(default=None, max_length=1000)
    estado: str = Field(pattern="^(activo|inactivo)$")


class TenantResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    estado: str
    created_at: object
    updated_at: object


class TenantKpiResponse(BaseModel):
    tenant_id: int
    nombre: str
    estado: str
    total_emergencias: int
    pendientes: int
    en_atencion: int
    finalizadas: int
    canceladas: int
    ingresos_total: float
    total_talleres: int
    talleres_activos: int
    total_tecnicos: int
    tecnicos_disponibles: int
    cotizaciones_aceptadas: int
    cotizaciones_rechazadas: int


@dataclass
class _QuotationStatusColumns:
    accepted_expr: str
    rejected_expr: str


def _tenant_to_compat_response(row: dict[str, object]) -> TenantResponse:
    return TenantResponse(
        id=int(row["id"]),
        nombre=str(row["nombre"]),
        descripcion=str(row["razon_social"]) if row.get("razon_social") else None,
        estado=str(row["estado"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_tenant_or_404(tenant_id: int) -> dict[str, object]:
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NO_ENCONTRADO")
    return tenant


def _get_tenant_kpis_from_tenant_db(tenant: dict[str, object]) -> dict[str, object]:
    engine = get_tenant_engine(tenant)
    with engine.connect() as conn:
        emergency_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_emergencias,
                        COUNT(*) FILTER (WHERE emergency_status IN ('pendiente', 'solicitud_recibida', 'en_revision')) AS pendientes,
                        COUNT(*) FILTER (WHERE emergency_status IN ('activo', 'auxilio_asignado', 'auxilio_en_camino', 'servicio_en_proceso', 'tecnico_en_sitio')) AS en_atencion,
                        COUNT(*) FILTER (WHERE emergency_status = 'servicio_finalizado') AS finalizadas,
                        COUNT(*) FILTER (WHERE emergency_status IN ('rechazado', 'solicitud_cancelada', 'cancelado')) AS canceladas,
                        COALESCE(SUM(price) FILTER (WHERE emergency_status = 'servicio_finalizado'), 0) AS ingresos_total
                    FROM emergency_reports
                    """
                )
            ).mappings().one()
        )
        workshop_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_talleres,
                        COUNT(*) FILTER (WHERE approval_status = 'activo') AS talleres_activos
                    FROM workshop_registrations
                    """
                )
            ).mappings().one()
        )
        technician_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_tecnicos,
                        COUNT(*) FILTER (WHERE status = 'disponible') AS tecnicos_disponibles
                    FROM technicians
                    """
                )
            ).mappings().one()
        )
        quotation_columns = {
            str(row["column_name"])
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'quotation_offers'
                    """
                )
            ).mappings().all()
        }

        if "status" in quotation_columns:
            quotation_exprs = _QuotationStatusColumns(
                accepted_expr="status = 'aceptada'",
                rejected_expr="status = 'rechazada'",
            )
        elif "offer_status" in quotation_columns:
            quotation_exprs = _QuotationStatusColumns(
                accepted_expr="offer_status IN ('aceptada', 'seleccionada', 'selected')",
                rejected_expr="offer_status IN ('rechazada', 'not_selected', 'no_seleccionada')",
            )
        else:
            quotation_exprs = _QuotationStatusColumns(
                accepted_expr="FALSE",
                rejected_expr="FALSE",
            )

        quotation_counts = dict(
            conn.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) FILTER (WHERE {quotation_exprs.accepted_expr}) AS cotizaciones_aceptadas,
                        COUNT(*) FILTER (WHERE {quotation_exprs.rejected_expr}) AS cotizaciones_rechazadas
                    FROM quotation_offers
                    """
                )
            ).mappings().one()
        )

    return {
        **emergency_counts,
        **workshop_counts,
        **technician_counts,
        **quotation_counts,
    }


def _list_workshops_for_tenant(tenant: dict[str, object]) -> list[dict[str, object]]:
    engine = get_tenant_engine(tenant)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    workshop_name,
                    email,
                    zone,
                    specialty,
                    approval_status
                FROM workshop_registrations
                ORDER BY workshop_name ASC, id ASC
                """
            )
        ).mappings().all()
    tenant_id = int(tenant["id"])
    return [
        {
            "id": int(row["id"]),
            "workshop_name": row.get("workshop_name"),
            "email": row.get("email"),
            "zone": row.get("zone"),
            "specialty": row.get("specialty"),
            "approval_status": row.get("approval_status"),
            "tenant_id": tenant_id,
        }
        for row in rows
    ]


@router.get(
    f"{settings.api_prefix}/tenants",
    response_model=list[TenantResponse],
)
def listar_tenants(
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> list[TenantResponse]:
    rows = list_all_tenants()
    return [_tenant_to_compat_response(row) for row in rows]


@router.post(
    f"{settings.api_prefix}/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_tenant(
    payload: TenantCreateRequest,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> TenantResponse:
    from app.saas_master import create_saas_tenant

    slug = generate_unique_slug(payload.nombre)
    db_name = f"tenant_{slug}"
    synthetic_email = f"{slug}@tenant.local"

    create_tenant_database(db_name)
    tenant = create_saas_tenant(
        {
            "nombre": payload.nombre,
            "slug": slug,
            "razon_social": payload.descripcion,
            "nit": None,
            "correo": synthetic_email,
            "telefono": None,
            "direccion_principal": None,
            "zona": None,
            "ciudad": "Santa Cruz",
            "latitud": None,
            "longitud": None,
            "database_name": db_name,
            "database_host": settings.postgres_host,
            "database_port": settings.postgres_port,
            "database_user": settings.postgres_user,
            "database_password": settings.postgres_password,
            "plan_id": None,
        }
    )
    init_tenant_schema(tenant)
    if payload.estado == "inactivo":
        tenant = toggle_tenant_estado(int(tenant["id"]), "inactivo") or tenant
    return _tenant_to_compat_response(tenant)


@router.get(
    f"{settings.api_prefix}/tenants/{{tenant_id}}",
    response_model=TenantResponse,
)
def obtener_tenant(
    tenant_id: int,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> TenantResponse:
    return _tenant_to_compat_response(_get_tenant_or_404(tenant_id))


@router.get(
    f"{settings.api_prefix}/tenants/{{tenant_id}}/kpis",
    response_model=TenantKpiResponse,
)
def obtener_kpis_tenant(
    tenant_id: int,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> TenantKpiResponse:
    tenant = _get_tenant_or_404(tenant_id)
    if tenant.get("estado") == "inactivo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_INACTIVO")
    kpis = _get_tenant_kpis_from_tenant_db(tenant)
    return TenantKpiResponse(
        tenant_id=tenant_id,
        nombre=str(tenant["nombre"]),
        estado=str(tenant["estado"]),
        total_emergencias=int(kpis.get("total_emergencias") or 0),
        pendientes=int(kpis.get("pendientes") or 0),
        en_atencion=int(kpis.get("en_atencion") or 0),
        finalizadas=int(kpis.get("finalizadas") or 0),
        canceladas=int(kpis.get("canceladas") or 0),
        ingresos_total=float(kpis.get("ingresos_total") or 0),
        total_talleres=int(kpis.get("total_talleres") or 0),
        talleres_activos=int(kpis.get("talleres_activos") or 0),
        total_tecnicos=int(kpis.get("total_tecnicos") or 0),
        tecnicos_disponibles=int(kpis.get("tecnicos_disponibles") or 0),
        cotizaciones_aceptadas=int(kpis.get("cotizaciones_aceptadas") or 0),
        cotizaciones_rechazadas=int(kpis.get("cotizaciones_rechazadas") or 0),
    )


@router.get(
    f"{settings.api_prefix}/tenants/{{tenant_id}}/workshops",
)
def obtener_talleres_del_tenant(
    tenant_id: int,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> list[dict[str, object]]:
    tenant = _get_tenant_or_404(tenant_id)
    return _list_workshops_for_tenant(tenant)


@router.put(
    f"{settings.api_prefix}/tenants/{{tenant_id}}",
    response_model=TenantResponse,
)
def actualizar_tenant(
    tenant_id: int,
    payload: TenantUpdateRequest,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> TenantResponse:
    _get_tenant_or_404(tenant_id)
    updated = update_saas_tenant(
        tenant_id,
        {
            "nombre": payload.nombre,
            "razon_social": payload.descripcion,
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NO_ENCONTRADO")
    if payload.estado != str(updated.get("estado")):
        updated = toggle_tenant_estado(tenant_id, payload.estado) or updated
    return _tenant_to_compat_response(updated)


@router.patch(
    f"{settings.api_prefix}/tenants/{{tenant_id}}/estado",
    response_model=TenantResponse,
)
def cambiar_estado_tenant(
    tenant_id: int,
    estado: str = Query(pattern="^(activo|inactivo)$"),
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> TenantResponse:
    _get_tenant_or_404(tenant_id)
    updated = toggle_tenant_estado(tenant_id, estado)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NO_ENCONTRADO")
    return _tenant_to_compat_response(updated)


@router.delete(
    f"{settings.api_prefix}/tenants/{{tenant_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_tenant(
    tenant_id: int,
    _admin: TokenPayload = Depends(require_superadmin_global),
) -> None:
    _get_tenant_or_404(tenant_id)
    updated = toggle_tenant_estado(tenant_id, "inactivo")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NO_ENCONTRADO")
