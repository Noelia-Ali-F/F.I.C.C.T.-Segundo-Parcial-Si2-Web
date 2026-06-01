from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.config import settings
from app.db import (
    create_technician,
    delete_technician,
    delete_technician_for_workshop,
    list_technicians,
    list_technicians_by_workshop,
    update_technician,
    update_technician_for_workshop,
)

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


class TechnicianBase(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=40)
    email: EmailStr
    specialty: str = Field(min_length=2, max_length=120)
    status: str = Field(pattern="^(disponible|ocupado|fuera_de_servicio)$")


class TechnicianCreate(TechnicianBase):
    workshop_id: int | None = Field(default=None, ge=1)


class TechnicianResponse(TechnicianBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workshop_id: int | None = None
    created_at: datetime
    updated_at: datetime


"""
Aqui esta la logica de registro de tecnico que crea
un tecnico nuevo y lo relaciona con un taller si corresponde.
"""
def register_technician_service(payload: TechnicianCreate, workshop_id: int | None) -> TechnicianResponse:
    created = create_technician({**payload.model_dump(), "workshop_id": workshop_id or payload.workshop_id})
    return TechnicianResponse.model_validate(created)


"""
Aqui esta la logica de listado de tecnicos que obtiene
todos los tecnicos o los filtra por taller.
"""
def get_technicians_service(workshop_id: int | None) -> list[TechnicianResponse]:
    rows = list_technicians_by_workshop(workshop_id) if workshop_id else list_technicians()
    return [TechnicianResponse.model_validate(row) for row in rows]


"""
Aqui esta la logica de edicion de tecnico que actualiza
sus datos y mantiene la relacion con el taller correspondiente.
"""
def edit_technician_service(
    technician_id: int,
    payload: TechnicianCreate,
    workshop_id: int | None,
) -> TechnicianResponse:
    technician_payload = payload.model_dump()
    technician_payload["workshop_id"] = workshop_id or payload.workshop_id
    updated = (
        update_technician_for_workshop(technician_id, workshop_id, technician_payload)
        if workshop_id
        else update_technician(technician_id, technician_payload)
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
    return TechnicianResponse.model_validate(updated)


"""
Aqui esta la logica de eliminacion de tecnico que borra
un tecnico general o un tecnico asociado a un taller.
"""
def remove_technician_service(technician_id: int, workshop_id: int | None) -> None:
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
) -> TechnicianResponse:
    return register_technician_service(payload, workshop_id)


@router.get(f"{settings.api_prefix}/technicians", response_model=list[TechnicianResponse])
# Aqui esta el controlador GET de listado de tecnicos que obtiene los tecnicos registrados.
def get_technicians(workshop_id: int | None = Query(default=None, ge=1)) -> list[TechnicianResponse]:
    return get_technicians_service(workshop_id)


@router.put(f"{settings.api_prefix}/technicians/{{technician_id}}", response_model=TechnicianResponse)
# Aqui esta el controlador PUT de edicion de tecnico que actualiza los datos de un tecnico.
def edit_technician(
    technician_id: int,
    payload: TechnicianCreate,
    workshop_id: int | None = Query(default=None, ge=1),
) -> TechnicianResponse:
    return edit_technician_service(technician_id, payload, workshop_id)


@router.delete(
    f"{settings.api_prefix}/technicians/{{technician_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
# Aqui esta el controlador DELETE de eliminacion de tecnico que borra un tecnico del sistema.
def remove_technician(technician_id: int, workshop_id: int | None = Query(default=None, ge=1)) -> None:
    remove_technician_service(technician_id, workshop_id)
