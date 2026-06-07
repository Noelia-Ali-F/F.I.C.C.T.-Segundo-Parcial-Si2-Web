"""
TenantConnectionManager: gestión de engines SQLAlchemy por tenant.

Cada tenant tiene su propia base de datos PostgreSQL. Este módulo:
  - Crea bases de datos dinámicamente (requiere AUTOCOMMIT).
  - Cachea engines por nombre de BD (evita recrearlos en cada request).
  - Ejecuta el schema completo en BDs recién creadas.
"""
import logging
import re
from threading import Lock

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

# Cache de engines: { database_name -> Engine }
_engines: dict[str, Engine] = {}
_engines_lock = Lock()


# =============================================================================
# Utilidad interna
# =============================================================================

def _validate_db_name(name: str) -> str:
    """Valida que el nombre de BD sea seguro (solo letras minúsculas, dígitos, _)."""
    clean = re.sub(r"[^a-z0-9_]", "", name.lower())
    if not clean or len(clean) > 63:
        raise ValueError(f"Nombre de base de datos inválido: '{name}'")
    return clean


# =============================================================================
# API pública
# =============================================================================

def get_tenant_engine(tenant_info: dict) -> Engine:
    """
    Devuelve el engine cacheado para el tenant.
    Si no existe en caché, lo crea con los parámetros de conexión del tenant
    y aplica el schema/migraciones ligeras del tenant al primer uso.

    tenant_info debe tener: database_name, database_host, database_port,
                            database_user, database_password
    """
    db_name = str(tenant_info["database_name"])
    if db_name not in _engines:
        with _engines_lock:
            if db_name not in _engines:
                url = (
                    f"postgresql+psycopg://{tenant_info['database_user']}"
                    f":{tenant_info['database_password']}"
                    f"@{tenant_info['database_host']}"
                    f":{tenant_info['database_port']}"
                    f"/{db_name}"
                )
                _engines[db_name] = create_engine(
                    url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={"connect_timeout": settings.postgres_connect_timeout},
                )
                from app.tenant_schema import (
                    TENANT_SCHEMA_UPGRADE_STATEMENTS,
                    TENANT_TABLES_IN_ORDER,
                )
                with _engines[db_name].begin() as conn:
                    for stmt in TENANT_TABLES_IN_ORDER:
                        conn.execute(stmt)
                    for stmt in TENANT_SCHEMA_UPGRADE_STATEMENTS:
                        conn.execute(stmt)
                logger.info("Engine creado para tenant BD: %s", db_name)
    return _engines[db_name]


def create_tenant_database(db_name: str) -> None:
    """
    Crea una base de datos PostgreSQL nueva.

    Requiere conectarse a la BD de mantenimiento 'postgres' en modo AUTOCOMMIT
    porque CREATE DATABASE no puede ejecutarse dentro de una transacción.
    """
    safe_name = _validate_db_name(db_name)
    admin_engine = create_engine(
        settings.postgres_maintenance_url,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": safe_name},
            ).first()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{safe_name}"'))
                logger.info("Base de datos de tenant creada: %s", safe_name)
            else:
                logger.info("Base de datos de tenant ya existe: %s", safe_name)
    finally:
        admin_engine.dispose()


def init_tenant_schema(tenant_info: dict) -> None:
    """
    Ejecuta el schema completo (CREATE TABLE IF NOT EXISTS) en la BD del tenant.
    Llama a este método justo después de crear la BD.
    """
    from app.tenant_schema import TENANT_TABLES_IN_ORDER

    engine = get_tenant_engine(tenant_info)
    with engine.begin() as conn:
        for stmt in TENANT_TABLES_IN_ORDER:
            conn.execute(stmt)
    logger.info(
        "Schema inicializado en tenant BD: %s", tenant_info["database_name"]
    )


def evict_tenant_engine(db_name: str) -> None:
    """Elimina el engine del caché (útil si cambió la contraseña de BD)."""
    with _engines_lock:
        engine = _engines.pop(db_name, None)
    if engine:
        engine.dispose()
        logger.info("Engine eviccionado del caché: %s", db_name)


def drop_tenant_database(db_name: str) -> None:
    """Elimina una base de datos de tenant. Uso exclusivo para rollback controlado."""
    safe_name = _validate_db_name(db_name)
    evict_tenant_engine(safe_name)
    admin_engine = create_engine(
        settings.postgres_maintenance_url,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :name AND pid <> pg_backend_pid()
                    """
                ),
                {"name": safe_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{safe_name}"'))
            logger.info("Base de datos de tenant eliminada: %s", safe_name)
    finally:
        admin_engine.dispose()
