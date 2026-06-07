"""
Schema completo para la base de datos de cada tenant.

Cada empresa registrada obtiene su propia BD con estas tablas.
Las tablas NO incluyen tenant_id porque la BD en sí es el tenant.
"""
from sqlalchemy import text

# =============================================================================
# TABLA: sucursales — sedes/branches del tenant
# =============================================================================
CREATE_SUCURSALES_SQL = text("""
    CREATE TABLE IF NOT EXISTS sucursales (
        id BIGSERIAL PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        direccion TEXT NOT NULL DEFAULT '',
        zona VARCHAR(120),
        ciudad VARCHAR(120) NOT NULL DEFAULT 'Santa Cruz',
        latitud DOUBLE PRECISION,
        longitud DOUBLE PRECISION,
        telefono VARCHAR(50),
        responsable VARCHAR(160),
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: usuarios_tenant — usuarios propios del tenant (SUPERADMIN_TENANT, ADMIN_SUCURSAL, TECNICO, CLIENTE)
# =============================================================================
CREATE_USUARIOS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS usuarios_tenant (
        id BIGSERIAL PRIMARY KEY,
        email VARCHAR(160) NOT NULL UNIQUE,
        full_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL DEFAULT '',
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(60) NOT NULL DEFAULT 'TECNICO',
        sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL,
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: workshop_registrations — talleres del tenant
# =============================================================================
CREATE_WORKSHOPS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS workshop_registrations (
        id BIGSERIAL PRIMARY KEY,
        workshop_name VARCHAR(160) NOT NULL,
        contact_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL,
        zone VARCHAR(120) NOT NULL,
        specialty VARCHAR(120) NOT NULL,
        approval_status VARCHAR(30) NOT NULL DEFAULT 'pendiente',
        availability_status VARCHAR(30) NOT NULL DEFAULT 'disponible',
        password_hash VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        timezone VARCHAR(120),
        utc_offset_minutes INTEGER,
        sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

CREATE_WORKSHOP_SPECIALTIES_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS workshop_specialties (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        specialty VARCHAR(120) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(workshop_id, specialty)
    )
""")

# =============================================================================
# TABLA: technicians — técnicos del tenant
# =============================================================================
CREATE_TECHNICIANS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS technicians (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        usuario_tenant_id BIGINT REFERENCES usuarios_tenant(id) ON DELETE SET NULL,
        full_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL DEFAULT '',
        specialty VARCHAR(120) NOT NULL,
        status VARCHAR(30) NOT NULL,
        sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: clients — clientes del tenant
# =============================================================================
CREATE_CLIENTS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS clients (
        id BIGSERIAL PRIMARY KEY,
        identity_card VARCHAR(40) NOT NULL UNIQUE,
        full_name VARCHAR(160) NOT NULL,
        email VARCHAR(160) NOT NULL UNIQUE,
        phone VARCHAR(40) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(40) NOT NULL DEFAULT 'CLIENTE',
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        accepted_terms BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: vehicles
# =============================================================================
CREATE_VEHICLES_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id BIGSERIAL PRIMARY KEY,
        client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
        brand VARCHAR(120) NOT NULL,
        model VARCHAR(120) NOT NULL,
        year INTEGER NOT NULL,
        plate VARCHAR(40) NOT NULL UNIQUE,
        color VARCHAR(80) NOT NULL,
        is_primary BOOLEAN NOT NULL DEFAULT FALSE,
        photo_path VARCHAR(255),
        photo_url VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: emergency_reports
# =============================================================================
CREATE_EMERGENCY_REPORTS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS emergency_reports (
        id BIGSERIAL PRIMARY KEY,
        local_id VARCHAR(64) UNIQUE,
        client_id BIGINT REFERENCES clients(id) ON DELETE SET NULL,
        vehicle_name VARCHAR(160) NOT NULL,
        vehicle_plate VARCHAR(40) NOT NULL,
        problem_type VARCHAR(120) NOT NULL,
        price INTEGER,
        emergency_status VARCHAR(30) NOT NULL DEFAULT 'pendiente',
        problem_type_standardized VARCHAR(120),
        photo_problem_type_standardized VARCHAR(120),
        photo_classification_confidence DOUBLE PRECISION,
        photo_classification_error TEXT,
        description TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        address VARCHAR(255),
        zone VARCHAR(120),
        nearest_workshop_id BIGINT,
        nearest_workshop_name VARCHAR(160),
        nearest_workshop_specialty VARCHAR(120),
        nearest_workshop_zone VARCHAR(120),
        nearest_workshop_distance_meters DOUBLE PRECISION,
        audio_duration_seconds DOUBLE PRECISION,
        audio_transcript TEXT,
        audio_transcript_status VARCHAR(30),
        audio_transcript_error TEXT,
        photo_paths TEXT NOT NULL DEFAULT '[]',
        photo_urls TEXT NOT NULL DEFAULT '[]',
        audio_path VARCHAR(255),
        audio_url VARCHAR(255),
        rejection_reason TEXT,
        rejected_at TIMESTAMPTZ,
        hora_llegada TIMESTAMPTZ,
        latitud_llegada DOUBLE PRECISION,
        longitud_llegada DOUBLE PRECISION,
        sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: emergency_assignments
# =============================================================================
CREATE_EMERGENCY_ASSIGNMENTS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS emergency_assignments (
        id BIGSERIAL PRIMARY KEY,
        emergency_report_id BIGINT NOT NULL UNIQUE REFERENCES emergency_reports(id) ON DELETE CASCADE,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        technician_id BIGINT NOT NULL REFERENCES technicians(id) ON DELETE RESTRICT,
        assignment_status VARCHAR(30) NOT NULL DEFAULT 'asignado',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: emergency_status_history
# =============================================================================
CREATE_EMERGENCY_STATUS_HISTORY_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS emergency_status_history (
        id BIGSERIAL PRIMARY KEY,
        emergency_id BIGINT NOT NULL REFERENCES emergency_reports(id) ON DELETE CASCADE,
        previous_status VARCHAR(50),
        new_status VARCHAR(50) NOT NULL,
        changed_by_role VARCHAR(50),
        changed_by_user_id BIGINT,
        observation TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: device_fcm_tokens
# =============================================================================
CREATE_DEVICE_FCM_TOKENS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS device_fcm_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        fcm_token TEXT NOT NULL UNIQUE,
        platform VARCHAR(40) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: notifications
# =============================================================================
CREATE_NOTIFICATIONS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS notifications (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        title VARCHAR(160) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        payload_json TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: emergency_tracking_points
# =============================================================================
CREATE_EMERGENCY_TRACKING_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS emergency_tracking_points (
        id BIGSERIAL PRIMARY KEY,
        emergency_id BIGINT NOT NULL REFERENCES emergency_reports(id) ON DELETE CASCADE,
        technician_id BIGINT REFERENCES technicians(id) ON DELETE SET NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        source VARCHAR(50) NOT NULL DEFAULT 'system',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: quotation_requests
# =============================================================================
CREATE_QUOTATION_REQUESTS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS quotation_requests (
        id BIGSERIAL PRIMARY KEY,
        emergency_id BIGINT REFERENCES emergency_reports(id) ON DELETE CASCADE,
        client_id BIGINT REFERENCES clients(id) ON DELETE SET NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'abierto',
        requested_workshops_count INTEGER NOT NULL DEFAULT 0,
        received_offers_count INTEGER NOT NULL DEFAULT 0,
        selected_offer_id BIGINT,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: quotation_request_workshops
# =============================================================================
CREATE_QUOTATION_REQUEST_WORKSHOPS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS quotation_request_workshops (
        id BIGSERIAL PRIMARY KEY,
        quotation_request_id BIGINT NOT NULL REFERENCES quotation_requests(id) ON DELETE CASCADE,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL DEFAULT 'notificado',
        notified_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# TABLA: quotation_offers
# =============================================================================
CREATE_QUOTATION_OFFERS_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS quotation_offers (
        id BIGSERIAL PRIMARY KEY,
        quotation_request_id BIGINT NOT NULL REFERENCES quotation_requests(id) ON DELETE CASCADE,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        workshop_rating DOUBLE PRECISION,
        price NUMERIC(12, 2),
        service_description TEXT,
        spare_parts TEXT,
        labor_detail TEXT,
        labor_cost NUMERIC(12, 2),
        spare_parts_cost NUMERIC(12, 2),
        estimated_service_time VARCHAR(80),
        estimated_arrival_time VARCHAR(80),
        warranty VARCHAR(255),
        validity_days INTEGER,
        observations TEXT,
        condiciones_servicio TEXT,
        status VARCHAR(30) NOT NULL DEFAULT 'enviada',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ
    )
""")

# =============================================================================
# TABLA: quotation_request_history
# =============================================================================
CREATE_QUOTATION_REQUEST_HISTORY_TENANT_SQL = text("""
    CREATE TABLE IF NOT EXISTS quotation_request_history (
        id BIGSERIAL PRIMARY KEY,
        quotation_request_id BIGINT NOT NULL REFERENCES quotation_requests(id) ON DELETE CASCADE,
        event_type VARCHAR(50) NOT NULL,
        detail TEXT,
        actor_role VARCHAR(50),
        actor_user_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
""")

# =============================================================================
# Orden de creación (respeta FKs)
# =============================================================================
TENANT_TABLES_IN_ORDER = [
    CREATE_SUCURSALES_SQL,
    CREATE_USUARIOS_TENANT_SQL,
    CREATE_WORKSHOPS_TENANT_SQL,
    CREATE_WORKSHOP_SPECIALTIES_TENANT_SQL,
    CREATE_TECHNICIANS_TENANT_SQL,
    CREATE_CLIENTS_TENANT_SQL,
    CREATE_VEHICLES_TENANT_SQL,
    CREATE_EMERGENCY_REPORTS_TENANT_SQL,
    CREATE_EMERGENCY_ASSIGNMENTS_TENANT_SQL,
    CREATE_EMERGENCY_STATUS_HISTORY_TENANT_SQL,
    CREATE_DEVICE_FCM_TOKENS_TENANT_SQL,
    CREATE_NOTIFICATIONS_TENANT_SQL,
    CREATE_EMERGENCY_TRACKING_TENANT_SQL,
    CREATE_QUOTATION_REQUESTS_TENANT_SQL,
    CREATE_QUOTATION_REQUEST_WORKSHOPS_TENANT_SQL,
    CREATE_QUOTATION_OFFERS_TENANT_SQL,
    CREATE_QUOTATION_REQUEST_HISTORY_TENANT_SQL,
]

TENANT_SCHEMA_UPGRADE_STATEMENTS = [
    text("CREATE INDEX IF NOT EXISTS workshop_specialties_workshop_id_idx ON workshop_specialties (workshop_id)"),
    text("CREATE INDEX IF NOT EXISTS workshop_specialties_specialty_idx ON workshop_specialties (specialty)"),
    text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS usuario_tenant_id BIGINT REFERENCES usuarios_tenant(id) ON DELETE SET NULL"),
    text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS sucursal_id BIGINT REFERENCES sucursales(id) ON DELETE SET NULL"),
    text("CREATE INDEX IF NOT EXISTS idx_technicians_sucursal_id ON technicians (sucursal_id)"),
    text(
        """
        UPDATE technicians t
        SET sucursal_id = wr.sucursal_id
        FROM workshop_registrations wr
        WHERE t.workshop_id = wr.id
          AND t.sucursal_id IS DISTINCT FROM wr.sucursal_id
        """
    ),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS estimated_arrival_time VARCHAR(80)"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS warranty VARCHAR(255)"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS validity_days INTEGER"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS observations TEXT"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS condiciones_servicio TEXT"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'enviada'"),
    text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ"),
    text(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'quotation_offers'
                  AND column_name = 'offer_status'
            ) THEN
                EXECUTE 'UPDATE quotation_offers SET status = COALESCE(status, offer_status, ''enviada'')';
            ELSE
                EXECUTE 'UPDATE quotation_offers SET status = COALESCE(status, ''enviada'')';
            END IF;
        END $$;
        """
    ),
    text("UPDATE quotation_offers SET status = 'enviada' WHERE status = 'pendiente'"),
    text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'notificado'"),
    text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_requests_emergency_id ON quotation_requests (emergency_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_requests_client_id ON quotation_requests (client_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_request_workshops_workshop_id ON quotation_request_workshops (workshop_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_request_workshops_quotation_request_id ON quotation_request_workshops (quotation_request_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_offers_workshop_id ON quotation_offers (workshop_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_offers_quotation_request_id ON quotation_offers (quotation_request_id)"),
    text("CREATE INDEX IF NOT EXISTS idx_quotation_request_history_request_id ON quotation_request_history (quotation_request_id)"),
    text("CREATE UNIQUE INDEX IF NOT EXISTS uq_quotation_request_workshops_request_workshop ON quotation_request_workshops (quotation_request_id, workshop_id)"),
    text("CREATE UNIQUE INDEX IF NOT EXISTS uq_quotation_offers_request_workshop ON quotation_offers (quotation_request_id, workshop_id)"),
]
