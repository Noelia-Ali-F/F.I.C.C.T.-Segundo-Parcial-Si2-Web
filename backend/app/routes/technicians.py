from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.config import settings
from app.db import (
    create_technician,
    delete_technician,
    delete_technician_for_workshop,
    get_sucursal_by_id,
    get_technician_by_id,
    get_workshop_by_sucursal,
    get_workshop_by_id,
    list_technicians,
    list_technicians_by_tenant,
    list_technicians_by_workshop,
    update_technician,
    update_technician_for_workshop,
)
from app.utils import ROLE_ADMIN_SUCURSAL, TokenPayload, get_current_user_optional, get_tenant_id_for_query

# =========================================================
# ARCHIVO DE RUTAS DE TECNICOS
# Aqui esta todo lo relacionado con los tecnicos asociados a talleres.
# Este archivo contiene:
# - modelos para crear y responder datos de tecnicos
# - logica para registrar, listar, editar y eliminar tecnicos
# - controladores HTTP del modulo tecnicos
# Palabras clave para buscar despues:
# TECNICOS, TECHNICIANS, REGISTER TECHNICIAN, UPDATE TECHNICIAN
# =========================================================
router = APIRouter(tags=["technicians"])


def _ensure_not_global_technician_management(current_user: TokenPayload | None) -> None:
    if current_user is not None and current_user.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los técnicos se administran dentro de cada organización.",
        )


class TechnicianBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    specialty: str = Field(min_length=2, max_length=120)
    status: str = Field(pattern="^(disponible|ocupado|fuera_de_servicio)$")


class TechnicianCreate(TechnicianBase):
    workshop_id: int | None = Field(default=None, ge=1)
    sucursal_id: int | None = Field(default=None, ge=1)


class TechnicianResponse(TechnicianBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_id: int | None = None
    usuario_tenant_id: int | None = None
    tenant_id: int | None = None
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    created_at: datetime
    updated_at: datetime


"""
Aqui esta la logica de registro de tecnico que crea
un tecnico nuevo y lo relaciona con un taller si corresponde.
"""
def _resolve_technician_scope(
    payload: TechnicianCreate,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> tuple[int | None, int | None]:
    resolved_sucursal_id = payload.sucursal_id

    if current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL:
        if resolved_sucursal_id is not None and resolved_sucursal_id != current_user.sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
        resolved_sucursal_id = current_user.sucursal_id

    resolved_workshop_id = workshop_id or payload.workshop_id
    tenant_scoped = current_user is not None and bool(current_user.tenant_slug)

    if resolved_sucursal_id is not None:
        sucursal = get_sucursal_by_id(resolved_sucursal_id)
        if not sucursal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
        if sucursal.get("estado") != "activo":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sucursal asignada está inactiva",
            )
        workshop = get_workshop_by_sucursal(resolved_sucursal_id)
        if not workshop:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sucursal seleccionada no tiene taller operativo vinculado",
            )
        resolved_workshop_id = int(workshop["id"])
        return resolved_workshop_id, resolved_sucursal_id

    workshop = get_workshop_by_id(resolved_workshop_id) if resolved_workshop_id is not None else None
    if workshop is not None:
        workshop_sucursal_id = (
            int(workshop["sucursal_id"])
            if workshop.get("sucursal_id") is not None
            else None
        )
        if current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL and workshop_sucursal_id != current_user.sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
        resolved_sucursal_id = workshop_sucursal_id

    if tenant_scoped and resolved_sucursal_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona una sucursal para el técnico.",
        )

    return resolved_workshop_id, resolved_sucursal_id


def register_technician_service(
    payload: TechnicianCreate,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> TechnicianResponse:
    resolved_workshop_id, resolved_sucursal_id = _resolve_technician_scope(payload, workshop_id, current_user)
    created = create_technician(
        {
            **payload.model_dump(exclude={"workshop_id", "sucursal_id"}),
            "workshop_id": resolved_workshop_id,
            "sucursal_id": resolved_sucursal_id,
        }
    )
    created_detail = get_technician_by_id(int(created["id"])) or created
    return TechnicianResponse.model_validate(created_detail)


"""
Aqui esta la logica de listado de tecnicos que obtiene
todos los tecnicos o los filtra por taller.
"""
def get_technicians_service(
    workshop_id: int | None,
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
) -> list[TechnicianResponse]:
    if workshop_id:
        rows = list_technicians_by_workshop(workshop_id)
    elif tenant_id is not None:
        rows = list_technicians_by_tenant(tenant_id, sucursal_id)
    else:
        rows = list_technicians()
    if sucursal_id is not None:
        rows = [row for row in rows if row.get("sucursal_id") == sucursal_id]
    return [TechnicianResponse.model_validate(row) for row in rows]


"""
Aqui esta la logica de edicion de tecnico que actualiza
sus datos y mantiene la relacion con el taller correspondiente.
"""
def edit_technician_service(
    technician_id: int,
    payload: TechnicianCreate,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> TechnicianResponse:
    current_technician = get_technician_by_id(technician_id)
    if not current_technician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
    if (
        current_user is not None
        and current_user.role == ROLE_ADMIN_SUCURSAL
        and current_technician.get("sucursal_id") != current_user.sucursal_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    resolved_workshop_id, resolved_sucursal_id = _resolve_technician_scope(payload, workshop_id, current_user)
    technician_payload = payload.model_dump(exclude={"workshop_id", "sucursal_id"})
    technician_payload["workshop_id"] = resolved_workshop_id
    technician_payload["sucursal_id"] = resolved_sucursal_id
    keep_same_workshop = (
        resolved_workshop_id is not None
        and current_technician.get("workshop_id") == resolved_workshop_id
        and current_user is not None
        and not current_user.tenant_slug
    )
    updated = (
        update_technician_for_workshop(technician_id, resolved_workshop_id, technician_payload)
        if keep_same_workshop
        else update_technician(technician_id, technician_payload)
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
    updated_detail = get_technician_by_id(technician_id) or updated
    return TechnicianResponse.model_validate(updated_detail)


"""
Aqui esta la logica de eliminacion de tecnico que borra
un tecnico general o un tecnico asociado a un taller.
"""
def remove_technician_service(
    technician_id: int,
    workshop_id: int | None,
    current_user: TokenPayload | None = None,
) -> None:
    current_technician = get_technician_by_id(technician_id)
    if not current_technician:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
    if (
        current_user is not None
        and current_user.role == ROLE_ADMIN_SUCURSAL
        and current_technician.get("sucursal_id") != current_user.sucursal_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    deleted = (
        delete_technician_for_workshop(technician_id, workshop_id)
        if workshop_id
        else delete_technician(technician_id)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")


# =========================================================
# CONTROLADORES HTTP DE TECNICOS
# En esta seccion estan los endpoints del modulo tecnicos.
# Aqui puedes encontrar:
# - POST para registrar tecnico
# - GET para listar tecnicos
# - PUT para editar tecnico
# - DELETE para eliminar tecnico
# Algunos endpoints pueden trabajar filtrando por workshop_id.
# =========================================================
@router.post(
    f"{settings.api_prefix}/technicians",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de registro de tecnico que crea un tecnico para un taller.
def register_technician(
    payload: TechnicianCreate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> TechnicianResponse:
    _ensure_not_global_technician_management(current_user)
    return register_technician_service(payload, workshop_id, current_user)


@router.get(f"{settings.api_prefix}/technicians", response_model=list[TechnicianResponse])
# Aqui esta el controlador GET de listado de tecnicos filtrado por taller o por tenant del usuario.
def get_technicians(
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> list[TechnicianResponse]:
    _ensure_not_global_technician_management(current_user)
    if workshop_id is not None and current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL:
        workshop = get_workshop_by_id(workshop_id)
        if workshop and workshop.get("sucursal_id") != current_user.sucursal_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
    tenant_id = get_tenant_id_for_query(current_user)
    sucursal_id = (
        current_user.sucursal_id
        if current_user is not None and current_user.role == ROLE_ADMIN_SUCURSAL
        else None
    )
    return get_technicians_service(workshop_id, tenant_id, sucursal_id)


@router.put(f"{settings.api_prefix}/technicians/{{technician_id}}", response_model=TechnicianResponse)
# Aqui esta el controlador PUT de edicion de tecnico que actualiza los datos de un tecnico.
def edit_technician(
    technician_id: int,
    payload: TechnicianCreate,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> TechnicianResponse:
    _ensure_not_global_technician_management(current_user)
    return edit_technician_service(technician_id, payload, workshop_id, current_user)


@router.delete(
    f"{settings.api_prefix}/technicians/{{technician_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
# Aqui esta el controlador DELETE de eliminacion de tecnico que borra un tecnico del sistema.
def remove_technician(
    technician_id: int,
    workshop_id: int | None = Query(default=None, ge=1),
    current_user: TokenPayload | None = Depends(get_current_user_optional),
) -> None:
    _ensure_not_global_technician_management(current_user)
    remove_technician_service(technician_id, workshop_id, current_user)
