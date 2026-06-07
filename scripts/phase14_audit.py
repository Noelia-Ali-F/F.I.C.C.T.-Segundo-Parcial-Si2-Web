#!/usr/bin/env python3
from __future__ import annotations

import json

from phase14_common import (
    LEGACY_COUNT_TABLES,
    LEGACY_DB,
    MASTER_DB,
    TENANT_COUNT_TABLES,
    classify_tenant,
    list_databases,
    list_saas_tenants,
    table_counts,
)


def main() -> None:
    report: dict[str, object] = {
        "databases": list_databases(),
        "saas_master_counts": table_counts(
            MASTER_DB,
            ["planes", "saas_tenants", "suscripciones", "auditoria_saas", "device_fcm_tokens"],
        ),
        "legacy_counts": table_counts(LEGACY_DB, LEGACY_COUNT_TABLES),
        "tenants": [],
    }
    for tenant in list_saas_tenants():
        tenant_report = dict(tenant)
        tenant_report["classification"] = classify_tenant(str(tenant["slug"]))
        tenant_report["counts"] = table_counts(str(tenant["database_name"]), TENANT_COUNT_TABLES)
        report["tenants"].append(tenant_report)
    print(json.dumps(report, indent=2, default=str, ensure_ascii=True))


if __name__ == "__main__":
    main()

