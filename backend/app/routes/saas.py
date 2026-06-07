"""
Rutas SUPERADMIN_GLOBAL — gestión de tenants, planes y métricas globales.

Acceso restringido a: admin (legacy) y SUPERADMIN_GLOBAL.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import text

from app.config import settings
from app.utils import TokenPayload, require_superadmin_global

router = APIRouter(tags=["saas"])


# =============================================================================
# Modelos
# =============================================================================

class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str
    razon_social: str | None = None
    nit: str | None = None
    correo: str
    telefono: str | None = None
    ciudad: str
    estado: str
    database_name: str
    plan_id: int | None = None
    plan_nombre: str | None = None


class TenantUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    razon_social: str | None = Field(default=None, max_length=300)
    nit: str | None = Field(default=None, max_length=50)
    telefono: str | None = Field(default=None, max_length=50)
    ciudad: str | None = Field(default=None, max_length=120)
    plan_id: int | None = Field(default=None, ge=1)


class PlanCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    nombre: str = Field(min_length=2, max_length=200)
    descripcion: str | None = None
    precio_mensual: float = Field(ge=0)
    limite_sucursales: int = Field(ge=1, default=1)
    limite_tecnicos: int = Field(ge=1, default=10)
    limite_administradores: int = Field(ge=1, default=2)


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    precio_mensual: float
    limite_sucursales: int
    limite_tecnicos: int
    limite_administradores: int
    estado: str


# =============================================================================
# Endpoints: tenants
# =============================================================================

@router.get(
    f"{settings.api_prefix}/saas/tenants",
    response_model=list[TenantOut],
)
def listar_tenants(
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> list[TenantOut]:
    """Lista todos los tenants registrados en saas_master."""
    from app.saas_master import list_all_tenants
    rows = list_all_tenants()
    return [TenantOut.model_validate(r) for r in rows]


@router.get(
    f"{settings.api_prefix}/saas/tenants/{{tenant_id}}",
    response_model=TenantOut,
)
def obtener_tenant(
    tenant_id: int,
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> TenantOut:
    from app.saas_master import get_tenant_by_id
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    return TenantOut.model_validate(tenant)


@router.put(
    f"{settings.api_prefix}/saas/tenants/{{tenant_id}}",
    response_model=TenantOut,
)
def actualizar_tenant(
    tenant_id: int,
    payload: TenantUpdateRequest,
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> TenantOut:
    from app.saas_master import get_tenant_by_id, update_saas_tenant
    if not get_tenant_by_id(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = update_saas_tenant(tenant_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    return TenantOut.model_validate(updated)


@router.put(
    f"{settings.api_prefix}/saas/tenants/{{tenant_id}}/estado",
)
def cambiar_estado_tenant(
    tenant_id: int,
    estado: str,
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> dict:
    if estado not in ("activo", "suspendido", "inactivo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado inválido. Use: activo, suspendido, inactivo",
        )
    from app.saas_master import get_tenant_by_id, toggle_tenant_estado
    if not get_tenant_by_id(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    updated = toggle_tenant_estado(tenant_id, estado)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")
    return {"id": tenant_id, "estado": estado, "message": f"Tenant actualizado a: {estado}"}


# =============================================================================
# Endpoints: planes
# =============================================================================

@router.get(
    f"{settings.api_prefix}/saas/planes",
    response_model=list[PlanOut],
)
def listar_planes(
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> list[PlanOut]:
    from app.saas_master import list_planes
    return [PlanOut.model_validate(p) for p in list_planes(solo_activos=False)]


@router.post(
    f"{settings.api_prefix}/saas/planes",
    response_model=PlanOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_plan(
    payload: PlanCreate,
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> PlanOut:
    from app.saas_master import create_plan
    plan = create_plan(payload.model_dump())
    return PlanOut.model_validate(plan)


# =============================================================================
# Endpoints: métricas globales
# =============================================================================

@router.get(f"{settings.api_prefix}/saas/metricas")
def metricas_globales(
    current_user: TokenPayload = Depends(require_superadmin_global),
) -> dict:
    """KPIs globales del SaaS (conteos reales desde saas_master)."""
    from app.saas_master import get_master_engine

    engine = get_master_engine()
    with engine.connect() as conn:
        tenant_metrics = conn.execute(
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
        subscription_metrics = conn.execute(
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
        total_planes = conn.execute(text("SELECT COUNT(*) FROM planes WHERE estado = 'activo'")).scalar() or 0
        tenants_por_plan = [
            {
                "plan": str(row["plan_nombre"]),
                "total": int(row["total"]),
            }
            for row in conn.execute(
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
        ]

    return {
        "total_tenants": int(tenant_metrics["total_tenants"]),
        "tenants_activos": int(tenant_metrics["tenants_activos"]),
        "tenants_inactivos": int(tenant_metrics["tenants_inactivos"]),
        "tenants_suspendidos": int(tenant_metrics["tenants_suspendidos"]),
        "suscripciones_activas": int(subscription_metrics["suscripciones_activas"]),
        "ingresos_plataforma": float(subscription_metrics["ingresos_plataforma"] or 0),
        "total_planes_activos": int(total_planes),
        "tenants_por_plan": tenants_por_plan,
        "altas_recientes_7d": int(tenant_metrics["altas_recientes_7d"]),
    }
