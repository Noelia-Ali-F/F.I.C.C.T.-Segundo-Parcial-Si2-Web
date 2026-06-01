from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator

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
from app.utils import hash_password, verify_password

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
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    utc_offset_minutes: int | None = None
    created_at: datetime


class WorkshopApprovalStatusUpdate(BaseModel):
    approval_status: str = Field(pattern="^(pendiente|activo|rechazado)$")


"""
Aqui esta la logica de registro de taller que crea
una nueva solicitud de taller con estado pendiente.
"""
def register_workshop_service(payload: WorkshopRegistrationCreate) -> WorkshopRegistrationResponse:
    created = create_workshop_registration(
        {**payload.model_dump(), "approval_status": "pendiente", "password_hash": None}
    )
    return WorkshopRegistrationResponse.model_validate(created)


"""
Aqui esta la logica de listado de talleres que obtiene
todos los talleres registrados en el sistema.
"""
def get_workshops_service() -> list[WorkshopRegistrationResponse]:
    return [WorkshopRegistrationResponse.model_validate(row) for row in list_workshop_registrations()]


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
    workshop_id: int, payload: WorkshopRegistrationUpdate
) -> WorkshopRegistrationResponse:
    updated = update_workshop_registration(
        workshop_id,
        {
            **payload.model_dump(exclude={"password"}),
            "approval_status": None,
            "password_hash": hash_password(payload.password) if payload.password else None,
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
def remove_workshop_service(workshop_id: int) -> None:
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
def register_workshop(payload: WorkshopRegistrationCreate) -> WorkshopRegistrationResponse:
    return register_workshop_service(payload)


@router.get(f"{settings.api_prefix}/workshops", response_model=list[WorkshopRegistrationResponse])
# Aqui esta el controlador GET de listado de talleres que obtiene todos los talleres registrados.
def get_workshops() -> list[WorkshopRegistrationResponse]:
    return get_workshops_service()


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
    workshop_id: int, payload: WorkshopRegistrationUpdate
) -> WorkshopRegistrationResponse:
    return edit_workshop_service(workshop_id, payload)


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
def remove_workshop(workshop_id: int) -> None:
    remove_workshop_service(workshop_id)
