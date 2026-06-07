from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import HTTPException, WebSocket, status

from app.realtime_types import RealtimeEmitEvent, RealtimeEnvelope
from app.saas_master import get_tenant_by_slug_any
from app.utils import (
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    TokenPayload,
    _payload_to_token,
    decode_access_token,
    get_effective_technician_id,
    normalize_role,
)

logger = logging.getLogger(__name__)

SUPPORTED_REALTIME_ROLES = {
    ROLE_SUPERADMIN_GLOBAL,
    ROLE_SUPERADMIN_TENANT,
    ROLE_ADMIN_SUCURSAL,
    ROLE_TECNICO,
    ROLE_CLIENTE,
}


@dataclass(slots=True)
class RealtimeConnection:
    connection_id: str
    websocket: WebSocket
    user: TokenPayload
    channels: list[str]
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def public_snapshot(self) -> dict[str, object]:
        return {
            "connection_id": self.connection_id,
            "user_id": self.user.user_id,
            "technician_id": self.user.technician_id,
            "tenant_id": self.user.tenant_id,
            "tenant_slug": self.user.tenant_slug,
            "role": self.user.role,
            "sucursal_id": self.user.sucursal_id,
            "channels": list(self.channels),
            "connected_at": self.connected_at.isoformat(),
        }


def derive_realtime_channels(current_user: TokenPayload) -> list[str]:
    role = normalize_role(current_user.role)
    channels: list[str] = []

    if role == ROLE_SUPERADMIN_GLOBAL:
        return ["global:superadmin"]

    if current_user.tenant_id is None:
        return []

    tenant_prefix = f"tenant:{current_user.tenant_id}"
    channels.append(f"{tenant_prefix}:user:{current_user.user_id}")

    if role == ROLE_SUPERADMIN_TENANT:
        channels.insert(0, tenant_prefix)
    elif role == ROLE_ADMIN_SUCURSAL and current_user.sucursal_id is not None:
        channels.insert(0, f"{tenant_prefix}:sucursal:{current_user.sucursal_id}")
    elif role == ROLE_TECNICO:
        technician_id = get_effective_technician_id(current_user)
        channels.insert(0, f"{tenant_prefix}:tecnico:{technician_id}")
    elif role == ROLE_CLIENTE:
        channels.insert(0, f"{tenant_prefix}:cliente:{current_user.user_id}")

    return channels


def resolve_ws_token_payload(raw_token: str) -> TokenPayload:
    try:
        payload = decode_access_token(raw_token)
    except pyjwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado") from exc
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    role = normalize_role(str(payload.get("role") or payload.get("rol") or ""))
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_SIN_TENANT")
    if role not in SUPPORTED_REALTIME_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="REALTIME_ROLE_NO_SOPORTADO")

    current_user = _payload_to_token(payload)

    if current_user.is_tenant_user:
        tenant = get_tenant_by_slug_any(str(current_user.tenant_slug))
        if not tenant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_NO_ENCONTRADO")
        if int(tenant["id"]) != int(current_user.tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_TOKEN_MISMATCH")
        if tenant.get("estado") != "activo":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="TENANT_INACTIVO")

    return current_user


class RealtimeConnectionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: dict[str, RealtimeConnection] = {}
        self._channels: dict[str, set[str]] = defaultdict(set)
        self._sequence = 0

    async def connect(self, websocket: WebSocket, current_user: TokenPayload) -> RealtimeConnection:
        await websocket.accept()
        async with self._lock:
            self._sequence += 1
            connection_id = f"ws-{self._sequence}"
            channels = derive_realtime_channels(current_user)
            connection = RealtimeConnection(
                connection_id=connection_id,
                websocket=websocket,
                user=current_user,
                channels=channels,
            )
            self._connections[connection_id] = connection
            for channel in channels:
                self._channels[channel].add(connection_id)
        logger.info(
            "WS connected connection_id=%s user_id=%s tenant_id=%s role=%s channels=%s",
            connection.connection_id,
            current_user.user_id,
            current_user.tenant_id,
            current_user.role,
            channels,
        )
        return connection

    async def disconnect(self, connection_id: str) -> None:
        async with self._lock:
            connection = self._connections.pop(connection_id, None)
            if not connection:
                return
            for channel in connection.channels:
                members = self._channels.get(channel)
                if members is None:
                    continue
                members.discard(connection_id)
                if not members:
                    self._channels.pop(channel, None)
        logger.info("WS disconnected connection_id=%s", connection_id)

    async def list_active_connections(self) -> list[dict[str, object]]:
        async with self._lock:
            return [connection.public_snapshot() for connection in self._connections.values()]

    async def send_to_connection(self, connection_id: str, message: dict[str, object]) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)
        if not connection:
            return False
        try:
            await connection.websocket.send_json(message)
            return True
        except Exception:
            logger.exception("WS send_to_connection failed connection_id=%s", connection_id)
            await self.disconnect(connection_id)
            return False

    async def send_to_channel(self, channel: str, message: dict[str, object]) -> int:
        async with self._lock:
            connection_ids = list(self._channels.get(channel, set()))
        delivered = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                delivered += 1
        return delivered

    async def emit_event(self, event: RealtimeEmitEvent) -> dict[str, object]:
        target_channel = self._resolve_event_channel(event)
        envelope = RealtimeEnvelope(
            **event.model_dump(),
            delivery_channel=target_channel,
        )
        delivered = await self.send_to_channel(target_channel, envelope.model_dump(mode="json"))
        return {
            "delivery_channel": target_channel,
            "delivered_connections": delivered,
            "event": envelope.model_dump(mode="json"),
        }

    def _resolve_event_channel(self, event: RealtimeEmitEvent) -> str:
        normalized_role = normalize_role(event.role_target)
        if normalized_role == ROLE_SUPERADMIN_GLOBAL or (
            event.tenant_id is None and normalized_role == ROLE_SUPERADMIN_GLOBAL
        ):
            return "global:superadmin"

        if event.tenant_id is None:
            raise ValueError("tenant_id es requerido para eventos no globales")

        tenant_prefix = f"tenant:{event.tenant_id}"
        if normalized_role == ROLE_CLIENTE and event.user_id is not None:
            return f"{tenant_prefix}:cliente:{event.user_id}"
        if normalized_role == ROLE_TECNICO and event.user_id is not None:
            return f"{tenant_prefix}:tecnico:{event.user_id}"
        if normalized_role == ROLE_ADMIN_SUCURSAL and event.sucursal_id is not None:
            return f"{tenant_prefix}:sucursal:{event.sucursal_id}"
        if event.user_id is not None:
            return f"{tenant_prefix}:user:{event.user_id}"
        if event.sucursal_id is not None:
            return f"{tenant_prefix}:sucursal:{event.sucursal_id}"
        return tenant_prefix


_manager = RealtimeConnectionManager()


def get_realtime_manager() -> RealtimeConnectionManager:
    return _manager


async def emit_realtime_event(event: RealtimeEmitEvent | dict[str, object]) -> dict[str, object]:
    normalized_event = event if isinstance(event, RealtimeEmitEvent) else RealtimeEmitEvent.model_validate(event)
    return await _manager.emit_event(normalized_event)


async def emit_realtime_events(events: list[RealtimeEmitEvent | dict[str, object]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for event in events:
        results.append(await emit_realtime_event(event))
    return results


def allowed_test_emit_roles() -> set[str]:
    return set(SUPPORTED_REALTIME_ROLES)
