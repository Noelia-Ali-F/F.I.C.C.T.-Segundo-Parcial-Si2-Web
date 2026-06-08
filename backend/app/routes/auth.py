import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.utils import (
    PROTECTED_ADMIN_EMAIL,
    PROTECTED_ADMIN_ID,
    PROTECTED_ADMIN_ROLE,
    ROLE_CLIENTE,
    ROLE_TECNICO,
    ROLE_SUPERADMIN_GLOBAL,
    WORKSHOP_ROLE,
    TENANT_ROLES,
    create_access_token,
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
    # account_type ahora admite también 'tenant' para usuarios de empresa registrada
    account_type: str | None = Field(default=None, pattern="(?i)^(admin|workshop|client|cliente|tenant)$")


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
    tenant_id: int | None = None
    tenant_slug: str | None = None
    sucursal_id: int | None = None
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
    requested_account_type = _normalize_requested_account_type(payload.account_type)
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
            role=ROLE_SUPERADMIN_GLOBAL,
            status="active",
            tenant_id=None,
            requires_password_change=False,
            access_token=create_access_token(PROTECTED_ADMIN_ID, ROLE_SUPERADMIN_GLOBAL, None),
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
            workshop_tenant_id = int(workshop["tenant_id"]) if workshop.get("tenant_id") is not None else 1
            return LoginResponse(
                id=int(workshop["id"]),
                email=str(workshop["email"]),
                role=WORKSHOP_ROLE,
                status=workshop_login_status(workshop["approval_status"]),
                tenant_id=workshop_tenant_id,
                requires_password_change=True,
            )
        if workshop["approval_status"] != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El taller todavía no fue habilitado por el administrador",
            )
        reset_login_attempts(WORKSHOP_ROLE, normalized_email)
        workshop_tenant_id = int(workshop["tenant_id"]) if workshop.get("tenant_id") is not None else 1
        return LoginResponse(
            id=int(workshop["id"]),
            email=str(workshop["email"]),
            full_name=str(workshop["workshop_name"]),
            phone=str(workshop["phone"]),
            role=WORKSHOP_ROLE,
            status=workshop_login_status(workshop["approval_status"]),
            tenant_id=workshop_tenant_id,
            requires_password_change=False,
            access_token=create_access_token(int(workshop["id"]), WORKSHOP_ROLE, workshop_tenant_id),
            token_type="Bearer",
        )

    tenant_client_login = _try_tenant_client_login(normalized_email, payload.password)
    if tenant_client_login:
        return tenant_client_login

    client = get_client_by_email(normalized_email)
    if not client or not verify_password(payload.password, str(client["password_hash"])):
        # Intenta en usuarios_tenant antes de fallar definitivamente
        tenant_login = _try_tenant_user_login(normalized_email, payload.password)
        if tenant_login:
            return tenant_login
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    if client["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
    client_tenant_id = int(client["tenant_id"]) if client.get("tenant_id") is not None else 1
    resolved_role = ROLE_CLIENTE
    tenant_slug = str(client["tenant_slug"]) if client.get("tenant_slug") else _tenant_slug_from_id(client_tenant_id)
    return LoginResponse(
        id=int(client["id"]),
        email=str(client["email"]),
        full_name=str(client["full_name"]),
        phone=str(client["phone"]),
        role=resolved_role,
        status=str(client["status"]),
        tenant_id=client_tenant_id,
        tenant_slug=tenant_slug,
        requires_password_change=False,
        access_token=create_access_token(
            int(client["id"]),
            resolved_role,
            client_tenant_id,
            tenant_slug=tenant_slug,
        ),
        token_type="Bearer",
    )


def _normalize_requested_account_type(account_type: str | None) -> str | None:
    if account_type is None:
        return None
    normalized = account_type.strip().lower()
    if normalized == "cliente":
        return "client"
    return normalized or None


def _find_tenant_client_by_email(email: str) -> tuple[dict[str, object], dict[str, object]] | None:
    """Busca un cliente por correo dentro de los tenants activos."""
    try:
        from app.saas_master import list_all_tenants
        from app.tenant_manager import get_tenant_engine
        from sqlalchemy import text

        tenants = list_all_tenants()
        for tenant in tenants:
            if tenant.get("estado") != "activo":
                continue
            try:
                engine = get_tenant_engine(tenant)
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT * FROM clients WHERE email = :email"),
                        {"email": email},
                    ).mappings().first()
                if row:
                    return dict(tenant), dict(row)
            except Exception:
                continue
    except Exception:
        return None
    return None


def _try_tenant_client_login(email: str, password: str) -> "LoginResponse | None":
    """Intenta autenticar un cliente almacenado en la tabla clients de un tenant."""
    tenant_match = _find_tenant_client_by_email(email)
    if not tenant_match:
        return None

    tenant, row = tenant_match
    ensure_login_not_locked(ROLE_CLIENTE, email)
    if not verify_password(password, str(row.get("password_hash") or "")):
        register_failed_login_attempt(ROLE_CLIENTE, email)
    if row.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")

    reset_login_attempts(ROLE_CLIENTE, email)
    resolved_role = _resolve_tenant_client_role(row.get("role"))
    access_token = create_access_token(
        user_id=int(row["id"]),
        role=resolved_role,
        tenant_id=int(tenant["id"]),
        tenant_slug=str(tenant["slug"]),
        sucursal_id=None,
    )
    return LoginResponse(
        id=int(row["id"]),
        email=str(row["email"]),
        full_name=str(row["full_name"]) if row.get("full_name") is not None else None,
        phone=str(row["phone"]) if row.get("phone") is not None else None,
        role=resolved_role,
        status=str(row.get("status") or "active"),
        tenant_id=int(tenant["id"]),
        tenant_slug=str(tenant["slug"]),
        sucursal_id=None,
        requires_password_change=False,
        access_token=access_token,
        token_type="Bearer",
    )


def _resolve_tenant_client_role(role: object) -> str:
    normalized = str(role or "").strip().lower()
    if normalized in {"", "client", "cliente", ROLE_CLIENTE.lower()}:
        return ROLE_CLIENTE
    return str(role).strip()


def _tenant_slug_from_id(tenant_id: int | None) -> str | None:
    if tenant_id is None:
        return None
    try:
        from app.saas_master import get_tenant_by_id

        tenant = get_tenant_by_id(int(tenant_id))
        if tenant and tenant.get("slug"):
            return str(tenant["slug"])
    except Exception:
        return None
    return None


def _try_tenant_user_login(email: str, password: str) -> "LoginResponse | None":
    """
    Busca el usuario en todos los tenants activos de saas_master.

    Si lo encuentra y la contraseña es correcta, devuelve LoginResponse
    con tenant_slug en el JWT. Si no, retorna None.
    """
    try:
        from app.saas_master import list_all_tenants
        from app.tenant_manager import get_tenant_engine
        from sqlalchemy import text

        tenants = list_all_tenants()
        for tenant in tenants:
            if tenant.get("estado") != "activo":
                continue
            try:
                engine = get_tenant_engine(tenant)
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT * FROM usuarios_tenant WHERE email = :email"),
                        {"email": email},
                    ).mappings().first()
                if not row:
                    continue
                row = dict(row)
                if not verify_password(password, str(row["password_hash"])):
                    continue
                if row.get("estado") != "activo":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cuenta de usuario suspendida o inactiva",
                    )
                technician_id = None
                if str(row.get("role")) == ROLE_TECNICO:
                    if row.get("sucursal_id") is None:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tu cuenta técnica no tiene sucursal asignada. Solicita a tu empresa que complete la asignación.",
                        )
                    technician_id = _resolve_tenant_operational_technician_id(tenant, row)
                    if technician_id is None:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Tu cuenta técnica no tiene técnico operativo vinculado. Solicita a tu empresa que revise la configuración.",
                        )
                # Encontrado: genera JWT con tenant_slug
                sucursal_id = int(row["sucursal_id"]) if row.get("sucursal_id") else None
                access_token = create_access_token(
                    user_id=int(row["id"]),
                    role=str(row["role"]),
                    tenant_id=int(tenant["id"]),
                    tenant_slug=str(tenant["slug"]),
                    sucursal_id=sucursal_id,
                    technician_id=technician_id,
                )
                return LoginResponse(
                    id=int(row["id"]),
                    email=str(row["email"]),
                    full_name=str(row["full_name"]),
                    phone=str(row["phone"]),
                    role=str(row["role"]),
                    status="active",
                    tenant_id=int(tenant["id"]),
                    tenant_slug=str(tenant["slug"]),
                    sucursal_id=sucursal_id,
                    requires_password_change=False,
                    access_token=access_token,
                    token_type="Bearer",
                )
            except HTTPException:
                raise
            except Exception:
                continue
    except HTTPException:
        raise
    except Exception:
        pass
    return None


def _resolve_tenant_operational_technician_id(
    tenant: dict[str, object],
    tenant_user: dict[str, object],
) -> int | None:
    """Resuelve el technicians.id operativo asociado a un usuario TECNICO."""
    try:
        from app.tenant_manager import get_tenant_engine
        from sqlalchemy import text

        engine = get_tenant_engine(tenant)
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id
                    FROM technicians
                    WHERE usuario_tenant_id = :usuario_tenant_id
                    LIMIT 1
                    """
                ),
                {"usuario_tenant_id": int(tenant_user["id"])},
            ).mappings().first()
            if row:
                return int(row["id"])
            fallback = conn.execute(
                text(
                    """
                    SELECT id
                    FROM technicians
                    WHERE (
                        email = :email
                        OR (
                            full_name = :full_name
                            AND (
                                :sucursal_id IS NULL
                                OR sucursal_id = :sucursal_id
                            )
                        )
                    )
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ),
                {
                    "email": str(tenant_user.get("email") or ""),
                    "full_name": str(tenant_user.get("full_name") or ""),
                    "sucursal_id": int(tenant_user["sucursal_id"]) if tenant_user.get("sucursal_id") is not None else None,
                },
            ).mappings().first()
            if fallback:
                return int(fallback["id"])
    except Exception:
        return None
    return None


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
    tenant_client = _find_tenant_client_by_email(normalized_email)
    if tenant_client:
        _tenant, tenant_client_row = tenant_client
        return AccountTypeLookupResponse(role=str(tenant_client_row.get("role") or ROLE_CLIENTE))
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
    tenant_client = _find_tenant_client_by_email(normalized_email)
    if tenant_client:
        tenant, tenant_client_row = tenant_client
        if tenant_client_row.get("status") != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta suspendida")
        from app.tenant_manager import get_tenant_engine
        from sqlalchemy import text

        engine = get_tenant_engine(tenant)
        with engine.begin() as conn:
            updated = conn.execute(
                text(
                    """
                    UPDATE clients
                    SET password_hash = :password_hash,
                        updated_at = NOW()
                    WHERE id = :id
                    RETURNING id
                    """
                ),
                {
                    "id": int(tenant_client_row["id"]),
                    "password_hash": hash_password(payload.new_password),
                },
            ).mappings().first()
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
