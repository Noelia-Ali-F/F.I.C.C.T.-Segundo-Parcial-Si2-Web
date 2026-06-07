from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import (
    list_active_device_fcm_tokens,
    list_device_fcm_tokens,
    list_device_fcm_tokens_default,
    upsert_device_fcm_token,
)
from app.tenant_context import get_tenant
from app.utils import (
    TokenPayload,
    firebase_push_is_ready,
    get_current_user,
    normalize_role,
    send_push_to_device_token,
)

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
logger = logging.getLogger(__name__)


class DeviceFcmTokenCreate(BaseModel):
    user_id: int = Field(ge=0)
    fcm_token: str = Field(min_length=20, max_length=4096)
    platform: str = Field(default="android", pattern="^(android|ios|web)$")
    is_active: bool = True


class DeviceFcmTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int | None = None
    tenant_slug: str | None = None
    user_id: int
    role: str | None = None
    sucursal_id: int | None = None
    fcm_token: str
    platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None = None


class DeviceTestPushRequest(BaseModel):
    type: str = Field(default="test_push", min_length=1, max_length=80)
    title: str = Field(default="Prueba push", min_length=1, max_length=160)
    body: str = Field(default="Push temporal de desarrollo", min_length=1, max_length=500)
    delivery_mode: str = Field(default="auto", pattern="^(auto|data_only|generic_notification)$")
    tenant_id: int | None = Field(default=None, ge=1)
    tenant_slug: str | None = Field(default=None, min_length=1, max_length=120)
    user_id: int | None = Field(default=None, ge=1)
    emergency_id: int | None = Field(default=None, ge=1)
    quotation_request_id: int | None = Field(default=None, ge=1)
    status: str | None = Field(default=None, min_length=1, max_length=80)
    status_label: str | None = Field(default=None, min_length=1, max_length=160)
    role: str | None = Field(default=None, min_length=1, max_length=80)


class DeviceTestPushResponse(BaseModel):
    success: bool
    message_id: str
    token_id: int
    token_preview: str
    payload_sent: dict[str, object]
    diagnostics: dict[str, object] | None = None


"""
Aqui esta la logica de registro de dispositivo que guarda
o actualiza el token FCM para el envio de notificaciones push.
"""
def _build_device_scope(current_user: TokenPayload) -> dict[str, object]:
    normalized_role = normalize_role(current_user.role)
    if current_user.is_tenant_user:
        return {
            "tenant_id": current_user.tenant_id,
            "tenant_slug": current_user.tenant_slug,
            "user_id": current_user.user_id,
            "role": normalized_role,
            "sucursal_id": current_user.sucursal_id,
        }
    return {
        "tenant_id": None,
        "tenant_slug": None,
        "user_id": current_user.user_id,
        "role": normalized_role,
        "sucursal_id": None,
    }


def register_device_token_service(payload: DeviceFcmTokenCreate, current_user: TokenPayload) -> DeviceFcmTokenResponse:
    if payload.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="USER_ID_TOKEN_MISMATCH")
    scope = _build_device_scope(current_user)
    try:
        device = upsert_device_fcm_token(
            {
                **scope,
                "fcm_token": payload.fcm_token.strip(),
                "platform": payload.platform,
                "is_active": payload.is_active,
            }
        )
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TOKEN_FCM_NO_ENCONTRADO_PARA_ESTE_CONTEXTO")
    return DeviceFcmTokenResponse.model_validate(device)


def _preview_token(token: str) -> str:
    compact_token = token.strip()
    if len(compact_token) <= 12:
        return compact_token
    return f"{compact_token[:8]}...{compact_token[-7:]}"


def _stringify_payload_data(payload: DeviceTestPushRequest) -> dict[str, str]:
    raw_items = {
        "type": payload.type,
        "delivery_mode": payload.delivery_mode,
        "tenant_id": payload.tenant_id,
        "tenant_slug": payload.tenant_slug,
        "user_id": payload.user_id,
        "emergency_id": payload.emergency_id,
        "quotation_request_id": payload.quotation_request_id,
        "status": payload.status,
        "status_label": payload.status_label,
        "role": payload.role,
    }
    return {key: str(value) for key, value in raw_items.items() if value is not None}


def _prefer_visible_notification(payload: DeviceTestPushRequest) -> bool:
    return payload.delivery_mode == "generic_notification"


def _resolve_test_push_token_lookup(current_user: TokenPayload) -> tuple[list[dict[str, object]], dict[str, object]]:
    tenant = get_tenant()
    scope = _build_device_scope(current_user)
    current_tokens_all = list_device_fcm_tokens(**scope)
    current_tokens_active = list_active_device_fcm_tokens(**scope)
    normalized_role = str(scope["role"])
    is_tenant_scoped_user = current_user.tenant_id is not None

    diagnostics: dict[str, object] = {
        "lookup_query": (
            "SELECT id, tenant_id, tenant_slug, user_id, role, sucursal_id, fcm_token, platform, is_active, created_at, updated_at, last_seen_at "
            "FROM device_fcm_tokens "
            "WHERE user_id = :user_id AND role = :role AND tenant_id/tenant_slug/sucursal_id coinciden con el JWT AND is_active = TRUE "
            "ORDER BY updated_at DESC, id DESC"
        ),
        "lookup_scope": scope,
        "current_engine_scope": "tenant" if tenant else "default",
        "current_engine_tenant_slug": tenant.get("slug") if tenant else None,
        "tokens_found_before_is_active_filter": len(current_tokens_all),
        "tokens_found_after_is_active_filter": len(current_tokens_active),
        "fallback_default_tokens_before_is_active_filter": 0,
        "fallback_default_tokens_after_is_active_filter": 0,
        "selected_source": "saas_master",
        "fallback_default_skipped_reason": None,
    }

    if current_tokens_active:
        return current_tokens_active, diagnostics

    if current_tokens_all or is_tenant_scoped_user:
        diagnostics["selected_source"] = "saas_master"
        diagnostics["fallback_default_skipped_reason"] = (
            "saas_master_has_only_inactive_tokens"
            if current_tokens_all
            else "tenant_scope_never_uses_default_engine_fallback"
        )
        return current_tokens_active, diagnostics

    if normalized_role != "SUPERADMIN_GLOBAL":
        diagnostics["fallback_default_skipped_reason"] = "default_engine_fallback_restricted_to_superadmin_global_legacy"
        return current_tokens_active, diagnostics

    default_tokens_all = list_device_fcm_tokens_default(current_user.user_id)
    diagnostics["fallback_default_tokens_before_is_active_filter"] = len(default_tokens_all)
    default_tokens_active = [token for token in default_tokens_all if bool(token.get("is_active"))]
    diagnostics["fallback_default_tokens_after_is_active_filter"] = len(default_tokens_active)
    if default_tokens_active:
        diagnostics["selected_source"] = "default_engine_fallback"
        return default_tokens_active, diagnostics
    return current_tokens_active, diagnostics


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
def register_device_fcm_token(
    payload: DeviceFcmTokenCreate,
    current_user: TokenPayload = Depends(get_current_user),
) -> DeviceFcmTokenResponse:
    return register_device_token_service(payload, current_user)


@router.post(
    f"{settings.api_prefix}/devices/test-push",
    response_model=DeviceTestPushResponse,
    status_code=status.HTTP_200_OK,
)
def send_test_push_to_authenticated_device(
    payload: DeviceTestPushRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> DeviceTestPushResponse:
    if settings.app_env.strip().lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TEST_PUSH_SOLO_DISPONIBLE_EN_DEVELOPMENT",
        )

    ready, error_detail = firebase_push_is_ready()
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_detail or "Firebase Admin SDK no está disponible",
        )

    try:
        devices, lookup_diagnostics = _resolve_test_push_token_lookup(current_user)
    except OperationalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc

    diagnostics = {
        "current_user": {
            "user_id": current_user.user_id,
            "tenant_id": current_user.tenant_id,
            "tenant_slug": current_user.tenant_slug,
            "role": current_user.role,
            "sucursal_id": current_user.sucursal_id,
        },
        **lookup_diagnostics,
    }

    if not devices:
        logger.warning(
            "DEV test-push token lookup empty user_id=%s tenant_id=%s tenant_slug=%s role=%s diagnostics=%s",
            current_user.user_id,
            current_user.tenant_id,
            current_user.tenant_slug,
            current_user.role,
            diagnostics,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TOKEN_FCM_ACTIVO_NO_ENCONTRADO",
                "diagnostics": diagnostics,
            },
        )

    selected_device = devices[0]
    token = str(selected_device.get("fcm_token", "")).strip()
    token_id = int(selected_device["id"])
    token_preview = _preview_token(token)
    diagnostics["token_id_selected"] = token_id
    diagnostics["token_preview"] = token_preview
    if not token:
        logger.warning(
            "DEV test-push selected empty token user_id=%s token_id=%s diagnostics=%s",
            current_user.user_id,
            token_id,
            diagnostics,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TOKEN_FCM_ACTIVO_NO_ENCONTRADO",
                "diagnostics": diagnostics,
            },
        )

    data = _stringify_payload_data(payload)
    data.pop("delivery_mode", None)
    payload_sent = {
        "requested_notification": {
            "title": payload.title,
            "body": payload.body,
        },
        "data": data,
        "target": {
            "jwt_user_id": current_user.user_id,
            "jwt_tenant_id": current_user.tenant_id,
            "jwt_tenant_slug": current_user.tenant_slug,
            "jwt_role": current_user.role,
            "jwt_sucursal_id": current_user.sucursal_id,
        },
    }

    logger.warning(
        "DEV test-push requested by user_id=%s tenant_id=%s tenant_slug=%s role=%s sucursal_id=%s token_id=%s payload_user_id=%s payload_tenant_id=%s",
        current_user.user_id,
        current_user.tenant_id,
        current_user.tenant_slug,
        current_user.role,
        current_user.sucursal_id,
        token_id,
        payload.user_id,
        payload.tenant_id,
    )
    logger.warning("DEV test-push diagnostics user_id=%s details=%s", current_user.user_id, diagnostics)

    try:
        message_id, delivery = send_push_to_device_token(
            token=token,
            title=payload.title,
            body=payload.body,
            data=data,
            prefer_visible_notification=_prefer_visible_notification(payload),
        )
    except Exception as exc:
        logger.exception(
            "DEV test-push failed for user_id=%s token_id=%s",
            current_user.user_id,
            token_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NO_SE_PUDO_ENVIAR_PUSH_FCM",
        ) from exc

    payload_sent["delivery"] = {
        "mode": delivery["mode"],
        "sensitive": delivery["sensitive"],
        "notification": (
            {
                "title": delivery["notification_title"],
                "body": delivery["notification_body"],
            }
            if delivery["notification_title"] is not None and delivery["notification_body"] is not None
            else None
        ),
    }

    logger.warning(
        "DEV test-push sent successfully user_id=%s token_id=%s message_id=%s",
        current_user.user_id,
        token_id,
        message_id,
    )

    return DeviceTestPushResponse(
        success=True,
        message_id=message_id,
        token_id=token_id,
        token_preview=token_preview,
        payload_sent=payload_sent,
        diagnostics=diagnostics,
    )
