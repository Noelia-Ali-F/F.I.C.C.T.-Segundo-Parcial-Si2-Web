"""
saas_master: base de datos maestra del SaaS.

Tablas:
  - saas_tenants     → metadata y conexión de cada empresa registrada
  - planes           → planes de suscripción
  - suscripciones    → qué tenant tiene qué plan y hasta cuándo
  - auditoria_saas   → log de eventos globales

La BD 'saas_master' es creada automáticamente en el startup de la app.
"""
import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

# Engine apuntando a saas_master (se crea en init_saas_master())
_master_engine: Engine | None = None


def get_master_engine() -> Engine:
    global _master_engine
    if _master_engine is None:
        _master_engine = create_engine(
            settings.saas_master_url,
            pool_pre_ping=True,
            pool_size=5,
            connect_args={"connect_timeout": settings.postgres_connect_timeout},
        )
    return _master_engine


# =============================================================================
# DDL: tablas en saas_master
# =============================================================================

_CREATE_PLANES_SQL = text("""
    CREATE TABLE IF NOT EXISTS planes (
        id BIGSERIAL PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        descripcion TEXT,
        precio_mensual NUMERIC(12, 2) NOT NULL DEFAULT 0,
        limite_sucursales INTEGER NOT NULL DEFAULT 1,
        limite_tecnicos INTEGER NOT NULL DEFAULT 10,
        limite_administradores INTEGER NOT NULL DEFAULT 2,
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

_CREATE_SAAS_TENANTS_SQL = text("""
    CREATE TABLE IF NOT EXISTS saas_tenants (
        id BIGSERIAL PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        slug VARCHAR(100) NOT NULL UNIQUE,
        razon_social VARCHAR(300),
        nit VARCHAR(50),
        correo VARCHAR(200) NOT NULL UNIQUE,
        telefono VARCHAR(50),
        direccion_principal TEXT,
        zona VARCHAR(120),
        ciudad VARCHAR(120) NOT NULL DEFAULT 'Santa Cruz',
        latitud DOUBLE PRECISION,
        longitud DOUBLE PRECISION,
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        database_name VARCHAR(200) NOT NULL UNIQUE,
        database_host VARCHAR(200) NOT NULL DEFAULT 'db',
        database_port INTEGER NOT NULL DEFAULT 5432,
        database_user VARCHAR(200) NOT NULL,
        database_password VARCHAR(500) NOT NULL,
        plan_id BIGINT REFERENCES planes(id) ON DELETE SET NULL,
        fecha_expiracion TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

_CREATE_SUSCRIPCIONES_SQL = text("""
    CREATE TABLE IF NOT EXISTS suscripciones (
        id BIGSERIAL PRIMARY KEY,
        tenant_id BIGINT NOT NULL REFERENCES saas_tenants(id) ON DELETE CASCADE,
        plan_id BIGINT NOT NULL REFERENCES planes(id) ON DELETE RESTRICT,
        fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        fecha_fin TIMESTAMPTZ,
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        monto NUMERIC(12, 2),
        metodo_pago VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

_CREATE_AUDITORIA_SAAS_SQL = text("""
    CREATE TABLE IF NOT EXISTS auditoria_saas (
        id BIGSERIAL PRIMARY KEY,
        tenant_id BIGINT REFERENCES saas_tenants(id) ON DELETE SET NULL,
        usuario_id BIGINT,
        accion VARCHAR(200) NOT NULL,
        descripcion TEXT,
        ip VARCHAR(50),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

_CREATE_DEVICE_FCM_TOKENS_SQL = text("""
    CREATE TABLE IF NOT EXISTS device_fcm_tokens (
        id BIGSERIAL PRIMARY KEY,
        tenant_id BIGINT REFERENCES saas_tenants(id) ON DELETE SET NULL,
        tenant_slug VARCHAR(100),
        user_id BIGINT NOT NULL,
        role VARCHAR(80) NOT NULL,
        sucursal_id BIGINT,
        fcm_token TEXT NOT NULL UNIQUE,
        platform VARCHAR(40) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ
    )
""")

_SEED_PLANES_SQL = text("""
    INSERT INTO planes (nombre, descripcion, precio_mensual, limite_sucursales, limite_tecnicos, limite_administradores)
    SELECT * FROM (VALUES
        ('Básico',    'Plan inicial para talleres pequeños',     0,    1,  5,  1),
        ('Estándar',  'Plan para talleres con varias sucursales', 199,  3, 20,  3),
        ('Premium',   'Plan completo para redes de talleres',    499, 10, 100, 10)
    ) AS v(nombre, descripcion, precio_mensual, limite_sucursales, limite_tecnicos, limite_administradores)
    WHERE NOT EXISTS (SELECT 1 FROM planes LIMIT 1)
""")


# =============================================================================
# Inicialización
# =============================================================================

def init_saas_master() -> None:
    """
    Crea la BD saas_master si no existe y levanta las tablas.
    Se llama en el startup de FastAPI.
    """
    from app.tenant_manager import _validate_db_name

    saas_db = settings.saas_master_db

    # 1. Crear saas_master si no existe (requiere AUTOCOMMIT)
    maintenance_engine = create_engine(
        settings.postgres_maintenance_url,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with maintenance_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": saas_db},
            ).first()
            if not exists:
                safe_name = _validate_db_name(saas_db)
                conn.execute(text(f'CREATE DATABASE "{safe_name}"'))
                logger.info("BD saas_master creada.")
    finally:
        maintenance_engine.dispose()

    # 2. Crear tablas en saas_master
    engine = get_master_engine()
    with engine.begin() as conn:
        conn.execute(_CREATE_PLANES_SQL)
        conn.execute(_CREATE_SAAS_TENANTS_SQL)
        conn.execute(_CREATE_SUSCRIPCIONES_SQL)
        conn.execute(_CREATE_AUDITORIA_SAAS_SQL)
        conn.execute(_CREATE_DEVICE_FCM_TOKENS_SQL)
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES saas_tenants(id) ON DELETE SET NULL"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS tenant_slug VARCHAR(100)"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS user_id BIGINT"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS role VARCHAR(80)"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS sucursal_id BIGINT"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS fcm_token TEXT"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS platform VARCHAR(40)"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        conn.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS device_fcm_tokens_fcm_token_key ON device_fcm_tokens (fcm_token)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_fcm_tokens_user_tenant_active ON device_fcm_tokens (user_id, tenant_id, role, is_active)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_fcm_tokens_slug_user_active ON device_fcm_tokens (tenant_slug, user_id, role, is_active)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_fcm_tokens_user_role_active ON device_fcm_tokens (user_id, role, is_active)"))
        # Insertar planes por defecto si la tabla está vacía
        conn.execute(_SEED_PLANES_SQL)
    logger.info("saas_master inicializado correctamente.")


# =============================================================================
# CRUD: saas_tenants
# =============================================================================

def get_tenant_by_slug(slug: str) -> dict | None:
    with get_master_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM saas_tenants WHERE slug = :slug AND estado = 'activo'"),
            {"slug": slug},
        ).mappings().first()
        return dict(row) if row else None


def get_tenant_by_slug_any(slug: str) -> dict | None:
    with get_master_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM saas_tenants WHERE slug = :slug"),
            {"slug": slug},
        ).mappings().first()
        return dict(row) if row else None


def get_tenant_by_id(tenant_id: int) -> dict | None:
    with get_master_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM saas_tenants WHERE id = :id"),
            {"id": tenant_id},
        ).mappings().first()
        return dict(row) if row else None


def get_tenant_by_correo(correo: str) -> dict | None:
    with get_master_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM saas_tenants WHERE correo = :correo"),
            {"correo": correo.lower().strip()},
        ).mappings().first()
        return dict(row) if row else None


def list_all_tenants() -> list[dict]:
    with get_master_engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT st.*, p.nombre AS plan_nombre
                FROM saas_tenants st
                LEFT JOIN planes p ON p.id = st.plan_id
                ORDER BY st.created_at DESC
            """)
        ).mappings().all()
        return [dict(r) for r in rows]


def create_saas_tenant(data: dict) -> dict:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO saas_tenants (
                    nombre, slug, razon_social, nit, correo, telefono,
                    direccion_principal, zona, ciudad, latitud, longitud,
                    database_name, database_host, database_port,
                    database_user, database_password, plan_id, estado
                ) VALUES (
                    :nombre, :slug, :razon_social, :nit, :correo, :telefono,
                    :direccion_principal, :zona, :ciudad, :latitud, :longitud,
                    :database_name, :database_host, :database_port,
                    :database_user, :database_password, :plan_id, 'activo'
                )
                RETURNING *
            """),
            data,
        ).mappings().first()
        return dict(row)


def delete_saas_tenant(tenant_id: int) -> bool:
    with get_master_engine().begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM saas_tenants WHERE id = :id RETURNING id"),
            {"id": tenant_id},
        ).first()
        return deleted is not None


def update_saas_tenant(tenant_id: int, data: dict) -> dict | None:
    fields = ", ".join(f"{k} = :{k}" for k in data if k != "id")
    if not fields:
        return get_tenant_by_id(tenant_id)
    data["id"] = tenant_id
    data["updated_at"] = "NOW()"
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text(f"""
                UPDATE saas_tenants
                SET {fields}, updated_at = NOW()
                WHERE id = :id
                RETURNING *
            """),
            data,
        ).mappings().first()
        return dict(row) if row else None


def toggle_tenant_estado(tenant_id: int, nuevo_estado: str) -> dict | None:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text("""
                UPDATE saas_tenants
                SET estado = :estado, updated_at = NOW()
                WHERE id = :id
                RETURNING *
            """),
            {"estado": nuevo_estado, "id": tenant_id},
        ).mappings().first()
        return dict(row) if row else None


# =============================================================================
# CRUD: planes
# =============================================================================

def list_planes(solo_activos: bool = True) -> list[dict]:
    where = "WHERE estado = 'activo'" if solo_activos else ""
    with get_master_engine().connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM planes {where} ORDER BY precio_mensual ASC")
        ).mappings().all()
        return [dict(r) for r in rows]


def get_plan_by_id(plan_id: int) -> dict | None:
    with get_master_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM planes WHERE id = :id"),
            {"id": plan_id},
        ).mappings().first()
        return dict(row) if row else None


def create_plan(data: dict) -> dict:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text("""
                INSERT INTO planes (nombre, descripcion, precio_mensual,
                    limite_sucursales, limite_tecnicos, limite_administradores)
                VALUES (:nombre, :descripcion, :precio_mensual,
                    :limite_sucursales, :limite_tecnicos, :limite_administradores)
                RETURNING *
            """),
            data,
        ).mappings().first()
        return dict(row)


def create_subscription(
    *,
    tenant_id: int,
    plan_id: int,
    monto: float | int | None = None,
    estado: str = "activo",
    metodo_pago: str | None = None,
) -> dict:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO suscripciones (tenant_id, plan_id, estado, monto, metodo_pago)
                VALUES (:tenant_id, :plan_id, :estado, :monto, :metodo_pago)
                RETURNING *
                """
            ),
            {
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "estado": estado,
                "monto": monto,
                "metodo_pago": metodo_pago,
            },
        ).mappings().first()
        return dict(row)


def register_device_fcm_token_global(data: dict) -> dict:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO device_fcm_tokens (
                    tenant_id, tenant_slug, user_id, role, sucursal_id,
                    fcm_token, platform, is_active, last_seen_at
                )
                VALUES (
                    :tenant_id, :tenant_slug, :user_id, :role, :sucursal_id,
                    :fcm_token, :platform, :is_active,
                    CASE WHEN :is_active THEN NOW() ELSE NULL END
                )
                ON CONFLICT (fcm_token) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    tenant_slug = EXCLUDED.tenant_slug,
                    user_id = EXCLUDED.user_id,
                    role = EXCLUDED.role,
                    sucursal_id = EXCLUDED.sucursal_id,
                    platform = EXCLUDED.platform,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW(),
                    last_seen_at = CASE
                        WHEN EXCLUDED.is_active THEN NOW()
                        ELSE device_fcm_tokens.last_seen_at
                    END
                RETURNING *
                """
            ),
            data,
        ).mappings().first()
    return dict(row)


def deactivate_device_fcm_token_global(data: dict) -> dict | None:
    with get_master_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE device_fcm_tokens
                SET is_active = FALSE,
                    platform = :platform,
                    updated_at = NOW()
                WHERE fcm_token = :fcm_token
                  AND user_id = :user_id
                  AND role = :role
                  AND (
                    (CAST(:tenant_id AS BIGINT) IS NULL AND tenant_id IS NULL)
                    OR tenant_id = CAST(:tenant_id AS BIGINT)
                  )
                  AND (
                    (CAST(:tenant_slug AS VARCHAR(100)) IS NULL AND tenant_slug IS NULL)
                    OR tenant_slug = CAST(:tenant_slug AS VARCHAR(100))
                  )
                  AND (
                    (CAST(:sucursal_id AS BIGINT) IS NULL AND sucursal_id IS NULL)
                    OR sucursal_id = CAST(:sucursal_id AS BIGINT)
                  )
                RETURNING *
                """
            ),
            data,
        ).mappings().first()
    return dict(row) if row else None


def list_device_fcm_tokens_global(
    *,
    user_id: int,
    role: str,
    tenant_id: int | None,
    tenant_slug: str | None,
    sucursal_id: int | None,
    only_active: bool,
) -> list[dict]:
    with get_master_engine().connect() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT id, tenant_id, tenant_slug, user_id, role, sucursal_id, fcm_token, platform,
                       is_active, created_at, updated_at, last_seen_at
                FROM device_fcm_tokens
                WHERE user_id = :user_id
                  AND role = :role
                  AND (
                    (CAST(:tenant_id AS BIGINT) IS NULL AND tenant_id IS NULL)
                    OR tenant_id = CAST(:tenant_id AS BIGINT)
                  )
                  AND (
                    (CAST(:tenant_slug AS VARCHAR(100)) IS NULL AND tenant_slug IS NULL)
                    OR tenant_slug = CAST(:tenant_slug AS VARCHAR(100))
                  )
                  AND (
                    (CAST(:sucursal_id AS BIGINT) IS NULL AND sucursal_id IS NULL)
                    OR sucursal_id = CAST(:sucursal_id AS BIGINT)
                  )
                  {"AND is_active = TRUE" if only_active else ""}
                ORDER BY updated_at DESC, id DESC
                """
            ),
            {
                "user_id": user_id,
                "role": role,
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "sucursal_id": sucursal_id,
            },
        ).mappings().all()
    return [dict(row) for row in rows]


# =============================================================================
# Auditoría
# =============================================================================

def registrar_auditoria(
    accion: str,
    *,
    tenant_id: int | None = None,
    usuario_id: int | None = None,
    descripcion: str | None = None,
    ip: str | None = None,
) -> None:
    try:
        with get_master_engine().begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO auditoria_saas (tenant_id, usuario_id, accion, descripcion, ip)
                    VALUES (:tenant_id, :usuario_id, :accion, :descripcion, :ip)
                """),
                {
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "accion": accion,
                    "descripcion": descripcion,
                    "ip": ip,
                },
            )
    except Exception:
        logger.exception("No se pudo registrar auditoría: %s", accion)


# =============================================================================
# Helper: generar slug único
# =============================================================================

def generate_unique_slug(nombre: str) -> str:
    """
    Genera un slug URL-friendly desde el nombre de la empresa.
    Si ya existe, agrega un sufijo numérico.
    """
    import unicodedata

    normalized = unicodedata.normalize("NFKD", nombre)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    slug_base = re.sub(r"[^a-z0-9]+", "_", without_accents.lower()).strip("_")
    slug_base = slug_base[:50] or "empresa"

    with get_master_engine().connect() as conn:
        # Buscar slugs que empiecen con slug_base
        rows = conn.execute(
            text("SELECT slug FROM saas_tenants WHERE slug LIKE :pattern"),
            {"pattern": f"{slug_base}%"},
        ).scalars().all()

    existing = set(rows)
    if slug_base not in existing:
        return slug_base

    for suffix in range(2, 1000):
        candidate = f"{slug_base}_{suffix}"
        if candidate not in existing:
            return candidate

    raise RuntimeError(f"No se pudo generar un slug único para: {nombre}")
