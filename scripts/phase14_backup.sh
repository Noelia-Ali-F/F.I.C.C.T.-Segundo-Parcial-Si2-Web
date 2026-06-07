#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups/phase14"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "${BACKUP_DIR}"

export PGPASSWORD="${POSTGRES_PASSWORD:-diagramador}"
PGHOST="${POSTGRES_HOST:-127.0.0.1}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-diagramador}"

backup_db() {
  local db_name="$1"
  local out_file="${BACKUP_DIR}/${db_name}_${STAMP}.sql"
  echo "Backing up ${db_name} -> ${out_file}"
  pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db_name}" -f "${out_file}"
}

backup_db "saas_master"
backup_db "diagramador"
backup_db "tenant_auxilio_norte"
backup_db "tenant_mecanicos_express"
backup_db "tenant_qa_integral_1780805933"
backup_db "tenant_smoke_demo_a_1780794036"
backup_db "tenant_smoke_demo_b_1780794036"
backup_db "tenant_smoke_tenant_1780768874"
backup_db "tenant_taller_sur_premium"
backup_db "tenant_taller_verificacion_test"
backup_db "tenant_tenant_bootstrap_qa"

echo "Phase 14 backups completed in ${BACKUP_DIR}"

