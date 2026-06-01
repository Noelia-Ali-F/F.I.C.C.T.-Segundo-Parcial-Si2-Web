import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.utils import (
    PROTECTED_ADMIN_EMAIL,
    PROTECTED_ADMIN_ID,
    PROTECTED_ADMIN_ROLE,
    WORKSHOP_ROLE,
    ensure_login_not_locked,
    hash_password,
    is_protected_admin_email,
    register_failed_login_attempt,
    reset_login_attempts,
    verify_password,
    workshop_login_status,
)
from app.config import settings
from app.db import (
    get_client_by_email,
    get_workshop_by_email,
    update_client_password,
    update_workshop_password,
)

# =========================================================
# ARCHIVO DE RUTAS DE AUTENTICACION
# Aqui esta todo lo relacionado con el acceso al sistema.
# Este archivo contiene:
# - modelos de entrada y salida para login y recuperacion de cuenta
# - logica para validar credenciales
# - controladores HTTP de autenticacion
# Palabras clave para buscar despues:
# AUTH, LOGIN, ACCOUNT TYPE, FORGOT PASSWORD, AUTENTICACION
# =========================================================
router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)
    account_type: str | None = Field(default=None, pattern="^(admin|workshop|client)$")


class AccountTypeLookupRequest(BaseModel):
    email: EmailStr


class AccountTypeLookupResponse(BaseModel):
    role: str | None = None


class LoginResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    status: str
    requires_password_change: bool = False
    access_token: str | None = None
    token_type: str | None = None


class UnifiedForgotPasswordRequest(BaseModel):
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
    def validate_passwords(self) -> "UnifiedForgotPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


"""
Aqui esta la logica de inicio de sesion que valida credenciales
y determina si el acceso corresponde a administrador, taller o cliente.
"""
def login_service(payload: LoginRequest) -> LoginResponse:
    normalized_email = payload.email.lower().strip()
    requested_account_type = payload.account_type
    if is_protected_admin_email(normalized_email):
        ensure_login_not_locked(PROTECTED_ADMIN_ROLE, normalized_email)
        if requested_account_type and requested_account_type != PROTECTED_ADMIN_ROLE:
            register_failed_login_attempt(PROTECTED_ADMIN_ROLE, normalized_email)
        if payload.password != settings.protected_admin_password:
            register_failed_login_attempt(PROTECTED_ADMIN_ROLE, normalized_email)
        reset_login_attempts(PROTECTED_ADMIN_ROLE, normalized_email)
        return LoginResponse(
            id=PROTECTED_ADMIN_ID,
            email=PROTECTED_ADMIN_EMAIL,
            full_name=settings.protected_admin_full_name,
            phone=settings.protected_admin_phone,
            role=PROTECTED_ADMIN_ROLE,
            status="active",
            requires_password_change=False,
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer",
        )

    workshop = get_workshop_by_email(normalized_email)
    if workshop:
        ensure_login_not_locked(WORKSHOP_ROLE, normalized_email)
        if requested_account_type and requested_account_type != WORKSHOP_ROLE:
            register_failed_login_attempt(WORKSHOP_ROLE, normalized_email)
        password_hash = workshop.get("password_hash")
        uses_initial_password = isinstance(password_hash, str) and verify_password(
            settings.workshop_initial_password, password_hash
        )
        accepts_missing_initial_password = (
            not isinstance(password_hash, str)
            and workshop["approval_status"] != "activo"
            and payload.password == settings.workshop_initial_password
        )
        if not accepts_missing_initial_password and (
            not isinstance(password_hash, str) or not verify_password(payload.password, password_hash)
        ):
            register_failed_login_attempt(WORKSHOP_ROLE, normalized_email)
        if uses_initial_password or accepts_missing_initial_password:
            reset_login_attempts(WORKSHOP_ROLE, normalized_email)
            return LoginResponse(
                id=int(workshop["id"]),
                email=str(workshop["email"]),
                role=WORKSHOP_ROLE,
                status=workshop_login_status(workshop["approval_status"]),
                requires_password_change=True,
            )
        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )
        reset_login_attempts(WORKSHOP_ROLE, normalized_email)
        return LoginResponse(
            id=int(workshop["id"]),
            email=str(workshop["email"]),
            full_name=str(workshop["workshop_name"]),
            phone=str(workshop["phone"]),
            role=WORKSHOP_ROLE,
            status=workshop_login_status(workshop["approval_status"]),
            requires_password_change=False,
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer",
        )

    client = get_client_by_email(normalized_email)
    if not client or not verify_password(payload.password, str(client["password_hash"])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    if client["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
    return LoginResponse(
        id=int(client["id"]),
        email=str(client["email"]),
        full_name=str(client["full_name"]),
        phone=str(client["phone"]),
        role=str(client["role"]),
        status=str(client["status"]),
        requires_password_change=False,
        access_token=secrets.token_urlsafe(32),
        token_type="Bearer",
    )


"""
Aqui esta la logica de tipo de cuenta que revisa el correo
y detecta si pertenece a un taller, a un cliente o a ninguna cuenta.
"""
def lookup_account_type_service(payload: AccountTypeLookupRequest) -> AccountTypeLookupResponse:
    normalized_email = payload.email.lower().strip()
    workshop = get_workshop_by_email(normalized_email)
    if workshop:
        return AccountTypeLookupResponse(role=WORKSHOP_ROLE)
    client = get_client_by_email(normalized_email)
    if client:
        return AccountTypeLookupResponse(role=str(client["role"]))
    return AccountTypeLookupResponse(role=None)


"""
Aqui esta la logica de recuperacion de contrasena que actualiza
la clave de clientes o talleres segun el correo recibido.
"""
def forgot_password_service(payload: UnifiedForgotPasswordRequest) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    client = get_client_by_email(normalized_email)
    if client:
        if client["status"] != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
        updated = update_client_password(int(client["id"]), hash_password(payload.new_password))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
        return {"message": "La contraseña del cliente fue restablecida correctamente"}

    workshop = get_workshop_by_email(normalized_email)
    if workshop:
        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )
        updated = update_workshop_password(int(workshop["id"]), hash_password(payload.new_password))
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado")
        return {"message": "La contraseña del taller fue restablecida correctamente"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe una cuenta con ese correo")


# =========================================================
# CONTROLADORES HTTP DE AUTENTICACION
# En esta seccion estan los endpoints que recibe el frontend.
# Aqui vas a encontrar controladores de tipo:
# - POST para iniciar sesion
# - POST para identificar el tipo de cuenta por correo
# - POST y PUT para restablecer contrasena
# Si necesitas buscar las rutas principales de auth, estan aqui.
# =========================================================
@router.post(
    f"{settings.api_prefix}/auth/login",
    response_model=LoginResponse,
    response_model_exclude_none=True,
)
# Aqui esta el controlador POST de inicio de sesion que valida credenciales y devuelve el acceso.
def login(payload: LoginRequest) -> LoginResponse:
    return login_service(payload)


@router.post(
    f"{settings.api_prefix}/auth/account-type",
    response_model=AccountTypeLookupResponse,
)
# Aqui esta el controlador POST de tipo de cuenta que identifica si el correo pertenece a cliente o taller.
def lookup_account_type(payload: AccountTypeLookupRequest) -> AccountTypeLookupResponse:
    return lookup_account_type_service(payload)


@router.api_route(f"{settings.api_prefix}/auth/forgot-password", methods=["POST", "PUT"])
# Aqui esta el controlador POST y PUT de recuperacion de contrasena que restablece la clave de clientes o talleres.
def forgot_password(payload: UnifiedForgotPasswordRequest) -> dict[str, str]:
    return forgot_password_service(payload)
