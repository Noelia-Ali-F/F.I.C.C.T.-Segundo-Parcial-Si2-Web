import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import text

from app.config import settings
from app.db import (
    create_workshop_registration,
    delete_workshop_registration,
    get_workshop_by_email,
    get_workshop_by_id,
    list_workshop_registrations,
    update_workshop_approval_status_with_password,
    update_workshop_password,
    update_workshop_registration,
)
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    TokenPayload,
    calculate_distance_meters,
    get_current_user_optional,
    get_tenant_id_for_query,
    hash_password,
    normalize_optional_text,
    verify_password,
)
from app.db import list_workshops_by_tenant

# =========================================================
# ARCHIVO DE RUTAS DE TALLERES
# Aqui esta todo lo relacionado con los talleres del sistema.
# Este archivo contiene:
# - modelos para registrar y editar talleres
# - logica para aprobacion de talleres
# - logica para contrasena temporal y recuperacion de contrasena
# - controladores HTTP del modulo talleres
# Palabras clave para buscar despues:
# TALLERES, WORKSHOPS, APROBACION, PASSWORD, REGISTRO TALLER
# =========================================================
router = APIRouter(tags=["workshops"])
logger = logging.getLogger(__name__)


class WorkshopPasswordChangeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "WorkshopPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class WorkshopForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    new_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("new_password", "newPassword", "password"),
    )
    confirm_password: str = Field(
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "WorkshopForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class WorkshopRegistrationCreate(BaseModel):
    workshop_name: str = Field(min_length=3, max_length=160)
    contact_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    zone: str = Field(min_length=2, max_length=120)
    specialty: str = Field(min_length=2, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=2, max_length=120)
    utc_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    tenant_id: int | None = Field(default=None, ge=1)
    sucursal_id: int | None = Field(default=None, ge=1)


class WorkshopRegistrationUpdate(WorkshopRegistrationCreate):
    password: str | None = Field(default=None, min_length=6, max_length=255)


class WorkshopRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_name: str
    contact_name: str
    phone: str
    email: EmailStr
    zone: str
    specialty: str
    approval_status: str
    availability_status: str
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    utc_offset_minutes: int | None = None
    tenant_id: int | None = None
    tenant_slug: str | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    specialties: list[str] = Field(default_factory=list)
    created_at: datetime


class WorkshopApprovalStatusUpdate(BaseModel):
    approval_status: str = Field(pattern="^(pendiente|activo|rechazado)$")


"""
Aqui esta la logica de registro de taller que crea
una nueva solicitud de taller con estado pendiente.
"""
def register_workshop_service(
    payload: WorkshopRegistrationCreate,
    requesting_user: TokenPayload | None = None,
) -> WorkshopRegistrationResponse:
    # tenant_id: usa el del payload si lo envió el admin, sino el del usuario autenticado, sino 1
    tenant_id = payload.tenant_id
    if tenant_id is None and requesting_user is not None:
        tenant_id = requesting_user.tenant_id
    if tenant_id is None:
        tenant_id = 1
    sucursal_id = payload.sucursal_id
    if requesting_user is not None and requesting_user.role == ROLE_ADMIN_SUCURSAL:
        if sucursal_id is not None and sucursal_id != requesting_user.sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
        sucursal_id = requesting_user.sucursal_id
    elif requesting_user is not None and requesting_user.is_tenant_user and sucursal_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SUCURSAL_REQUERIDA")
    data = payload.model_dump(exclude={"tenant_id", "sucursal_id"})
    created = create_workshop_registration(
        {
            **data,
            "approval_status": "pendiente",
            "availability_status": "disponible",
            "password_hash": None,
            "tenant_id": tenant_id,
            "sucursal_id": sucursal_id,
        }
    )
    return WorkshopRegistrationResponse.model_validate(created)


"""
Aqui esta la logica de listado de talleres que obtiene
todos los talleres registrados en el sistema.
"""
def get_workshops_service(
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
) -> list[WorkshopRegistrationResponse]:
    if tenant_id is not None:
        rows = list_workshops_by_tenant(tenant_id, sucursal_id)
    else:
        rows = list_workshop_registrations()
    return [WorkshopRegistrationResponse.model_validate(row) for row in rows]


def _matches_requested_specialty(
    workshop: dict[str, object],
    requested_specialty: str | None,
) -> bool:
    normalized_requested = normalize_optional_text(requested_specialty)
    if not normalized_requested:
        return True

    requested_token = normalized_requested.casefold()
    specialties = [
        specialty.casefold()
        for specialty in workshop.get("specialties", [])
        if isinstance(specialty, str) and specialty.strip()
    ]
    primary_specialty = normalize_optional_text(str(workshop.get("specialty"))) if workshop.get("specialty") else None
    if primary_specialty and primary_specialty.casefold() not in specialties:
        specialties.insert(0, primary_specialty.casefold())
    return requested_token in specialties


def _safe_public_email(raw_email: object, *, tenant_id: int, workshop_id: int) -> str:
    candidate = normalize_optional_text(str(raw_email)) if raw_email is not None else None
    if candidate:
        local_part, separator, domain = candidate.partition("@")
        if separator and local_part and domain and "." in domain and not domain.endswith(".local"):
            return candidate
    return f"workshop-{workshop_id}-tenant-{tenant_id}@example.com"


def _build_public_workshop_row(tenant: dict[str, object], row: dict[str, object]) -> dict[str, object] | None:
    latitude = row.get("workshop_latitude")
    if latitude is None:
        latitude = row.get("sucursal_latitude")
    longitude = row.get("workshop_longitude")
    if longitude is None:
        longitude = row.get("sucursal_longitude")
    if latitude is None or longitude is None:
        return None

    raw_specialties = row.get("specialties") or []
    specialties = [str(value).strip() for value in raw_specialties if str(value).strip()]
    primary_specialty = normalize_optional_text(str(row.get("workshop_specialty") or "")) or (
        specialties[0] if specialties else None
    )
    if primary_specialty is None:
        return None
    if primary_specialty not in specialties:
        specialties.insert(0, primary_specialty)

    return {
        "id": int(row["workshop_id"]),
        "workshop_name": row.get("workshop_name") or row.get("sucursal_nombre") or tenant.get("nombre") or "Taller",
        "contact_name": row.get("contact_name") or row.get("responsable") or row.get("sucursal_nombre") or "Responsable",
        "phone": row.get("workshop_phone") or row.get("sucursal_telefono") or "",
        "email": _safe_public_email(
            row.get("email"),
            tenant_id=int(tenant["id"]),
            workshop_id=int(row["workshop_id"]),
        ),
        "zone": row.get("workshop_zone") or row.get("sucursal_zona") or "",
        "specialty": primary_specialty,
        "specialties": specialties,
        "approval_status": "activo",
        "availability_status": "disponible",
        "latitude": float(latitude),
        "longitude": float(longitude),
        "timezone": row.get("timezone"),
        "utc_offset_minutes": row.get("utc_offset_minutes"),
        "tenant_id": int(tenant["id"]),
        "tenant_slug": tenant.get("slug"),
        "sucursal_id": int(row["sucursal_id"]),
        "sucursal_nombre": row.get("sucursal_nombre"),
        "created_at": row["created_at"],
    }


def _list_public_saas_workshops(
    specialty: str | None = None,
    problem_type: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float | None = None,
) -> list[WorkshopRegistrationResponse]:
    from app.saas_master import list_all_tenants
    from app.tenant_manager import get_tenant_engine

    requested_specialty = problem_type or specialty
    sql = text(
        """
        SELECT
            s.id AS sucursal_id,
            s.nombre AS sucursal_nombre,
            s.zona AS sucursal_zona,
            s.telefono AS sucursal_telefono,
            s.responsable,
            s.latitud AS sucursal_latitude,
            s.longitud AS sucursal_longitude,
            wr.id AS workshop_id,
            wr.workshop_name,
            wr.contact_name,
            wr.phone AS workshop_phone,
            wr.email,
            wr.zone AS workshop_zone,
            wr.specialty AS workshop_specialty,
            wr.latitude AS workshop_latitude,
            wr.longitude AS workshop_longitude,
            wr.timezone,
            wr.utc_offset_minutes,
            wr.created_at,
            COALESCE(
                ws.specialties,
                CASE
                    WHEN wr.specialty IS NOT NULL THEN ARRAY[wr.specialty]::VARCHAR[]
                    ELSE ARRAY[]::VARCHAR[]
                END
            ) AS specialties
        FROM sucursales s
        JOIN LATERAL (
            SELECT
                id,
                workshop_name,
                contact_name,
                phone,
                email,
                zone,
                specialty,
                approval_status,
                availability_status,
                latitude,
                longitude,
                timezone,
                utc_offset_minutes,
                created_at
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

    public_rows: list[WorkshopRegistrationResponse] = []
    for tenant in list_all_tenants():
        if tenant.get("estado") != "activo":
            continue
        try:
            engine = get_tenant_engine(tenant)
            with engine.connect() as connection:
                rows = [dict(item) for item in connection.execute(sql).mappings().all()]
        except Exception:
            logger.exception(
                "No se pudo listar workshops publicos SaaS para tenant_id=%s slug=%s",
                tenant.get("id"),
                tenant.get("slug"),
            )
            continue

        for row in rows:
            normalized = _build_public_workshop_row(tenant, row)
            if normalized is None:
                continue
            if not _matches_requested_specialty(normalized, requested_specialty):
                continue
            if latitude is not None and longitude is not None and radius is not None:
                distance = calculate_distance_meters(
                    float(latitude),
                    float(longitude),
                    float(normalized["latitude"]),
                    float(normalized["longitude"]),
                )
                if distance > float(radius):
                    continue
            public_rows.append(WorkshopRegistrationResponse.model_validate(normalized))

    public_rows.sort(key=lambda item: (item.workshop_name.casefold(), item.id))
    return public_rows


"""
Aqui esta la logica de cambio de contrasena de taller que valida
la clave temporal inicial antes de guardar una nueva.
"""
def change_workshop_password_service(payload: WorkshopPasswordChangeRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    workshop = get_workshop_by_email(normalized_email)
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    password_hash = workshop.get("password_hash")
    uses_initial_password = isinstance(password_hash, str) and verify_password(
        settings.workshop_initial_password, password_hash
    )
    accepts_missing_initial_password = (
        not isinstance(password_hash, str) and workshop["approval_status"] != "activo"
    )
    if not uses_initial_password and not accepts_missing_initial_password:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este taller ya no usa la contraseña temporal inicial",
        )
    updated = update_workshop_approval_status_with_password(
        int(workshop["id"]),
        "activo",
        hash_password(payload.new_password),
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    return {"message": "La contraseña del taller fue actualizada correctamente"}


"""
Aqui esta la logica de recuperacion de contrasena de taller que restablece
la clave cuando el taller ya fue habilitado por el administrador.
"""
def forgot_workshop_password_service(payload: WorkshopForgotPasswordRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    workshop = get_workshop_by_email(normalized_email)
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if workshop["approval_status"] != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El taller todavía no fue habilitado por el administrador",
        )
    updated = update_workshop_password(int(workshop["id"]), hash_password(payload.new_password))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    return {"message": "La contraseña del taller fue restablecida correctamente"}


"""
Aqui esta la logica de edicion de taller que actualiza
los datos del taller y su contrasena si fue enviada.
"""
def edit_workshop_service(
    workshop_id: int,
    payload: WorkshopRegistrationUpdate,
    requesting_user: TokenPayload | None = None,
) -> WorkshopRegistrationResponse:
    current_workshop = get_workshop_by_id(workshop_id)
    if not current_workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if (
        requesting_user is not None
        and requesting_user.role == ROLE_ADMIN_SUCURSAL
        and current_workshop.get("sucursal_id") != requesting_user.sucursal_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    sucursal_id = payload.sucursal_id
    if requesting_user is not None and requesting_user.role == ROLE_ADMIN_SUCURSAL:
        if sucursal_id is not None and sucursal_id != requesting_user.sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
        sucursal_id = requesting_user.sucursal_id
    elif sucursal_id is None:
        sucursal_id = current_workshop.get("sucursal_id")
    updated = update_workshop_registration(
        workshop_id,
        {
            **payload.model_dump(exclude={"password", "tenant_id", "sucursal_id"}),
            "approval_status": None,
            "availability_status": None,
            "password_hash": hash_password(payload.password) if payload.password else None,
            "sucursal_id": sucursal_id,
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    return WorkshopRegistrationResponse.model_validate(updated)


"""
Aqui esta la logica de aprobacion de taller que cambia
el estado del taller y asigna la contrasena inicial cuando corresponde.
"""
def edit_workshop_approval_status_service(
    workshop_id: int, payload: WorkshopApprovalStatusUpdate
) -> WorkshopRegistrationResponse:
    current_workshop = get_workshop_by_id(workshop_id)
    if not current_workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if str(current_workshop["approval_status"]) == "activo" and payload.approval_status == "pendiente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un taller activo ya no puede volver a pendiente; solo puede pasar a rechazado",
        )
    password_hash = hash_password(settings.workshop_initial_password) if payload.approval_status == "activo" else None
    updated = update_workshop_approval_status_with_password(
        workshop_id,
        payload.approval_status,
        password_hash,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    return WorkshopRegistrationResponse.model_validate(updated)


"""
Aqui esta la logica de eliminacion de taller que verifica
si existe el taller y luego lo borra del sistema.
"""
def remove_workshop_service(workshop_id: int, requesting_user: TokenPayload | None = None) -> None:
    workshop = get_workshop_by_id(workshop_id)
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
    if (
        requesting_user is not None
        and requesting_user.role == ROLE_ADMIN_SUCURSAL
        and workshop.get("sucursal_id") != requesting_user.sucursal_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    if not delete_workshop_registration(workshop_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")


# =========================================================
# CONTROLADORES HTTP DE TALLERES
# En esta seccion estan los endpoints que maneja este modulo.
# Aqui puedes ubicar rapidamente:
# - POST para registrar taller
# - GET para listar talleres
# - PUT para editar datos del taller
# - PUT para cambiar el estado de aprobacion
# - POST y PUT para contrasena y recuperacion
# - DELETE para eliminar taller
# =========================================================
@router.post(
    f"{settings.api_prefix}/workshops",
    response_model=WorkshopRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de registro de taller que crea una nueva solicitud de taller.
def register_workshop(
    payload: WorkshopRegistrationCreate,
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> WorkshopRegistrationResponse:
    return register_workshop_service(payload, current_user)


@router.get(f"{settings.api_prefix}/workshops", response_model=list[WorkshopRegistrationResponse])
# Aqui esta el controlador GET de listado de talleres, filtrado por tenant del usuario autenticado.
def get_workshops(
    specialty: str | None = Query(default=None),
    problem_type: str | None = Query(default=None),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius: float | None = Query(default=None, gt=0),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> list[WorkshopRegistrationResponse]:
    if current_user is None:
        return _list_public_saas_workshops(
            specialty=specialty,
            problem_type=problem_type,
            latitude=lat,
            longitude=lng,
            radius=radius,
        )
    tenant_id = get_tenant_id_for_query(current_user)
    sucursal_id = (
        current_user.sucursal_id
        if current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL
        else None
    )
    return get_workshops_service(tenant_id, sucursal_id)


@router.post(f"{settings.api_prefix}/workshops/change-password")
# Aqui esta el controlador POST de cambio de contrasena que actualiza la clave inicial del taller.
def change_workshop_password(payload: WorkshopPasswordChangeRequest) -> dict[str, str]:
    return change_workshop_password_service(payload)


@router.api_route(f"{settings.api_prefix}/workshops/forgot-password", methods=["POST", "PUT"])
# Aqui esta el controlador POST y PUT de recuperacion de contrasena que restablece la clave del taller.
def forgot_workshop_password(payload: WorkshopForgotPasswordRequest) -> dict[str, str]:
    return forgot_workshop_password_service(payload)


@router.put(
    f"{settings.api_prefix}/workshops/{{workshop_id}}",
    response_model=WorkshopRegistrationResponse,
)
# Aqui esta el controlador PUT de edicion de taller que actualiza los datos del taller.
def edit_workshop(
    workshop_id: int,
    payload: WorkshopRegistrationUpdate,
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> WorkshopRegistrationResponse:
    return edit_workshop_service(workshop_id, payload, current_user)


@router.put(
    f"{settings.api_prefix}/workshops/{{workshop_id}}/approval-status",
    response_model=WorkshopRegistrationResponse,
)
# Aqui esta el controlador PUT de aprobacion de taller que cambia el estado de pendiente, activo o rechazado.
def edit_workshop_approval_status(
    workshop_id: int, payload: WorkshopApprovalStatusUpdate
) -> WorkshopRegistrationResponse:
    return edit_workshop_approval_status_service(workshop_id, payload)


@router.delete(
    f"{settings.api_prefix}/workshops/{{workshop_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
# Aqui esta el controlador DELETE de eliminacion de taller que borra un taller del sistema.
def remove_workshop(
    workshop_id: int,
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> None:
    remove_workshop_service(workshop_id, current_user)
