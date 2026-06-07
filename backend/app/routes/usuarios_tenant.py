"""
Gestión de usuarios dentro de un tenant.

SUPERADMIN_TENANT puede crear/listar/editar/desactivar usuarios de su empresa:
  - SUPERADMIN_TENANT (otros administradores globales de la empresa)
  - ADMIN_SUCURSAL (administradores de una sucursal)
  - TECNICO (técnicos asignados a una sucursal)
  - CLIENTE (clientes móviles de la empresa)
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import text

from app.config import settings
from app.utils import (
    TokenPayload,
    require_superadmin_tenant,
    require_admin_sucursal,
    get_current_user,
    ROLE_SUPERADMIN_TENANT,
    ROLE_ADMIN_SUCURSAL,
    ROLE_TECNICO,
    ROLE_CLIENTE,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["usuarios-tenant"])

ROLES_PERMITIDOS = {ROLE_SUPERADMIN_TENANT, ROLE_ADMIN_SUCURSAL, ROLE_TECNICO, ROLE_CLIENTE}


# =============================================================================
# Modelos
# =============================================================================

class UsuarioTenantCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    email: EmailStr
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(default="", max_length=40)
    password: str = Field(min_length=6, max_length=255)
    role: str = Field(default=ROLE_TECNICO)
    sucursal_id: int | None = Field(default=None, ge=1)

    def validate_role(self) -> None:
        if self.role not in ROLES_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol inválido. Permitidos: {', '.join(sorted(ROLES_PERMITIDOS))}",
            )


class UsuarioTenantUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    full_name: str | None = Field(default=None, min_length=3, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    role: str | None = None
    sucursal_id: int | None = None
    estado: str | None = Field(default=None, pattern="^(activo|inactivo|suspendido)$")


class UsuarioTenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str
    role: str
    sucursal_id: int | None = None
    estado: str
    created_at: datetime
    updated_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=6, max_length=255)


def _get_engine(current_user: TokenPayload):
    if not current_user.tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es exclusivo para usuarios de empresa (tenant).",
        )
    from app.tenant_context import get_engine
    return get_engine()


def _get_sucursal_by_id(engine, sucursal_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, nombre, estado FROM sucursales WHERE id = :id"),
            {"id": sucursal_id},
        ).mappings().first()
    return dict(row) if row else None


def _validate_user_role_scope(
    *,
    engine,
    role: str,
    sucursal_id: int | None,
) -> None:
    if role == ROLE_SUPERADMIN_TENANT:
        if sucursal_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SUPERADMIN_TENANT no debe estar asignado a una sucursal",
            )
        return

    if role in {ROLE_ADMIN_SUCURSAL, ROLE_TECNICO} and sucursal_id is None:
        detail = "Selecciona la sucursal que administrará este usuario." if role == ROLE_ADMIN_SUCURSAL else f"El rol {role} requiere sucursal_id"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    if sucursal_id is not None:
        sucursal = _get_sucursal_by_id(engine, sucursal_id)
        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sucursal no encontrada",
            )
        if sucursal.get("estado") != "activo":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sucursal asignada está inactiva",
            )


def _get_usuario_or_404(engine, usuario_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM usuarios_tenant WHERE id = :id"),
            {"id": usuario_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return dict(row)


def _ensure_user_scope(current_user: TokenPayload, usuario: dict) -> None:
    if current_user.role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id != usuario.get("sucursal_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCESO_DENEGADO_SUCURSAL",
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    f"{settings.api_prefix}/tenant/usuarios",
    response_model=list[UsuarioTenantOut],
)
def listar_usuarios(
    current_user: TokenPayload = Depends(require_admin_sucursal),
) -> list[UsuarioTenantOut]:
    """Lista usuarios del tenant. ADMIN_SUCURSAL solo ve los de su sucursal."""
    engine = _get_engine(current_user)
    with engine.connect() as conn:
        if current_user.role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id:
            rows = conn.execute(
                text("SELECT * FROM usuarios_tenant WHERE sucursal_id = :sid ORDER BY full_name"),
                {"sid": current_user.sucursal_id},
            ).mappings().all()
        else:
            rows = conn.execute(
                text("SELECT * FROM usuarios_tenant ORDER BY full_name")
            ).mappings().all()
    return [UsuarioTenantOut.model_validate(dict(r)) for r in rows]


@router.post(
    f"{settings.api_prefix}/tenant/usuarios",
    response_model=UsuarioTenantOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    payload: UsuarioTenantCreate,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> UsuarioTenantOut:
    """Crea un nuevo usuario en el tenant. Solo SUPERADMIN_TENANT."""
    payload.validate_role()
    email = str(payload.email).lower().strip()
    engine = _get_engine(current_user)
    _validate_user_role_scope(
        engine=engine,
        role=payload.role,
        sucursal_id=payload.sucursal_id,
    )
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM usuarios_tenant WHERE email = :email"),
            {"email": email},
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese correo.",
            )
        row = conn.execute(
            text("""
                INSERT INTO usuarios_tenant (email, full_name, phone, password_hash, role, sucursal_id, estado)
                VALUES (:email, :full_name, :phone, :password_hash, :role, :sucursal_id, 'activo')
                RETURNING *
            """),
            {
                "email": email,
                "full_name": payload.full_name,
                "phone": payload.phone,
                "password_hash": hash_password(payload.password),
                "role": payload.role,
                "sucursal_id": payload.sucursal_id,
            },
        ).mappings().first()
    return UsuarioTenantOut.model_validate(dict(row))


@router.get(
    f"{settings.api_prefix}/tenant/usuarios/{{usuario_id}}",
    response_model=UsuarioTenantOut,
)
def obtener_usuario(
    usuario_id: int,
    current_user: TokenPayload = Depends(require_admin_sucursal),
) -> UsuarioTenantOut:
    engine = _get_engine(current_user)
    usuario = _get_usuario_or_404(engine, usuario_id)
    _ensure_user_scope(current_user, usuario)
    return UsuarioTenantOut.model_validate(usuario)


@router.put(
    f"{settings.api_prefix}/tenant/usuarios/{{usuario_id}}",
    response_model=UsuarioTenantOut,
)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioTenantUpdate,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> UsuarioTenantOut:
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if payload.role and payload.role not in ROLES_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Permitidos: {', '.join(sorted(ROLES_PERMITIDOS))}",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sin datos para actualizar")
    engine = _get_engine(current_user)
    usuario_actual = _get_usuario_or_404(engine, usuario_id)
    role_objetivo = payload.role or str(usuario_actual["role"])
    sucursal_objetivo = payload.sucursal_id if "sucursal_id" in data else usuario_actual.get("sucursal_id")
    _validate_user_role_scope(
        engine=engine,
        role=str(role_objetivo),
        sucursal_id=int(sucursal_objetivo) if sucursal_objetivo is not None else None,
    )
    fields = ", ".join(f"{k} = :{k}" for k in data)
    data["id"] = usuario_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE usuarios_tenant SET {fields}, updated_at = NOW() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UsuarioTenantOut.model_validate(dict(row))


@router.post(f"{settings.api_prefix}/tenant/usuarios/{{usuario_id}}/change-password")
def cambiar_password_usuario(
    usuario_id: int,
    payload: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """Permite al usuario cambiar su propia contraseña."""
    if current_user.user_id != usuario_id and not current_user.is_global_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes cambiar tu propia contraseña")
    engine = _get_engine(current_user)
    usuario = _get_usuario_or_404(engine, usuario_id)
    _ensure_user_scope(current_user, usuario)
    if not verify_password(payload.current_password, str(usuario["password_hash"])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña actual incorrecta")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE usuarios_tenant SET password_hash = :ph, updated_at = NOW() WHERE id = :id"),
            {"ph": hash_password(payload.new_password), "id": usuario_id},
        )
    return {"message": "Contraseña actualizada correctamente"}


@router.delete(
    f"{settings.api_prefix}/tenant/usuarios/{{usuario_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_usuario(
    usuario_id: int,
    current_user: TokenPayload = Depends(require_superadmin_tenant),
) -> None:
    engine = _get_engine(current_user)
    usuario = _get_usuario_or_404(engine, usuario_id)
    if str(usuario["role"]) == ROLE_SUPERADMIN_TENANT and int(usuario["id"]) == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes eliminar tu propio usuario SUPERADMIN_TENANT",
        )
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM usuarios_tenant WHERE id = :id RETURNING id"),
            {"id": usuario_id},
        ).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
