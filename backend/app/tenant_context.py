"""
Tenant context: almacena el engine activo para el request actual.

ContextVar propaga el valor dentro de la misma coroutine y a threads
lanzados por asyncio (run_in_executor preserva el contexto desde Python 3.7).
Esto permite que las funciones síncronas de db.py usen automáticamente
el engine correcto sin recibir parámetros extra.
"""
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

_current_engine: ContextVar["Engine | None"] = ContextVar(
    "current_tenant_engine", default=None
)
_current_tenant: ContextVar[dict | None] = ContextVar(
    "current_tenant_metadata", default=None
)


def get_engine() -> "Engine":
    """Devuelve el engine del tenant activo o el engine por defecto (diagramador)."""
    eng = _current_engine.get()
    if eng is not None:
        return eng
    from app.db import _default_engine
    return _default_engine


def set_engine(engine: "Engine") -> None:
    _current_engine.set(engine)


def set_tenant(tenant: dict | None) -> None:
    _current_tenant.set(tenant)


def get_tenant() -> dict | None:
    return _current_tenant.get()


def set_context(engine: "Engine", tenant: dict) -> None:
    _current_engine.set(engine)
    _current_tenant.set(tenant)


def clear_engine() -> None:
    _current_engine.set(None)
    _current_tenant.set(None)
