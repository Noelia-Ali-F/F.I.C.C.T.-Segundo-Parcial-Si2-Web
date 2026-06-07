from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RealtimeEmitEvent(BaseModel):
    type: str = Field(min_length=1, max_length=120)
    tenant_id: int | None = Field(default=None, ge=1)
    tenant_slug: str | None = Field(default=None, min_length=1, max_length=100)
    sucursal_id: int | None = Field(default=None, ge=1)
    user_id: int | None = Field(default=None, ge=0)
    role_target: str | None = Field(default=None, min_length=1, max_length=80)
    entity_type: str | None = Field(default=None, min_length=1, max_length=80)
    entity_id: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class RealtimeEnvelope(RealtimeEmitEvent):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivery_channel: str | None = None


class RealtimeTestEmitRequest(RealtimeEmitEvent):
    pass
