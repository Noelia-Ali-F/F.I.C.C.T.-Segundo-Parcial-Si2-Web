from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app.realtime import (
    allowed_test_emit_roles,
    emit_realtime_event,
    get_realtime_manager,
    resolve_ws_token_payload,
)
from app.realtime_types import RealtimeTestEmitRequest
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    ROLE_SUPERADMIN_GLOBAL,
    TokenPayload,
    get_current_user,
    normalize_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])


@router.websocket(f"{settings.api_prefix}/ws")
async def realtime_websocket_endpoint(websocket: WebSocket) -> None:
    raw_token = websocket.query_params.get("token", "").strip()
    if not raw_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="TOKEN_REQUERIDO")
        return

    try:
        current_user = resolve_ws_token_payload(raw_token)
    except HTTPException as exc:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc.detail),
        )
        return

    manager = get_realtime_manager()
    connection = await manager.connect(websocket, current_user)

    try:
        await websocket.send_json(
            {
                "type": "ws_connected",
                "user_id": current_user.user_id,
                "technician_id": current_user.technician_id,
                "tenant_id": current_user.tenant_id,
                "tenant_slug": current_user.tenant_slug,
                "role": current_user.role,
                "sucursal_id": current_user.sucursal_id,
                "channels": list(connection.channels),
            }
        )

        while True:
            payload = await websocket.receive_json()
            message_type = str(payload.get("type") or "").strip()

            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json(
                {
                    "type": "ws_error",
                    "detail": "MENSAJE_NO_SOPORTADO",
                }
            )
    except WebSocketDisconnect:
        logger.info("WS client disconnected connection_id=%s", connection.connection_id)
    except Exception:
        logger.exception("WS connection failed connection_id=%s", connection.connection_id)
    finally:
        await manager.disconnect(connection.connection_id)


@router.post(f"{settings.api_prefix}/realtime/test-emit")
async def test_emit_realtime_event(
    payload: RealtimeTestEmitRequest,
    current_user: TokenPayload = Depends(get_current_user),
) -> dict[str, object]:
    if settings.app_env.lower() != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")

    role = normalize_role(current_user.role)
    if role not in allowed_test_emit_roles():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_TENANT")

    event = payload.model_copy(deep=True)

    if current_user.is_tenant_user:
        event.tenant_id = current_user.tenant_id
        event.tenant_slug = current_user.tenant_slug
        if role == ROLE_ADMIN_SUCURSAL:
            if event.sucursal_id is not None and event.sucursal_id != current_user.sucursal_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_SUCURSAL")
            event.sucursal_id = current_user.sucursal_id
        if normalize_role(event.role_target) == ROLE_SUPERADMIN_GLOBAL:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MODO_SOPORTE_REQUERIDO")
    elif role == ROLE_SUPERADMIN_GLOBAL:
        if normalize_role(event.role_target) == ROLE_SUPERADMIN_GLOBAL:
            event.tenant_id = None
            event.tenant_slug = None

    try:
        result = await emit_realtime_event(event)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "success": True,
        **result,
    }
