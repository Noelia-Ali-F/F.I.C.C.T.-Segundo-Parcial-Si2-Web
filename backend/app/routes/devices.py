from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import upsert_device_fcm_token
from app.utils import ensure_client_exists

# =========================================================
# ARCHIVO DE RUTAS DE DISPOSITIVOS
# Aqui esta todo lo relacionado con el registro del dispositivo del usuario.
# Este archivo contiene:
# - modelo de entrada del token FCM
# - modelo de respuesta del dispositivo
# - logica para guardar o actualizar el token del dispositivo
# - controlador HTTP para notificaciones push
# Palabras clave para buscar despues:
# DEVICES, FCM TOKEN, NOTIFICACIONES, DISPOSITIVO, PUSH
# =========================================================
router = APIRouter(tags=["devices"])


class DeviceFcmTokenCreate(BaseModel):
    user_id: int = Field(ge=1)
    fcm_token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern="^(android|ios|web)$")


class DeviceFcmTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    fcm_token: str
    platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


"""
Aqui esta la logica de registro de dispositivo que guarda
o actualiza el token FCM para el envio de notificaciones push.
"""
def register_device_token_service(payload: DeviceFcmTokenCreate) -> DeviceFcmTokenResponse:
    ensure_client_exists(payload.user_id)
    try:
        device = upsert_device_fcm_token(
            {
                "user_id": payload.user_id,
                "fcm_token": payload.fcm_token.strip(),
                "platform": payload.platform,
            }
        )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return DeviceFcmTokenResponse.model_validate(device)


# =========================================================
# CONTROLADORES HTTP DE DISPOSITIVOS
# En esta seccion esta el endpoint que usa el frontend para registrar
# el token del dispositivo y permitir el envio de notificaciones push.
# Aqui esta el controlador POST principal de este modulo.
# =========================================================
@router.post(
    f"{settings.api_prefix}/devices/fcm-token",
    response_model=DeviceFcmTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
# Aqui esta el controlador POST de dispositivo que registra o actualiza el token FCM para notificaciones.
def register_device_fcm_token(payload: DeviceFcmTokenCreate) -> DeviceFcmTokenResponse:
    return register_device_token_service(payload)
