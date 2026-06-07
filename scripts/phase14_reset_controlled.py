#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Any

from phase14_common import (
    ARCHIVE_TENANT_SLUGS,
    ARCHIVE_SLUG_PREFIXES,
    FINAL_TENANTS,
    MASTER_DB,
    PRESERVE_TENANT_SLUGS,
    TENANT_OPERATIONAL_TABLES,
    classify_tenant,
    connect,
    fetch_all,
    latest_backup_for_database,
    list_saas_tenants,
    resolve_plan_id,
)


def preview() -> None:
    print("Preview only. No data will be modified.\n")
    for slug, seed in FINAL_TENANTS.items():
        print(f"- preserve-final: {slug} -> {seed.database_name}")
    try:
        tenant_rows = list_saas_tenants()
        archive_candidates = list_archive_candidates(tenant_rows)
    except BaseException:
        tenant_rows = []
        archive_candidates = []
    print("\nArchive policy:")
    print(f"- prefixes: {', '.join(ARCHIVE_SLUG_PREFIXES)}")
    print(f"- explicit slugs: {', '.join(sorted(ARCHIVE_TENANT_SLUGS))}")
    if archive_candidates:
        print("\nTenants that would be archived with current database state:")
        for tenant in archive_candidates:
            print(f"- {tenant['slug']} -> {tenant['database_name']}")
    else:
        print("\nTenants that would be archived with current database state:")
        print("- preview sin psycopg/DB; ejecutalo con dependencias del backend instaladas para ver la lista exacta")
    print("\nTables to truncate in preserved tenants:")
    for table in TENANT_OPERATIONAL_TABLES:
        print(f"- {table}")
    print("\nSeed targets after reset:")
    for slug in FINAL_TENANTS:
        print(f"- {slug}")
    print("\nActions planned:")
    print("1. Keep saas_master plan catalog and protected SUPERADMIN_GLOBAL credentials untouched.")
    print("2. Mark smoke/qa/test tenants as inactivo and close their subscriptions.")
    print("3. Clear all global and tenant FCM tokens.")
    print("4. Wipe operational rows only for final tenants auxilio_norte and mecanicos_express.")
    print("5. Leave legacy database diagramador untouched.")


def list_archive_candidates(tenant_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for tenant in tenant_rows:
        if classify_tenant(str(tenant["slug"])) == "archive-smoke":
            candidates.append(tenant)
    return candidates


def archive_non_final_tenants(cur, archive_slugs: list[str]) -> None:
    if not archive_slugs:
        return
    cur.execute(
        """
        UPDATE saas_tenants
        SET estado = 'inactivo', updated_at = NOW()
        WHERE slug = ANY(%(archive_slugs)s)
        """,
        {"archive_slugs": archive_slugs},
    )
    cur.execute(
        """
        UPDATE suscripciones
        SET estado = 'inactivo', fecha_fin = COALESCE(fecha_fin, NOW())
        WHERE tenant_id IN (
            SELECT id FROM saas_tenants WHERE slug = ANY(%(archive_slugs)s)
        )
        """,
        {"archive_slugs": archive_slugs},
    )


def clear_master_tokens(cur) -> None:
    cur.execute("DELETE FROM device_fcm_tokens")


def wipe_tenant_database(database_name: str) -> None:
    with connect(database_name) as conn, conn.cursor() as cur:
        for table in TENANT_OPERATIONAL_TABLES:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        conn.commit()


def ensure_final_metadata(cur, tenant_rows: list[dict[str, Any]]) -> None:
    plan_rows = fetch_all(MASTER_DB, "SELECT id, nombre FROM planes")
    for tenant in tenant_rows:
        slug = str(tenant["slug"])
        if slug not in FINAL_TENANTS:
            continue
        seed = FINAL_TENANTS[slug]
        plan_id = resolve_plan_id(plan_rows, seed.plan_nombre)
        cur.execute(
            """
            UPDATE saas_tenants
            SET nombre = %(nombre)s,
                correo = %(correo)s,
                telefono = %(telefono)s,
                direccion_principal = %(direccion)s,
                zona = %(zona)s,
                ciudad = %(ciudad)s,
                plan_id = %(plan_id)s,
                estado = 'activo',
                updated_at = NOW()
            WHERE slug = %(slug)s
            """,
            {
                "nombre": seed.nombre,
                "correo": seed.correo,
                "telefono": seed.telefono,
                "direccion": seed.direccion_principal,
                "zona": seed.zona,
                "ciudad": seed.ciudad,
                "plan_id": plan_id,
                "slug": slug,
            },
        )
        cur.execute(
            """
            INSERT INTO suscripciones (tenant_id, plan_id, fecha_inicio, estado, monto, metodo_pago)
            SELECT st.id, %(plan_id)s, NOW(), 'activo', 0, 'phase14_reset'
            FROM saas_tenants st
            WHERE st.slug = %(slug)s
              AND NOT EXISTS (
                  SELECT 1
                  FROM suscripciones s
                  WHERE s.tenant_id = st.id
                    AND s.estado = 'activo'
              )
            """,
            {"slug": slug, "plan_id": plan_id},
        )


def verify_backup_prerequisites() -> None:
    missing = [
        db_name for db_name in ("saas_master", "tenant_auxilio_norte", "tenant_mecanicos_express")
        if latest_backup_for_database(db_name) is None
    ]
    if missing:
        raise SystemExit(
            "Faltan backups previos requeridos en backups/phase14 para: "
            + ", ".join(missing)
            + ".\nEjecuta primero: bash scripts/phase14_backup.sh\n"
            + "Si realmente deseas omitir este control, usa --skip-backup-check."
        )


def apply_reset(*, skip_backup_check: bool = False) -> None:
    if not skip_backup_check:
        verify_backup_prerequisites()
    tenant_rows = list_saas_tenants()
    archive_candidates = list_archive_candidates(tenant_rows)
    archive_slugs = [str(tenant["slug"]) for tenant in archive_candidates]
    with connect(MASTER_DB) as conn, conn.cursor() as cur:
        archive_non_final_tenants(cur, archive_slugs)
        clear_master_tokens(cur)
        ensure_final_metadata(cur, tenant_rows)
        conn.commit()

    for tenant in tenant_rows:
        if str(tenant["slug"]) in PRESERVE_TENANT_SLUGS:
            wipe_tenant_database(str(tenant["database_name"]))

    print("Reset controlado aplicado.")
    print("Tenants preservados limpiados: auxilio_norte, mecanicos_express")
    print("Tenants smoke/qa/test archivados en saas_master.")
    print("Tokens FCM globales eliminados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 14 controlled reset")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reset. Without this flag the script only prints the plan.",
    )
    parser.add_argument(
        "--skip-backup-check",
        action="store_true",
        help="Skip required backup presence checks before apply.",
    )
    args = parser.parse_args()
    if not args.apply:
        preview()
        return
    apply_reset(skip_backup_check=args.skip_backup_check)


if __name__ == "__main__":
    main()
