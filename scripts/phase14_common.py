#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING
import unicodedata

if TYPE_CHECKING:
    import psycopg

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(os.getenv("PHASE14_BACKUP_DIR", str(ROOT_DIR / "backups" / "phase14")))

PGHOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
PGPORT = int(os.getenv("POSTGRES_PORT", "5432"))
PGUSER = os.getenv("POSTGRES_USER", "diagramador")
PGPASSWORD = os.getenv("POSTGRES_PASSWORD", "diagramador")

MASTER_DB = os.getenv("SAAS_MASTER_DB", "saas_master")
LEGACY_DB = os.getenv("POSTGRES_DB", "diagramador")

ROLE_SUPERADMIN_GLOBAL = "SUPERADMIN_GLOBAL"
ROLE_SUPERADMIN_TENANT = "SUPERADMIN_TENANT"
ROLE_ADMIN_SUCURSAL = "ADMIN_SUCURSAL"
ROLE_TECNICO = "TECNICO"
ROLE_CLIENTE = "CLIENTE"

PRESERVE_TENANT_SLUGS = {"auxilio_norte", "mecanicos_express"}
ARCHIVE_SLUG_PREFIXES = ("smoke_", "qa_", "test_", "demo_")
ARCHIVE_TENANT_SLUGS = {
    "smoke_tenant_1780768874",
    "smoke_demo_a_1780794036",
    "smoke_demo_b_1780794036",
    "qa_integral_1780805933",
    "tenant_bootstrap_qa",
    "taller_verificacion_test",
}
REQUIRED_BACKUP_DATABASES = ["saas_master", "tenant_auxilio_norte", "tenant_mecanicos_express"]

TENANT_OPERATIONAL_TABLES = [
    "quotation_request_history",
    "quotation_offers",
    "quotation_request_workshops",
    "quotation_requests",
    "emergency_tracking_points",
    "notifications",
    "device_fcm_tokens",
    "emergency_status_history",
    "emergency_assignments",
    "emergency_reports",
    "vehicles",
    "clients",
    "technicians",
    "workshop_registrations",
    "usuarios_tenant",
    "sucursales",
]

TENANT_COUNT_TABLES = [
    "sucursales",
    "usuarios_tenant",
    "workshop_registrations",
    "technicians",
    "clients",
    "vehicles",
    "emergency_reports",
    "emergency_assignments",
    "emergency_status_history",
    "device_fcm_tokens",
    "notifications",
    "emergency_tracking_points",
    "quotation_requests",
    "quotation_request_workshops",
    "quotation_offers",
    "quotation_request_history",
]

LEGACY_COUNT_TABLES = [
    "tenants",
    "workshop_registrations",
    "technicians",
    "clients",
    "vehicles",
    "emergency_reports",
    "emergency_assignments",
    "emergency_status_history",
    "device_fcm_tokens",
    "notifications",
    "emergency_tracking_points",
    "quotation_requests",
    "quotation_request_workshops",
    "quotation_offers",
    "quotation_request_history",
]


@dataclass(frozen=True)
class BranchSeed:
    key: str
    nombre: str
    direccion: str
    zona: str
    telefono: str
    responsable: str
    latitud: float
    longitud: float


@dataclass(frozen=True)
class TenantSeed:
    slug: str
    nombre: str
    correo: str
    telefono: str
    ciudad: str
    zona: str
    direccion_principal: str
    plan_nombre: str
    database_name: str
    admin_password: str
    client_password: str
    workshop_password: str
    branches: tuple[BranchSeed, ...]


FINAL_TENANTS: dict[str, TenantSeed] = {
    "auxilio_norte": TenantSeed(
        slug="auxilio_norte",
        nombre="Auxilio Norte",
        correo="contacto@auxilionorte.com",
        telefono="70010001",
        ciudad="Santa Cruz",
        zona="Norte",
        direccion_principal="Av. Banzer 1234",
        plan_nombre="Estandar",
        database_name="tenant_auxilio_norte",
        admin_password="AuxilioNorte#2026",
        client_password="ClienteAuxilio#2026",
        workshop_password="WorkshopAuxilio#2026",
        branches=(
            BranchSeed(
                key="norte",
                nombre="Sucursal Norte",
                direccion="Av. Banzer 1234",
                zona="Norte",
                telefono="70010011",
                responsable="Rosa Perez",
                latitud=-17.7534,
                longitud=-63.1768,
            ),
            BranchSeed(
                key="sur",
                nombre="Sucursal Sur",
                direccion="Av. Santos Dumont 5421",
                zona="Sur",
                telefono="70010012",
                responsable="Luis Arce",
                latitud=-17.8348,
                longitud=-63.1902,
            ),
        ),
    ),
    "mecanicos_express": TenantSeed(
        slug="mecanicos_express",
        nombre="Mecanicos Express",
        correo="admin@mecanicosexpress.com",
        telefono="70020001",
        ciudad="Santa Cruz",
        zona="Centro",
        direccion_principal="Av. Alemana 808",
        plan_nombre="Estandar",
        database_name="tenant_mecanicos_express",
        admin_password="MecanicosExpress#2026",
        client_password="ClienteExpress#2026",
        workshop_password="WorkshopExpress#2026",
        branches=(
            BranchSeed(
                key="central",
                nombre="Sucursal Central",
                direccion="Av. Alemana 808",
                zona="Centro",
                telefono="70020011",
                responsable="Javier Roca",
                latitud=-17.7792,
                longitud=-63.1824,
            ),
        ),
    ),
}


def connect(dbname: str, *, autocommit: bool = False) -> "psycopg.Connection":
    require_psycopg()
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(
        host=PGHOST,
        port=PGPORT,
        user=PGUSER,
        password=PGPASSWORD,
        dbname=dbname,
        row_factory=dict_row,
    )
    conn.autocommit = autocommit
    return conn


def fetch_all(dbname: str, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with connect(dbname) as conn, conn.cursor() as cur:
        cur.execute(query, params or {})
        return list(cur.fetchall())


def fetch_one(dbname: str, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(dbname, query, params)
    return rows[0] if rows else None


def execute(dbname: str, query: str, params: dict[str, Any] | None = None) -> None:
    with connect(dbname) as conn, conn.cursor() as cur:
        cur.execute(query, params or {})
        conn.commit()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def require_psycopg() -> None:
    if importlib.util.find_spec("psycopg") is not None:
        return
    raise SystemExit(
        "psycopg no esta disponible en el Python actual.\n"
        "Instala dependencias del backend en tu entorno local antes de usar --apply:\n"
        "  python3 -m pip install -r backend/requirements.txt\n"
        "Nota: el contenedor backend actual no tiene montado el directorio scripts/, "
        "asi que estos archivos no pueden ejecutarse alli sin ajustar docker-compose o copiar los scripts."
    )


def normalize_text_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_only.strip().lower()


def build_plan_lookup(plan_rows: list[dict[str, Any]]) -> dict[str, int]:
    aliases: dict[str, int] = {}
    for row in plan_rows:
        plan_id = int(row["id"])
        raw_name = str(row["nombre"])
        keys = {
            normalize_text_key(raw_name),
            normalize_text_key(raw_name.replace("á", "a").replace("Á", "A")),
        }
        if normalize_text_key(raw_name) == "estandar":
            keys.update({"estandar", "estándar"})
        for key in keys:
            aliases[key] = plan_id
    return aliases


def resolve_plan_id(plan_rows: list[dict[str, Any]], desired_name: str) -> int:
    plan_lookup = build_plan_lookup(plan_rows)
    normalized = normalize_text_key(desired_name)
    if normalized not in plan_lookup:
        available = ", ".join(sorted(str(row["nombre"]) for row in plan_rows))
        raise SystemExit(
            f"No se pudo resolver el plan '{desired_name}'. "
            f"Planes disponibles: {available}"
        )
    return plan_lookup[normalized]


def list_databases() -> list[str]:
    rows = fetch_all(
        "postgres",
        """
        SELECT datname
        FROM pg_database
        WHERE datistemplate = FALSE
        ORDER BY datname
        """,
    )
    return [str(row["datname"]) for row in rows]


def list_saas_tenants() -> list[dict[str, Any]]:
    return fetch_all(
        MASTER_DB,
        """
        SELECT
            st.id,
            st.slug,
            st.nombre,
            st.correo,
            st.estado,
            st.database_name,
            st.created_at,
            p.nombre AS plan_nombre
        FROM saas_tenants st
        LEFT JOIN planes p ON p.id = st.plan_id
        ORDER BY st.id
        """,
    )


def table_counts(dbname: str, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connect(dbname) as conn, conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) AS total FROM {table}")
            counts[table] = int(cur.fetchone()["total"])
    return counts


def classify_tenant(slug: str) -> str:
    if slug in PRESERVE_TENANT_SLUGS:
        return "preserve-final"
    if slug in ARCHIVE_TENANT_SLUGS:
        return "archive-smoke"
    if any(slug.startswith(prefix) for prefix in ARCHIVE_SLUG_PREFIXES):
        return "archive-smoke"
    return "review-manual"


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def list_backup_files() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(path for path in BACKUP_DIR.glob("*.sql") if path.is_file())


def latest_backup_for_database(db_name: str) -> Path | None:
    candidates = sorted(BACKUP_DIR.glob(f"{db_name}_*.sql"))
    return candidates[-1] if candidates else None
