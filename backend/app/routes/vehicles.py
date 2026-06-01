from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.db import create_vehicle, delete_vehicle, get_vehicle_by_id, list_vehicles, update_vehicle
from app.utils import ensure_client_exists, normalize_plate, remove_vehicle_photo, save_vehicle_photo

# =========================================================
# ARCHIVO DE RUTAS DE VEHICULOS
# Aqui esta todo lo relacionado con los vehiculos de los clientes.
# Este archivo contiene:
# - modelo de respuesta de vehiculo
# - logica para registrar, listar, editar y eliminar vehiculos
# - manejo de foto del vehiculo
# - controladores HTTP del modulo vehiculos
# Palabras clave para buscar despues:
# VEHICULOS, VEHICLES, FOTO VEHICULO, REGISTER VEHICLE, DELETE VEHICLE
# =========================================================
router = APIRouter(tags=["vehicles"])


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    brand: str
    model: str
    year: int
    plate: str
    color: str
    is_primary: bool
    photo_path: str | None = None
    photo_url: str | None = None
    created_at: datetime


"""
Aqui esta la logica de registro de vehiculo que guarda
los datos del vehiculo y su foto para un cliente.
"""
def register_vehicle_service(
    *,
    client_id: int,
    brand: str,
    model: str,
    year: int,
    plate: str,
    color: str,
    is_primary: bool,
    photo: UploadFile | None,
) -> VehicleResponse:
    ensure_client_exists(client_id)
    photo_path, photo_url = save_vehicle_photo(photo)
    try:
        created = create_vehicle(
            {
                "client_id": client_id,
                "brand": brand.strip(),
                "model": model.strip(),
                "year": year,
                "plate": normalize_plate(plate),
                "color": color.strip(),
                "is_primary": is_primary,
                "photo_path": photo_path,
                "photo_url": photo_url,
            }
        )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un vehiculo con esa placa") from exc
    return VehicleResponse.model_validate(created)


"""
Aqui esta la logica de listado de vehiculos que obtiene
los vehiculos registrados de un cliente especifico.
"""
def get_vehicles_service(client_id: int) -> list[VehicleResponse]:
    ensure_client_exists(client_id)
    try:
        rows = list_vehicles(client_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return [VehicleResponse.model_validate(row) for row in rows]


"""
Aqui esta la logica de edicion de vehiculo que actualiza
sus datos y reemplaza la foto cuando se envia una nueva.
"""
def edit_vehicle_service(
    *,
    vehicle_id: int,
    client_id: int,
    brand: str,
    model: str,
    year: int,
    plate: str,
    color: str,
    is_primary: bool,
    photo: UploadFile | None,
) -> VehicleResponse:
    ensure_client_exists(client_id)
    try:
        current_vehicle = get_vehicle_by_id(vehicle_id, client_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not current_vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")

    new_photo_path, new_photo_url = save_vehicle_photo(photo)
    photo_path = new_photo_path if new_photo_path is not None else current_vehicle.get("photo_path")
    photo_url = new_photo_url if new_photo_url is not None else current_vehicle.get("photo_url")
    try:
        updated = update_vehicle(
            vehicle_id,
            {
                "client_id": client_id,
                "brand": brand.strip(),
                "model": model.strip(),
                "year": year,
                "plate": normalize_plate(plate),
                "color": color.strip(),
                "is_primary": is_primary,
                "photo_path": photo_path,
                "photo_url": photo_url,
            },
        )
    except OperationalError as exc:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    except IntegrityError as exc:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un vehiculo con esa placa") from exc
    if not updated:
        if new_photo_path is not None:
            remove_vehicle_photo(new_photo_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    if new_photo_path is not None:
        remove_vehicle_photo(str(current_vehicle.get("photo_path")) if current_vehicle.get("photo_path") else None)
    return VehicleResponse.model_validate(updated)


"""
Aqui esta la logica de eliminacion de vehiculo que borra
el vehiculo y tambien elimina su foto almacenada.
"""
def remove_vehicle_service(vehicle_id: int, client_id: int) -> None:
    ensure_client_exists(client_id)
    try:
        deleted = delete_vehicle(vehicle_id, client_id)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    remove_vehicle_photo(str(deleted.get("photo_path")) if deleted.get("photo_path") else None)


# =========================================================
# CONTROLADORES HTTP DE VEHICULOS
# En esta seccion estan los endpoints principales del modulo vehiculos.
# Aqui vas a encontrar:
# - POST para registrar vehiculo
# - GET para listar vehiculos por cliente
# - PUT para editar vehiculo
# - DELETE para eliminar vehiculo
# Todos estos controladores trabajan con client_id y pueden manejar foto.
# =========================================================
@router.post(
    f"{settings.api_prefix}/vehiculos",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de registro de vehiculo que crea un vehiculo para un cliente.
def register_vehicle(
    client_id: int = Form(ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
) -> VehicleResponse:
    return register_vehicle_service(
        client_id=client_id,
        brand=brand,
        model=model,
        year=year,
        plate=plate,
        color=color,
        is_primary=is_primary,
        photo=photo,
    )


@router.get(f"{settings.api_prefix}/vehiculos", response_model=list[VehicleResponse])
# Aqui esta el controlador GET de listado de vehiculos que obtiene los vehiculos de un cliente.
def get_vehicles(client_id: int = Query(ge=1)) -> list[VehicleResponse]:
    return get_vehicles_service(client_id)


@router.put(f"{settings.api_prefix}/vehiculos/{{vehicle_id}}", response_model=VehicleResponse)
# Aqui esta el controlador PUT de edicion de vehiculo que actualiza los datos y la foto del vehiculo.
def edit_vehicle(
    vehicle_id: int,
    client_id: int = Form(ge=1),
    brand: str = Form(min_length=1, max_length=120),
    model: str = Form(min_length=1, max_length=120),
    year: int = Form(ge=1900, le=2100),
    plate: str = Form(min_length=3, max_length=40),
    color: str = Form(min_length=2, max_length=80),
    is_primary: bool = Form(default=False),
    photo: UploadFile | None = File(default=None),
) -> VehicleResponse:
    return edit_vehicle_service(
        vehicle_id=vehicle_id,
        client_id=client_id,
        brand=brand,
        model=model,
        year=year,
        plate=plate,
        color=color,
        is_primary=is_primary,
        photo=photo,
    )


@router.delete(f"{settings.api_prefix}/vehiculos/{{vehicle_id}}", status_code=status.HTTP_204_NO_CONTENT)
# Aqui esta el controlador DELETE de eliminacion de vehiculo que borra un vehiculo del cliente.
def remove_vehicle(vehicle_id: int, client_id: int = Query(ge=1)) -> None:
    remove_vehicle_service(vehicle_id, client_id)
