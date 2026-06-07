"""
Rutas de Sucursales — branches/sedes de un tenant.

Requiere token JWT con tenant_slug (usuario de tipo tenant, no admin global).
El middleware de main.py ya resolvió el engine correcto para este request.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.config import settings
from app.utils import (
    TokenPayload,
    require_admin_sucursal,
    require_superadmin_tenant,
    get_current_user,
    ROLE_ADMIN_SUCURSAL,
)

router = APIRouter(tags=["sucursales"])
DEFAULT_SUCURSAL_SPECIALTY = "Mecánica general"
ALLOWED_SUCURSAL_SPECIALTIES = (
    "Batería",
    "Motor",
    "Electricidad",
    "Llanta",
    "Choque",
    "Grúa",
    "Mecánica general",
)


# =============================================================================
# Modelos
# =============================================================================

class SucursalCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    nombre: str = Field(min_length=2, max_length=200)
    direccion: str = Field(default="", max_length=400)
    zona: str | None = Field(default=None, max_length=120)
    ciudad: str = Field(default="Santa Cruz", max_length=120)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    telefono: str | None = Field(default=None, max_length=50)
    responsable: str | None = Field(default=None, max_length=160)
    especialidades: list[str] = Field(default_factory=list)


class SucursalUpdate(SucursalCreate):
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    estado: str | None = Field(default=None, pattern="^(activo|inactivo)$")


class SucursalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    direccion: str
    zona: str | None = None
    ciudad: str
    latitud: float | None = None
    longitud: float | None = None
    telefono: str | None = None
    responsable: str | None = None
    workshop_id: int | None = None
    workshop_name: str | None = None
    workshop_specialty: str | None = None
    especialidades: list[str] = Field(default_factory=list)
    workshop_approval_status: str | None = None
    workshop_availability_status: str | None = None
    technicians_count: int = 0
    estado: str
    created_at: datetime
    updated_at: datetime


class SucursalMapaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    empresa: str
    tenant_id: int
    tenant_slug: str
    sucursal_id: int
    workshop_id: int
    workshop_name: str | None = None
    latitud: float
    longitud: float
    zona: str | None = None
    responsable: str | None = None
    telefono: str | None = None
    especialidades: list[str] = Field(default_factory=list)
    estado: str
    approval_status: str


def _tenant_display_name(current_user: TokenPayload) -> str:
    slug = (current_user.tenant_slug or "").replace("-", "_").strip("_")
    parts = [part for part in slug.split("_") if part]
    return " ".join(part.capitalize() for part in parts) or "Empresa"


def _derive_workshop_name(current_user: TokenPayload, sucursal_nombre: str) -> str:
    tenant_name = _tenant_display_name(current_user)
    clean_name = sucursal_nombre.strip()
    if not clean_name:
        return tenant_name
    if clean_name.casefold().startswith(tenant_name.casefold()):
        return clean_name
    return f"{tenant_name} {clean_name}"


def _normalize_sucursal_specialties(raw_specialties: list[str] | None) -> list[str]:
    if raw_specialties is None:
        return []

    allowed_lookup = {specialty.casefold(): specialty for specialty in ALLOWED_SUCURSAL_SPECIALTIES}
    normalized: list[str] = []
    seen: set[str] = set()

    for raw in raw_specialties:
        candidate = str(raw).strip()
        if not candidate:
            continue
        resolved = allowed_lookup.get(candidate.casefold())
        if resolved is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Especialidad no permitida: {candidate}",
            )
        token = resolved.casefold()
        if token in seen:
            continue
        seen.add(token)
        normalized.append(resolved)

    return normalized


def _replace_workshop_specialties(conn, workshop_id: int, specialties: list[str]) -> None:
    conn.execute(
        text("DELETE FROM workshop_specialties WHERE workshop_id = :workshop_id"),
        {"workshop_id": workshop_id},
    )
    for specialty in specialties:
        conn.execute(
            text(
                """
                INSERT INTO workshop_specialties (workshop_id, specialty)
                VALUES (:workshop_id, :specialty)
                ON CONFLICT (workshop_id, specialty) DO NOTHING
                """
            ),
            {"workshop_id": workshop_id, "specialty": specialty},
        )


def _workshop_status_for_sucursal_estado(estado: str | None) -> tuple[str, str]:
    if (estado or "activo").strip().lower() == "inactivo":
        return "rechazado", "fuera_de_servicio"
    return "activo", "disponible"


def _list_public_sucursales_mapa() -> list[dict[str, object]]:
    from app.saas_master import list_all_tenants
    from app.tenant_manager import get_tenant_engine

    sql = text(
        """
        SELECT
            s.id AS sucursal_id,
            s.nombre AS sucursal_nombre,
            s.zona AS sucursal_zona,
            s.telefono AS sucursal_telefono,
            s.responsable,
            s.estado AS sucursal_estado,
            s.latitud AS sucursal_latitud,
            s.longitud AS sucursal_longitud,
            wr.id AS workshop_id,
            wr.workshop_name,
            wr.specialty AS workshop_specialty,
            wr.approval_status,
            wr.availability_status,
            wr.latitude AS workshop_latitud,
            wr.longitude AS workshop_longitud,
            COALESCE(
                ws.specialties,
                CASE
                    WHEN wr.specialty IS NOT NULL THEN ARRAY[wr.specialty]::VARCHAR[]
                    ELSE ARRAY[]::VARCHAR[]
                END
            ) AS especialidades
        FROM sucursales s
        JOIN LATERAL (
            SELECT
                id,
                workshop_name,
                specialty,
                approval_status,
                availability_status,
                latitude,
                longitude
            FROM workshop_registrations
            WHERE sucursal_id = s.id
              AND approval_status = 'activo'
              AND COALESCE(availability_status, 'disponible') <> 'fuera_de_servicio'
            ORDER BY created_at ASC, id ASC
            LIMIT 1
        ) wr ON TRUE
        LEFT JOIN LATERAL (
            SELECT ARRAY_AGG(specialty ORDER BY created_at ASC, id ASC)::VARCHAR[] AS specialties
            FROM workshop_specialties
            WHERE workshop_id = wr.id
        ) ws ON TRUE
        WHERE s.estado = 'activo'
        ORDER BY s.nombre ASC, wr.id ASC
        """
    )

    rows: list[dict[str, object]] = []
    for tenant in list_all_tenants():
        if tenant.get("estado") != "activo":
            continue

        try:
            engine = get_tenant_engine(tenant)
            with engine.connect() as conn:
                tenant_rows = [dict(item) for item in conn.execute(sql).mappings().all()]
        except Exception:
            continue

        for row in tenant_rows:
            latitude = row.get("workshop_latitud")
            if latitude is None:
                latitude = row.get("sucursal_latitud")
            longitude = row.get("workshop_longitud")
            if longitude is None:
                longitude = row.get("sucursal_longitud")
            if latitude is None or longitude is None:
                continue

            especialidades = [str(value).strip() for value in (row.get("especialidades") or []) if str(value).strip()]
            specialty = str(row.get("workshop_specialty") or "").strip()
            if specialty and specialty not in especialidades:
                especialidades.insert(0, specialty)
            if not especialidades:
                continue

            rows.append(
                {
                    "id": int(row["workshop_id"]),
                    "nombre": str(row.get("sucursal_nombre") or row.get("workshop_name") or "Sucursal"),
                    "empresa": str(tenant.get("nombre") or "Empresa"),
                    "tenant_id": int(tenant["id"]),
                    "tenant_slug": str(tenant.get("slug") or ""),
                    "sucursal_id": int(row["sucursal_id"]),
                    "workshop_id": int(row["workshop_id"]),
                    "workshop_name": row.get("workshop_name"),
                    "latitud": float(latitude),
                    "longitud": float(longitude),
                    "zona": row.get("sucursal_zona"),
                    "responsable": row.get("responsable"),
                    "telefono": row.get("sucursal_telefono"),
                    "especialidades": especialidades,
                    "estado": str(row.get("sucursal_estado") or "activo"),
                    "approval_status": str(row.get("approval_status") or "activo"),
                }
            )

    rows.sort(key=lambda item: (str(item["empresa"]).casefold(), str(item["nombre"]).casefold(), int(item["id"])))
    return rows


def get_or_create_workshop_for_sucursal(
    conn,
    current_user: TokenPayload,
    sucursal_id: int,
    payload: SucursalCreate | SucursalUpdate,
) -> dict[str, object]:
    workshops = conn.execute(
        text(
            """
            SELECT id, email, specialty, password_hash, timezone, utc_offset_minutes
            FROM workshop_registrations
            WHERE sucursal_id = :sucursal_id
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"sucursal_id": sucursal_id},
    ).mappings().all()
    workshop = workshops[0] if workshops else None
    duplicate_ids = [int(row["id"]) for row in workshops[1:]]
    if duplicate_ids:
        conn.execute(
            text(
                """
                UPDATE workshop_registrations
                SET sucursal_id = NULL,
                    approval_status = 'rechazado',
                    availability_status = 'fuera_de_servicio'
                WHERE id = ANY(:duplicate_ids)
                """
            ),
            {"duplicate_ids": duplicate_ids},
        )
    existing_specialties = (
        [
            str(value)
            for value in conn.execute(
                text(
                    """
                    SELECT specialty
                    FROM workshop_specialties
                    WHERE workshop_id = :workshop_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"workshop_id": workshop["id"]},
            ).scalars().all()
        ]
        if workshop
        else []
    )
    normalized_specialties = _normalize_sucursal_specialties(getattr(payload, "especialidades", None))

    workshop_name = _derive_workshop_name(current_user, str(payload.nombre or "Sucursal"))
    zone = payload.zona or "Centro"
    specialties = normalized_specialties or existing_specialties or (
        [str(workshop["specialty"])] if workshop and workshop.get("specialty") else [DEFAULT_SUCURSAL_SPECIALTY]
    )
    specialty = specialties[0]
    approval_status, availability_status = _workshop_status_for_sucursal_estado(getattr(payload, "estado", "activo"))
    contact_name = payload.responsable or payload.nombre or "Responsable de sucursal"
    phone = payload.telefono or "0000000"
    generated_email = f"sucursal.{sucursal_id}@{(current_user.tenant_slug or 'empresa').replace('_', '-')}.local"
    latitude = payload.latitud
    longitude = payload.longitud

    if workshop:
        conn.execute(
            text(
                """
                UPDATE workshop_registrations
                SET workshop_name = :workshop_name,
                    contact_name = :contact_name,
                    phone = :phone,
                    email = :email,
                    zone = :zone,
                    specialty = :specialty,
                    approval_status = :approval_status,
                    availability_status = :availability_status,
                    latitude = :latitude,
                    longitude = :longitude,
                    timezone = :timezone,
                    utc_offset_minutes = :utc_offset_minutes,
                    sucursal_id = :sucursal_id
                WHERE id = :id
                """
            ),
            {
                "id": workshop["id"],
                "workshop_name": workshop_name,
                "contact_name": contact_name,
                "phone": phone,
                "email": workshop["email"] or generated_email,
                "zone": zone,
                "specialty": specialty,
                "approval_status": approval_status,
                "availability_status": availability_status,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": workshop["timezone"],
                "utc_offset_minutes": workshop["utc_offset_minutes"],
                "sucursal_id": sucursal_id,
            },
        )
        _replace_workshop_specialties(conn, int(workshop["id"]), specialties)
        return {
            **dict(workshop),
            "id": int(workshop["id"]),
            "specialty": specialty,
            "approval_status": approval_status,
            "availability_status": availability_status,
            "sucursal_id": sucursal_id,
        }

    created = conn.execute(
        text(
            """
            INSERT INTO workshop_registrations (
                workshop_name,
                contact_name,
                phone,
                email,
                zone,
                specialty,
                approval_status,
                availability_status,
                password_hash,
                latitude,
                longitude,
                timezone,
                utc_offset_minutes,
                sucursal_id
            ) VALUES (
                :workshop_name,
                :contact_name,
                :phone,
                :email,
                :zone,
                :specialty,
                :approval_status,
                :availability_status,
                NULL,
                :latitude,
                :longitude,
                NULL,
                NULL,
                :sucursal_id
            )
            RETURNING id, email, specialty, timezone, utc_offset_minutes, approval_status, availability_status, sucursal_id
            """
        ),
        {
            "workshop_name": workshop_name,
            "contact_name": contact_name,
            "phone": phone,
            "email": generated_email,
            "zone": zone,
            "specialty": specialty,
            "approval_status": approval_status,
            "availability_status": availability_status,
            "latitude": latitude,
            "longitude": longitude,
            "sucursal_id": sucursal_id,
        },
    ).mappings().first()
    _replace_workshop_specialties(conn, int(created["id"]), specialties)
    return dict(created)


def _sync_workshop_for_sucursal(
    conn,
    current_user: TokenPayload,
    payload: SucursalCreate | SucursalUpdate,
    sucursal_id: int,
) -> dict[str, object]:
    return get_or_create_workshop_for_sucursal(conn, current_user, sucursal_id, payload)


def _select_sucursal_by_id(conn, current_user: TokenPayload, sucursal_id: int) -> dict[str, object] | None:
    where_clause = "WHERE s.id = :id"
    params: dict[str, object] = {"id": sucursal_id}
    if current_user.role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id is not None:
        where_clause += " AND s.id = :scope_id"
        params["scope_id"] = current_user.sucursal_id

    row = conn.execute(
        text(
            f"""
            SELECT
                s.*,
                wr.id AS workshop_id,
                wr.workshop_name,
                wr.specialty AS workshop_specialty,
                COALESCE(
                    ws.specialties,
                    CASE
                        WHEN wr.specialty IS NOT NULL THEN ARRAY[wr.specialty]::VARCHAR[]
                        ELSE ARRAY[]::VARCHAR[]
                    END
                ) AS especialidades,
                wr.approval_status AS workshop_approval_status,
                wr.availability_status AS workshop_availability_status,
                COALESCE(tech.technicians_count, 0) AS technicians_count
            FROM sucursales s
            LEFT JOIN LATERAL (
                SELECT id, workshop_name, specialty, approval_status, availability_status
                FROM workshop_registrations
                WHERE sucursal_id = s.id
                ORDER BY created_at ASC, id ASC
                LIMIT 1
            ) wr ON TRUE
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(specialty ORDER BY created_at ASC, id ASC)::VARCHAR[] AS specialties
                FROM workshop_specialties
                WHERE workshop_id = wr.id
            ) ws ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::INT AS technicians_count
                FROM technicians
                WHERE sucursal_id = s.id
                  AND status IN ('disponible', 'ocupado')
            ) tech ON TRUE
            {where_clause}
            """
        ),
        params,
    ).mappings().first()
    return dict(row) if row else None


def _list_sucursales(conn, current_user: TokenPayload) -> list[dict[str, object]]:
    where_clause = ""
    params: dict[str, object] = {}
    if current_user.role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id is not None:
        where_clause = "WHERE s.id = :id"
        params["id"] = current_user.sucursal_id

    rows = conn.execute(
        text(
            f"""
            SELECT
                s.*,
                wr.id AS workshop_id,
                wr.workshop_name,
                wr.specialty AS workshop_specialty,
                COALESCE(
                    ws.specialties,
                    CASE
                        WHEN wr.specialty IS NOT NULL THEN ARRAY[wr.specialty]::VARCHAR[]
                        ELSE ARRAY[]::VARCHAR[]
                    END
                ) AS especialidades,
                wr.approval_status AS workshop_approval_status,
                wr.availability_status AS workshop_availability_status,
                COALESCE(tech.technicians_count, 0) AS technicians_count
            FROM sucursales s
            LEFT JOIN LATERAL (
                SELECT id, workshop_name, specialty, approval_status, availability_status
                FROM workshop_registrations
                WHERE sucursal_id = s.id
                ORDER BY created_at ASC, id ASC
                LIMIT 1
            ) wr ON TRUE
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(specialty ORDER BY created_at ASC, id ASC)::VARCHAR[] AS specialties
                FROM workshop_specialties
                WHERE workshop_id = wr.id
            ) ws ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::INT AS technicians_count
                FROM technicians
                WHERE sucursal_id = s.id
                  AND status IN ('disponible', 'ocupado')
            ) tech ON TRUE
            {where_clause}
            ORDER BY s.nombre ASC
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def _get_engine(current_user: TokenPayload):
    """
    Devuelve el engine del tenant activo para este request.
    Si el usuario no tiene tenant_slug en su JWT, rechaza la operación.
    Los usuarios globales (admin) deben usar /api/saas/* para gestión global.
    """
    if not current_user.tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es exclusivo para usuarios de empresa (tenant). Usa /api/saas/tenants para la vista global.",
        )
    from app.tenant_context import get_engine
    return get_engine()


def _ensure_sucursal_scope(current_user: TokenPayload, sucursal_id: int) -> None:
    if current_user.role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id != sucursal_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCESO_DENEGADO_SUCURSAL",
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    f"{settings.api_prefix}/sucursales/mapa",
    response_model=list[SucursalMapaOut],
)
def listar_sucursales_mapa() -> list[SucursalMapaOut]:
    """Lista pública de sucursales SaaS activas para el mapa móvil."""
    return [SucursalMapaOut.model_validate(row) for row in _list_public_sucursales_mapa()]


@router.get(
    f"{settings.api_prefix}/sucursales",
    response_model=list[SucursalOut],
)
def listar_sucursales(
    current_user: TokenPayload = Depends(require_admin_sucursal),
) -> list[SucursalOut]:
    """Lista todas las sucursales del tenant activo."""
    engine = _get_engine(current_user)
    with engine.connect() as conn:
        rows = _list_sucursales(conn, current_user)
    return [SucursalOut.model_validate(dict(r)) for r in rows]


@router.post(
    f"{settings.api_prefix}/sucursales",
    response_model=SucursalOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_sucursal(
    payload: SucursalCreate,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> SucursalOut:
    """Crea una sucursal. Solo SUPERADMIN_TENANT o admin puede crear sucursales."""
    specialties = _normalize_sucursal_specialties(payload.especialidades)
    if not specialties:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona al menos una especialidad.",
        )
    payload = payload.model_copy(update={"especialidades": specialties})
    engine = _get_engine(current_user)
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO sucursales
                    (nombre, direccion, zona, ciudad, latitud, longitud, telefono, responsable, estado)
                VALUES
                    (:nombre, :direccion, :zona, :ciudad, :latitud, :longitud, :telefono, :responsable, 'activo')
                RETURNING *
            """),
            payload.model_dump(),
        ).mappings().first()
        _sync_workshop_for_sucursal(conn, current_user, payload, int(row["id"]))
        refreshed = _select_sucursal_by_id(conn, current_user, int(row["id"]))
    return SucursalOut.model_validate(dict(refreshed))


@router.get(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    response_model=SucursalOut,
)
def obtener_sucursal(
    sucursal_id: int,
    current_user: TokenPayload = Depends(require_admin_sucursal),
) -> SucursalOut:
    _ensure_sucursal_scope(current_user, sucursal_id)
    engine = _get_engine(current_user)
    with engine.connect() as conn:
        row = _select_sucursal_by_id(conn, current_user, sucursal_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return SucursalOut.model_validate(row)


@router.put(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    response_model=SucursalOut,
)
def actualizar_sucursal(
    sucursal_id: int,
    payload: SucursalUpdate,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> SucursalOut:
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    requested_specialties = _normalize_sucursal_specialties(payload.especialidades)
    data.pop("especialidades", None)
    engine = _get_engine(current_user)
    with engine.begin() as conn:
        row = None
        if data:
            fields = ", ".join(f"{k} = :{k}" for k in data)
            data["id"] = sucursal_id
            row = conn.execute(
                text(f"UPDATE sucursales SET {fields}, updated_at = NOW() WHERE id = :id RETURNING *"),
                data,
            ).mappings().first()
        else:
            row = conn.execute(
                text("SELECT * FROM sucursales WHERE id = :id"),
                {"id": sucursal_id},
            ).mappings().first()
        if row:
            current_specialties = []
            workshop_row = conn.execute(
                text(
                    """
                    SELECT wr.id, wr.specialty
                    FROM workshop_registrations wr
                    WHERE wr.sucursal_id = :sucursal_id
                    ORDER BY wr.created_at ASC, wr.id ASC
                    LIMIT 1
                    """
                ),
                {"sucursal_id": sucursal_id},
            ).mappings().first()
            if workshop_row:
                current_specialties = [
                    str(value)
                    for value in conn.execute(
                        text(
                            """
                            SELECT specialty
                            FROM workshop_specialties
                            WHERE workshop_id = :workshop_id
                            ORDER BY created_at ASC, id ASC
                            """
                        ),
                        {"workshop_id": workshop_row["id"]},
                    ).scalars().all()
                ]
                if not current_specialties and workshop_row.get("specialty"):
                    current_specialties = [str(workshop_row["specialty"])]
            effective_specialties = requested_specialties or current_specialties
            if not effective_specialties:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Selecciona al menos una especialidad.",
                )
            merged_payload = SucursalCreate(
                nombre=str(row["nombre"]),
                direccion=str(row["direccion"] or ""),
                zona=row["zona"],
                ciudad=str(row["ciudad"] or "Santa Cruz"),
                latitud=row["latitud"],
                longitud=row["longitud"],
                telefono=row["telefono"],
                responsable=row["responsable"],
                especialidades=effective_specialties,
            )
            _sync_workshop_for_sucursal(conn, current_user, merged_payload, sucursal_id)
            row = _select_sucursal_by_id(conn, current_user, sucursal_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return SucursalOut.model_validate(dict(row) if not isinstance(row, dict) else row)


@router.delete(
    f"{settings.api_prefix}/sucursales/{{sucursal_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_sucursal(
    sucursal_id: int,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> None:
    engine = _get_engine(current_user)
    with engine.begin() as conn:
        sucursal = conn.execute(
            text("SELECT * FROM sucursales WHERE id = :id"),
            {"id": sucursal_id},
        ).mappings().first()
        if not sucursal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
        conn.execute(
            text(
                """
                UPDATE sucursales
                SET estado = 'inactivo',
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": sucursal_id},
        )
        conn.execute(
            text(
                """
                UPDATE workshop_registrations
                SET approval_status = 'rechazado',
                    availability_status = 'fuera_de_servicio',
                    sucursal_id = :id
                WHERE sucursal_id = :id
                """
            ),
            {"id": sucursal_id},
        )
