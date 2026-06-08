from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy.exc import IntegrityError

from app.utils import (
    ROLE_CLIENTE,
    TokenPayload,
    get_current_user_optional,
    get_tenant_id_for_query,
    hash_password,
    is_protected_admin_email,
    is_protected_admin_role,
    verify_password,
)
from app.config import settings
from app.db import (
    create_client,
    delete_client,
    get_client_by_email,
    list_clients,
    list_clients_by_tenant,
    update_client,
    update_client_password,
    update_client_status,
)

# =========================================================
# ARCHIVO DE RUTAS DE CLIENTES
# Aqui esta todo lo relacionado con la gestion de clientes.
# Este archivo contiene:
# - modelos de registro, actualizacion y cambio de contrasena
# - logica para crear, editar, listar y eliminar clientes
# - controladores HTTP usados por el frontend para clientes
# Palabras clave para buscar despues:
# CLIENTES, REGISTER CLIENT, GET CLIENTS, UPDATE CLIENT, DELETE CLIENT
# =========================================================
router = APIRouter(tags=["clients"])


class ClientRegistrationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    identity_card: str = Field(
        min_length=5,
        max_length=40,
        validation_alias=AliasChoices("identity_card", "identityCard", "ci"),
    )
    full_name: str = Field(
        min_length=3,
        max_length=160,
        validation_alias=AliasChoices("full_name", "fullName", "name"),
    )
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40, validation_alias=AliasChoices("phone", "telefono"))
    password: str = Field(min_length=6, max_length=255)
    confirm_password: str | None = Field(
        default=None,
        min_length=6,
        max_length=255,
        validation_alias=AliasChoices("confirm_password", "confirmPassword"),
    )
    role: str = Field(default="client", min_length=2, max_length=40)
    accepted_terms: bool = Field(
        default=False,
        validation_alias=AliasChoices("accepted_terms", "acceptedTerms", "termsAccepted"),
    )
    tenant_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        validation_alias=AliasChoices("tenant_slug", "tenantSlug"),
    )
    tenant_id: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("tenant_id", "tenantId"),
    )

    @model_validator(mode="after")
    def validate_registration(self) -> "ClientRegistrationCreate":
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        if not self.accepted_terms:
            raise ValueError("Debes aceptar los terminos y condiciones")
        return self


class ClientRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identity_card: str
    full_name: str
    email: EmailStr
    phone: str
    role: str
    status: str
    accepted_terms: bool
    created_at: datetime
    updated_at: datetime


class ClientPasswordChangeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    current_password: str = Field(
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("current_password", "currentPassword"),
    )
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
    def validate_passwords(self) -> "ClientPasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        if self.current_password == self.new_password:
            raise ValueError("La nueva contraseña debe ser distinta a la actual")
        return self


class ClientForgotPasswordRequest(BaseModel):
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
    def validate_passwords(self) -> "ClientForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class ClientStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")


class ClientUpdate(BaseModel):
    identity_card: str = Field(min_length=5, max_length=40)
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    password: str | None = Field(default=None, min_length=6, max_length=255)
    role: str = Field(min_length=2, max_length=40)
    status: str = Field(pattern="^(active|suspended)$")
    accepted_terms: bool = True


"""
Aqui esta la logica de registro de cliente que valida
y crea una nueva cuenta de cliente en el sistema.
"""
def register_client_service(payload: ClientRegistrationCreate) -> ClientRegistrationResponse:
    normalized_email = payload.email.lower().strip()
    if is_protected_admin_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese correo está reservado para el administrador del sistema",
        )
    if is_protected_admin_role(payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se permite registrar clientes con rol administrador",
        )
    canonical_role = ROLE_CLIENTE
    requested_tenant_slug = (payload.tenant_slug or "").strip()
    requested_tenant_id = int(payload.tenant_id) if payload.tenant_id is not None else None

    try:
        if requested_tenant_slug or requested_tenant_id is not None:
            from app.saas_master import get_tenant_by_id, get_tenant_by_slug_any
            from app.tenant_context import clear_engine, set_context
            from app.tenant_manager import get_tenant_engine

            tenant = get_tenant_by_slug_any(requested_tenant_slug) if requested_tenant_slug else get_tenant_by_id(requested_tenant_id)
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TENANT_NO_ENCONTRADO")
            if tenant.get("estado") != "activo":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_INACTIVO")

            set_context(get_tenant_engine(tenant), tenant)
            try:
                created = create_client(
                    {
                        "identity_card": payload.identity_card,
                        "full_name": payload.full_name,
                        "email": normalized_email,
                        "phone": payload.phone,
                        "password_hash": hash_password(payload.password),
                        "role": ROLE_CLIENTE,
                        "status": "active",
                        "accepted_terms": payload.accepted_terms,
                    }
                )
            finally:
                clear_engine()
        else:
            created = create_client(
                {
                    "identity_card": payload.identity_card,
                    "full_name": payload.full_name,
                    "email": normalized_email,
                    "phone": payload.phone,
                    "password_hash": hash_password(payload.password),
                    "role": canonical_role,
                    "status": "active",
                    "accepted_terms": payload.accepted_terms,
                    "tenant_id": 1,
                }
            )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc
    return ClientRegistrationResponse.model_validate(created)


"""
Aqui esta la logica de listado de clientes que obtiene
todos los clientes registrados para mostrarlos en el sistema.
"""
def get_clients_service(tenant_id: int | None = None) -> list[ClientRegistrationResponse]:
    rows = list_clients_by_tenant(tenant_id) if tenant_id is not None else list_clients()
    return [ClientRegistrationResponse.model_validate(row) for row in rows]


"""
Aqui esta la logica de cambio de contrasena que verifica
la clave actual del cliente antes de guardar una nueva.
"""
def change_client_password_service(payload: ClientPasswordChangeRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    client = get_client_by_email(normalized_email)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if client["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
    password_hash = client.get("password_hash")
    if not isinstance(password_hash, str) or not verify_password(payload.current_password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual es incorrecta",
        )
    updated = update_client_password(int(client["id"]), hash_password(payload.new_password))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return {"message": "La contraseña del cliente fue actualizada correctamente"}


"""
Aqui esta la logica de recuperacion de contrasena que restablece
la clave de un cliente cuando su cuenta esta activa.
"""
def forgot_client_password_service(payload: ClientForgotPasswordRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    client = get_client_by_email(normalized_email)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if client["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
    updated = update_client_password(int(client["id"]), hash_password(payload.new_password))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return {"message": "La contraseña del cliente fue restablecida correctamente"}


"""
Aqui esta la logica de cambio de estado de cliente que actualiza
si la cuenta queda activa o suspendida.
"""
def edit_client_status_service(client_id: int, payload: ClientStatusUpdate) -> ClientRegistrationResponse:
    updated = update_client_status(client_id, payload.status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return ClientRegistrationResponse.model_validate(updated)


"""
Aqui esta la logica de edicion de cliente que actualiza
sus datos principales, rol, estado y contrasena si corresponde.
"""
def edit_client_service(client_id: int, payload: ClientUpdate) -> ClientRegistrationResponse:
    normalized_email = payload.email.lower().strip()
    if is_protected_admin_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese correo está reservado para el administrador del sistema",
        )
    if is_protected_admin_role(payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se permite asignar el rol administrador desde este módulo",
        )
    try:
        updated = update_client(
            client_id,
            {
                "identity_card": payload.identity_card,
                "full_name": payload.full_name,
                "email": normalized_email,
                "phone": payload.phone,
                "password_hash": hash_password(payload.password) if payload.password else None,
                "role": payload.role,
                "status": payload.status,
                "accepted_terms": payload.accepted_terms,
            },
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese carnet o correo",
        ) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return ClientRegistrationResponse.model_validate(updated)


"""
Aqui esta la logica de eliminacion de cliente que busca
y borra un cliente existente del sistema.
"""
def remove_client_service(client_id: int) -> None:
    if not delete_client(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


# =========================================================
# CONTROLADORES HTTP DE CLIENTES
# En esta seccion estan los endpoints principales del modulo clientes.
# Aqui estan agrupados los controladores para:
# - POST registrar cliente
# - GET listar clientes
# - PUT editar cliente y cambiar estado
# - DELETE eliminar cliente
# - POST o PUT para cambio y recuperacion de contrasena
# =========================================================
@router.post(
    f"{settings.api_prefix}/clientes",
    response_model=ClientRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de registro de cliente que crea una nueva cuenta de cliente.
def register_client(
    payload: ClientRegistrationCreate,
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    x_tenant_id: int | None = Header(default=None, alias="X-Tenant-Id"),
) -> ClientRegistrationResponse:
    updates: dict[str, object] = {}
    if x_tenant_slug and not payload.tenant_slug:
        updates["tenant_slug"] = x_tenant_slug
    if x_tenant_id is not None and payload.tenant_id is None:
        updates["tenant_id"] = x_tenant_id
    if updates:
        payload = payload.model_copy(update=updates)
    return register_client_service(payload)


@router.get(f"{settings.api_prefix}/clientes", response_model=list[ClientRegistrationResponse])
# Aqui esta el controlador GET de listado de clientes que obtiene todos los clientes registrados.
def get_clients(
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> list[ClientRegistrationResponse]:
    tenant_id = get_tenant_id_for_query(current_user)
    return get_clients_service(tenant_id)


@router.post(f"{settings.api_prefix}/clientes/change-password")
# Aqui esta el controlador POST de cambio de contrasena que actualiza la clave del cliente.
def change_client_password(payload: ClientPasswordChangeRequest) -> dict[str, str]:
    return change_client_password_service(payload)


@router.api_route(f"{settings.api_prefix}/clientes/forgot-password", methods=["POST", "PUT"])
# Aqui esta el controlador POST y PUT de recuperacion de contrasena que restablece la clave del cliente.
def forgot_client_password(payload: ClientForgotPasswordRequest) -> dict[str, str]:
    return forgot_client_password_service(payload)


@router.put(
    f"{settings.api_prefix}/clientes/{{client_id}}/status",
    response_model=ClientRegistrationResponse,
)
# Aqui esta el controlador PUT de estado del cliente que cambia si la cuenta esta activa o suspendida.
def edit_client_status(client_id: int, payload: ClientStatusUpdate) -> ClientRegistrationResponse:
    return edit_client_status_service(client_id, payload)


@router.put(f"{settings.api_prefix}/clientes/{{client_id}}", response_model=ClientRegistrationResponse)
# Aqui esta el controlador PUT de edicion de cliente que actualiza sus datos principales.
def edit_client(client_id: int, payload: ClientUpdate) -> ClientRegistrationResponse:
    return edit_client_service(client_id, payload)


@router.delete(f"{settings.api_prefix}/clientes/{{client_id}}", status_code=status.HTTP_204_NO_CONTENT)
# Aqui esta el controlador DELETE de eliminacion de cliente que borra un cliente del sistema.
def remove_client(client_id: int) -> None:
    remove_client_service(client_id)
