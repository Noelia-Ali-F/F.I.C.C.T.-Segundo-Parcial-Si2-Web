from collections.abc import Mapping

from sqlalchemy import create_engine, text

from app.config import settings


# Engine por defecto apunta a la BD 'diagramador' (backward-compatible).
# Para operaciones globales del admin y datos legados.
_default_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": settings.postgres_connect_timeout},
)


class _TenantEngineProxy:
    """
    Proxy transparente sobre el engine SQLAlchemy.

    En cada llamada a .connect() o .begin() devuelve el engine del tenant
    activo en el contexto del request actual (si existe), o el engine
    por defecto ('diagramador') en caso contrario.

    Esto permite que todo el código existente de db.py sea multi-tenant
    sin cambiar ninguna función individual.
    """

    def connect(self):
        return self._resolve().connect()

    def begin(self):
        return self._resolve().begin()

    def dispose(self):
        return self._resolve().dispose()

    @staticmethod
    def _resolve():
        try:
            from app.tenant_context import get_engine
            return get_engine()
        except Exception:
            return _default_engine


engine = _TenantEngineProxy()

CREATE_TENANTS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS tenants (
        id BIGSERIAL PRIMARY KEY,
        nombre VARCHAR(200) NOT NULL,
        descripcion TEXT,
        estado VARCHAR(30) NOT NULL DEFAULT 'activo',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_WORKSHOPS_TABLE_SQL = text(
    """
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
        sucursal_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_WORKSHOP_SPECIALTIES_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS workshop_specialties (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        specialty VARCHAR(120) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(workshop_id, specialty)
    )
    """
)
CREATE_TECHNICIANS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS technicians (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        usuario_tenant_id BIGINT,
        full_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL DEFAULT '',
        specialty VARCHAR(120) NOT NULL,
        status VARCHAR(30) NOT NULL,
        sucursal_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_CLIENTS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS clients (
        id BIGSERIAL PRIMARY KEY,
        identity_card VARCHAR(40) NOT NULL UNIQUE,
        full_name VARCHAR(160) NOT NULL,
        email VARCHAR(160) NOT NULL UNIQUE,
        phone VARCHAR(40) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(40) NOT NULL DEFAULT 'client',
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        accepted_terms BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_VEHICLES_TABLE_SQL = text(
    """
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
    """
)
CREATE_EMERGENCY_REPORTS_TABLE_SQL = text(
    """
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
        sucursal_id BIGINT,
        hora_llegada TIMESTAMPTZ,
        latitud_llegada DOUBLE PRECISION,
        longitud_llegada DOUBLE PRECISION,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_EMERGENCY_ASSIGNMENTS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS emergency_assignments (
        id BIGSERIAL PRIMARY KEY,
        emergency_report_id BIGINT NOT NULL UNIQUE REFERENCES emergency_reports(id) ON DELETE CASCADE,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        technician_id BIGINT NOT NULL REFERENCES technicians(id) ON DELETE RESTRICT,
        assignment_status VARCHAR(30) NOT NULL DEFAULT 'asignado',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_EMERGENCY_STATUS_HISTORY_TABLE_SQL = text(
    """
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
    """
)
CREATE_DEVICE_FCM_TOKENS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS device_fcm_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        fcm_token TEXT NOT NULL UNIQUE,
        platform VARCHAR(40) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_NOTIFICATIONS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        title VARCHAR(160) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        payload_json TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_EMERGENCY_TRACKING_POINTS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS emergency_tracking_points (
        id BIGSERIAL PRIMARY KEY,
        emergency_id BIGINT NOT NULL REFERENCES emergency_reports(id) ON DELETE CASCADE,
        technician_id BIGINT REFERENCES technicians(id) ON DELETE SET NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        source VARCHAR(50) NOT NULL DEFAULT 'system',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

CREATE_QUOTATION_REQUESTS_TABLE_SQL = text(
    """
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
    """
)
CREATE_QUOTATION_REQUEST_WORKSHOPS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS quotation_request_workshops (
        id BIGSERIAL PRIMARY KEY,
        quotation_request_id BIGINT NOT NULL REFERENCES quotation_requests(id) ON DELETE CASCADE,
        workshop_id BIGINT NOT NULL REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL DEFAULT 'notificado',
        notified_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_QUOTATION_OFFERS_TABLE_SQL = text(
    """
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
    """
)
CREATE_QUOTATION_REQUEST_HISTORY_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS quotation_request_history (
        id BIGSERIAL PRIMARY KEY,
        quotation_request_id BIGINT NOT NULL REFERENCES quotation_requests(id) ON DELETE CASCADE,
        event_type VARCHAR(50) NOT NULL,
        detail TEXT,
        actor_role VARCHAR(50),
        actor_user_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)

INSERT_WORKSHOP_SQL = text("INSERT INTO workshop_registrations (workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id) VALUES (:workshop_name, :contact_name, :phone, :email, :zone, :specialty, :approval_status, :availability_status, :password_hash, :latitude, :longitude, :timezone, :utc_offset_minutes, :sucursal_id) RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at")
LIST_WORKSHOPS_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at FROM workshop_registrations ORDER BY created_at DESC, id DESC")
UPDATE_WORKSHOP_SQL = text("UPDATE workshop_registrations SET workshop_name = :workshop_name, contact_name = :contact_name, phone = :phone, email = :email, zone = :zone, specialty = :specialty, approval_status = COALESCE(:approval_status, approval_status), availability_status = COALESCE(:availability_status, availability_status), password_hash = COALESCE(:password_hash, password_hash), latitude = :latitude, longitude = :longitude, timezone = :timezone, utc_offset_minutes = :utc_offset_minutes, sucursal_id = :sucursal_id WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at")
UPDATE_WORKSHOP_APPROVAL_STATUS_SQL = text("UPDATE workshop_registrations SET approval_status = :approval_status, password_hash = COALESCE(:password_hash, password_hash) WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at")
UPDATE_WORKSHOP_PASSWORD_SQL = text("UPDATE workshop_registrations SET password_hash = :password_hash WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at")
GET_WORKSHOP_BY_EMAIL_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at FROM workshop_registrations WHERE email = :email LIMIT 1")
GET_WORKSHOP_BY_ID_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at FROM workshop_registrations WHERE id = :id LIMIT 1")
GET_WORKSHOP_BY_SUCURSAL_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at FROM workshop_registrations WHERE sucursal_id = :sucursal_id ORDER BY created_at ASC, id ASC LIMIT 1")
GET_SUCURSAL_BY_ID_SQL = text("SELECT id, nombre, estado FROM sucursales WHERE id = :id LIMIT 1")
DELETE_WORKSHOP_SQL = text("DELETE FROM workshop_registrations WHERE id = :id RETURNING id")

INSERT_TECHNICIAN_SQL = text("INSERT INTO technicians (workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id) VALUES (:workshop_id, :usuario_tenant_id, :full_name, :phone, :email, :specialty, :status, :sucursal_id) RETURNING id, workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at")
LIST_TECHNICIANS_SQL = text("SELECT t.id, t.workshop_id, t.usuario_tenant_id, t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, s.nombre AS sucursal_nombre, t.created_at, t.updated_at FROM technicians t LEFT JOIN sucursales s ON s.id = t.sucursal_id ORDER BY t.updated_at DESC, t.id DESC")
LIST_TECHNICIANS_BY_WORKSHOP_SQL = text("SELECT t.id, t.workshop_id, t.usuario_tenant_id, t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, s.nombre AS sucursal_nombre, t.created_at, t.updated_at FROM technicians t LEFT JOIN sucursales s ON s.id = t.sucursal_id WHERE t.workshop_id = :workshop_id ORDER BY t.updated_at DESC, t.id DESC")
GET_TECHNICIAN_BY_WORKSHOP_SQL = text("SELECT t.id, t.workshop_id, t.usuario_tenant_id, t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, s.nombre AS sucursal_nombre, t.created_at, t.updated_at FROM technicians t LEFT JOIN sucursales s ON s.id = t.sucursal_id WHERE t.id = :id AND t.workshop_id = :workshop_id LIMIT 1")
UPDATE_TECHNICIAN_SQL = text("UPDATE technicians SET workshop_id = COALESCE(:workshop_id, workshop_id), full_name = :full_name, phone = :phone, email = :email, specialty = :specialty, status = :status, sucursal_id = :sucursal_id, updated_at = NOW() WHERE id = :id RETURNING id, workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at")
UPDATE_TECHNICIAN_STATUS_SQL = text("UPDATE technicians SET status = :status, updated_at = NOW() WHERE id = :id RETURNING id, workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at")
UPDATE_TECHNICIAN_BY_WORKSHOP_SQL = text("UPDATE technicians SET full_name = :full_name, phone = :phone, email = :email, specialty = :specialty, status = :status, sucursal_id = :sucursal_id, updated_at = NOW() WHERE id = :id AND workshop_id = :workshop_id RETURNING id, workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at")
DELETE_TECHNICIAN_SQL = text("DELETE FROM technicians WHERE id = :id RETURNING id")
DELETE_TECHNICIAN_BY_WORKSHOP_SQL = text("DELETE FROM technicians WHERE id = :id AND workshop_id = :workshop_id RETURNING id")

INSERT_CLIENT_SQL = text("INSERT INTO clients (identity_card, full_name, email, phone, password_hash, role, status, accepted_terms) VALUES (:identity_card, :full_name, :email, :phone, :password_hash, :role, :status, :accepted_terms) RETURNING id, identity_card, full_name, email, phone, role, status, accepted_terms, created_at, updated_at")
UPDATE_CLIENT_SQL = text("UPDATE clients SET identity_card = :identity_card, full_name = :full_name, email = :email, phone = :phone, password_hash = COALESCE(:password_hash, password_hash), role = :role, status = :status, accepted_terms = :accepted_terms, updated_at = NOW() WHERE id = :id RETURNING id, identity_card, full_name, email, phone, role, status, accepted_terms, created_at, updated_at")
LIST_CLIENTS_SQL = text("SELECT id, identity_card, full_name, email, phone, role, status, accepted_terms, created_at, updated_at FROM clients ORDER BY created_at DESC, id DESC")
GET_CLIENT_BY_EMAIL_SQL = text("SELECT id, identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at FROM clients WHERE email = :email LIMIT 1")
GET_CLIENT_BY_ID_SQL = text("SELECT id, identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at FROM clients WHERE id = :id LIMIT 1")
UPDATE_CLIENT_STATUS_SQL = text("UPDATE clients SET status = :status, updated_at = NOW() WHERE id = :id RETURNING id, identity_card, full_name, email, phone, role, status, accepted_terms, created_at, updated_at")
UPDATE_CLIENT_PASSWORD_SQL = text("UPDATE clients SET password_hash = :password_hash, updated_at = NOW() WHERE id = :id RETURNING id, identity_card, full_name, email, phone, role, status, accepted_terms, created_at, updated_at")
DELETE_CLIENT_SQL = text("DELETE FROM clients WHERE id = :id RETURNING id")
DELETE_CLIENT_VEHICLES_SQL = text("DELETE FROM vehicles WHERE client_id = :client_id")

INSERT_VEHICLE_SQL = text("INSERT INTO vehicles (client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url) VALUES (:client_id, :brand, :model, :year, :plate, :color, :is_primary, :photo_path, :photo_url) RETURNING id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at")
LIST_VEHICLES_SQL = text("SELECT id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at FROM vehicles WHERE client_id = :client_id ORDER BY created_at DESC, id DESC")
GET_VEHICLE_BY_ID_SQL = text("SELECT id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at FROM vehicles WHERE id = :id AND client_id = :client_id LIMIT 1")
UPDATE_VEHICLE_SQL = text("UPDATE vehicles SET client_id = :client_id, brand = :brand, model = :model, year = :year, plate = :plate, color = :color, is_primary = :is_primary, photo_path = :photo_path, photo_url = :photo_url WHERE id = :id AND client_id = :client_id RETURNING id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at")
DELETE_VEHICLE_SQL = text("DELETE FROM vehicles WHERE id = :id AND client_id = :client_id RETURNING id, client_id, photo_path")

INSERT_EMERGENCY_REPORT_SQL = text("INSERT INTO emergency_reports (local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at, sucursal_id) VALUES (:local_id, :client_id, :vehicle_name, :vehicle_plate, :problem_type, :price, :emergency_status, :problem_type_standardized, :photo_problem_type_standardized, :photo_classification_confidence, :photo_classification_error, :description, :latitude, :longitude, :address, :zone, :nearest_workshop_id, :nearest_workshop_name, :nearest_workshop_specialty, :nearest_workshop_zone, :nearest_workshop_distance_meters, :audio_duration_seconds, :audio_transcript, :audio_transcript_status, :audio_transcript_error, :photo_paths, :photo_urls, :audio_path, :audio_url, :rejection_reason, :rejected_at, :sucursal_id) RETURNING id, local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at, sucursal_id, created_at")
GET_EMERGENCY_BY_LOCAL_ID_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.created_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE er.local_id = :local_id LIMIT 1")
LIST_EMERGENCY_REPORTS_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.photo_problem_type_standardized, er.photo_classification_confidence, er.photo_classification_error, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.nearest_workshop_specialty, er.nearest_workshop_zone, er.nearest_workshop_distance_meters, er.audio_duration_seconds, er.audio_transcript, er.audio_transcript_status, er.audio_transcript_error, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.hora_llegada, er.latitud_llegada, er.longitud_llegada, er.sucursal_id, er.created_at, er.updated_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR er.nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) AND (CAST(:emergency_status AS VARCHAR(30)) IS NULL OR er.emergency_status = CAST(:emergency_status AS VARCHAR(30))) AND (CAST(:client_id AS BIGINT) IS NULL OR er.client_id = CAST(:client_id AS BIGINT)) AND (CAST(:technician_id AS BIGINT) IS NULL OR ea.technician_id = CAST(:technician_id AS BIGINT)) ORDER BY er.created_at DESC, er.id DESC")
GET_EMERGENCY_REPORT_BY_ID_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.photo_problem_type_standardized, er.photo_classification_confidence, er.photo_classification_error, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.nearest_workshop_specialty, er.nearest_workshop_zone, er.nearest_workshop_distance_meters, er.audio_duration_seconds, er.audio_transcript, er.audio_transcript_status, er.audio_transcript_error, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.hora_llegada, er.latitud_llegada, er.longitud_llegada, er.sucursal_id, er.created_at, er.updated_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE er.id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR er.nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) LIMIT 1")
GET_EMERGENCY_STATUS_FOR_UPDATE_SQL = text("SELECT id, emergency_status FROM emergency_reports WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) LIMIT 1")
UPDATE_EMERGENCY_STATUS_SQL = text("UPDATE emergency_reports SET emergency_status = :emergency_status, updated_at = NOW(), hora_llegada = CASE WHEN :set_hora_llegada THEN NOW() ELSE hora_llegada END, latitud_llegada = CASE WHEN :set_hora_llegada AND CAST(:latitud_llegada AS DOUBLE PRECISION) IS NOT NULL THEN CAST(:latitud_llegada AS DOUBLE PRECISION) ELSE latitud_llegada END, longitud_llegada = CASE WHEN :set_hora_llegada AND CAST(:longitud_llegada AS DOUBLE PRECISION) IS NOT NULL THEN CAST(:longitud_llegada AS DOUBLE PRECISION) ELSE longitud_llegada END, rejection_reason = CASE WHEN :set_rejection_metadata THEN :rejection_reason WHEN :clear_rejection_metadata THEN NULL ELSE rejection_reason END, rejected_at = CASE WHEN :set_rejection_metadata THEN :rejected_at WHEN :clear_rejection_metadata THEN NULL ELSE rejected_at END WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) RETURNING id")
UPDATE_EMERGENCY_REASSIGNMENT_SQL = text("UPDATE emergency_reports SET nearest_workshop_id = :nearest_workshop_id, nearest_workshop_name = :nearest_workshop_name, nearest_workshop_specialty = :nearest_workshop_specialty, nearest_workshop_zone = :nearest_workshop_zone, nearest_workshop_distance_meters = :nearest_workshop_distance_meters, emergency_status = :emergency_status, sucursal_id = :sucursal_id WHERE id = :report_id RETURNING id")
ASSIGN_EMERGENCY_TECHNICIAN_SQL = text("INSERT INTO emergency_assignments (emergency_report_id, workshop_id, technician_id, assignment_status) VALUES (:report_id, :workshop_id, :technician_id, 'asignado') ON CONFLICT (emergency_report_id) DO UPDATE SET workshop_id = EXCLUDED.workshop_id, technician_id = EXCLUDED.technician_id, assignment_status = 'asignado', updated_at = NOW() RETURNING id, emergency_report_id, workshop_id, technician_id, assignment_status, created_at, updated_at")
DELETE_EMERGENCY_ASSIGNMENT_SQL = text("DELETE FROM emergency_assignments WHERE emergency_report_id = :report_id RETURNING id, technician_id")
DELETE_EMERGENCY_REPORT_SQL = text("DELETE FROM emergency_reports WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) RETURNING id, photo_paths, photo_urls, audio_path, audio_url")
BACKFILL_EMERGENCY_PRICES_SQL = text("UPDATE emergency_reports SET price = CASE WHEN COALESCE(problem_type_standardized, problem_type) = 'Batería' THEN 50 WHEN COALESCE(problem_type_standardized, problem_type) = 'Neumático' THEN 50 WHEN COALESCE(problem_type_standardized, problem_type) = 'Combustible' THEN 60 WHEN COALESCE(problem_type_standardized, problem_type) = 'Motor' THEN 100 WHEN COALESCE(problem_type_standardized, problem_type) = 'Sistema eléctrico' THEN 90 WHEN COALESCE(problem_type_standardized, problem_type) = 'Accidente' THEN 150 WHEN COALESCE(problem_type_standardized, problem_type) = 'Cerrajería / llaves' THEN 80 ELSE price END WHERE price IS NULL AND COALESCE(problem_type_standardized, problem_type) IN ('Batería','Neumático','Combustible','Motor','Sistema eléctrico','Accidente','Cerrajería / llaves')")
INSERT_EMERGENCY_STATUS_HISTORY_SQL = text("INSERT INTO emergency_status_history (emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation) VALUES (:emergency_id, :previous_status, :new_status, :changed_by_role, :changed_by_user_id, :observation) RETURNING id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at")
LIST_EMERGENCY_STATUS_HISTORY_SQL = text("SELECT id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at FROM emergency_status_history WHERE emergency_id = :emergency_id ORDER BY created_at ASC, id ASC")

UPSERT_DEVICE_FCM_TOKEN_SQL = text("INSERT INTO device_fcm_tokens (user_id, fcm_token, platform, is_active) VALUES (:user_id, :fcm_token, :platform, :is_active) ON CONFLICT (fcm_token) DO UPDATE SET user_id = EXCLUDED.user_id, platform = EXCLUDED.platform, is_active = EXCLUDED.is_active, updated_at = NOW() RETURNING id, user_id, fcm_token, platform, is_active, created_at, updated_at")
LIST_DEVICE_FCM_TOKENS_SQL = text("SELECT id, user_id, fcm_token, platform, is_active, created_at, updated_at FROM device_fcm_tokens WHERE user_id = :user_id ORDER BY updated_at DESC, id DESC")
LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL = text("SELECT id, user_id, fcm_token, platform, is_active, created_at, updated_at FROM device_fcm_tokens WHERE user_id = :user_id AND is_active = TRUE ORDER BY updated_at DESC, id DESC")
INSERT_EMERGENCY_TRACKING_POINT_SQL = text("INSERT INTO emergency_tracking_points (emergency_id, technician_id, latitude, longitude, source) VALUES (:emergency_id, :technician_id, :latitude, :longitude, :source) RETURNING id, emergency_id, technician_id, latitude, longitude, source, created_at")
GET_LATEST_EMERGENCY_TRACKING_POINT_SQL = text("SELECT id, emergency_id, technician_id, latitude, longitude, source, created_at FROM emergency_tracking_points WHERE emergency_id = :emergency_id ORDER BY created_at DESC, id DESC LIMIT 1")

INSERT_QUOTATION_REQUEST_SQL = text("INSERT INTO quotation_requests (emergency_id, client_id, status, requested_workshops_count, requested_at, expires_at) VALUES (:emergency_id, :client_id, 'abierto', :requested_workshops_count, NOW(), :expires_at) RETURNING id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at")
INSERT_QUOTATION_REQUEST_WORKSHOP_SQL = text("INSERT INTO quotation_request_workshops (quotation_request_id, workshop_id, status, notified_at) VALUES (:quotation_request_id, :workshop_id, 'notificado', NOW()) RETURNING id, quotation_request_id, workshop_id, status, notified_at, created_at")
INSERT_QUOTATION_OFFER_SQL = text("INSERT INTO quotation_offers (quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, expires_at) VALUES (:quotation_request_id, :workshop_id, :workshop_rating, :price, :service_description, :spare_parts, :labor_detail, :labor_cost, :spare_parts_cost, :estimated_service_time, :estimated_arrival_time, :warranty, :validity_days, :observations, :condiciones_servicio, 'enviada', :expires_at) RETURNING id, quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, created_at, expires_at")
UPDATE_QUOTATION_OFFER_SQL = text("UPDATE quotation_offers SET workshop_rating = :workshop_rating, price = :price, service_description = :service_description, spare_parts = :spare_parts, labor_detail = :labor_detail, labor_cost = :labor_cost, spare_parts_cost = :spare_parts_cost, estimated_service_time = :estimated_service_time, estimated_arrival_time = :estimated_arrival_time, warranty = :warranty, validity_days = :validity_days, observations = :observations, condiciones_servicio = :condiciones_servicio, status = 'actualizada', expires_at = :expires_at WHERE id = :offer_id AND quotation_request_id = :quotation_request_id AND workshop_id = :workshop_id RETURNING id, quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, created_at, expires_at")
GET_QUOTATION_REQUEST_BY_ID_SQL = text("SELECT id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at FROM quotation_requests WHERE id = :id LIMIT 1")
LIST_QUOTATION_REQUESTS_BY_CLIENT_SQL = text("SELECT id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at FROM quotation_requests WHERE client_id = :client_id ORDER BY created_at DESC, id DESC")
LIST_QUOTATION_REQUESTS_BY_WORKSHOP_SQL = text("SELECT qr.id, qr.emergency_id, qr.client_id, qr.status, qr.requested_workshops_count, qr.received_offers_count, qr.selected_offer_id, qr.requested_at, qr.expires_at, qr.created_at, qr.updated_at, qrw.status AS workshop_invitation_status, qrw.notified_at FROM quotation_requests qr JOIN quotation_request_workshops qrw ON qrw.quotation_request_id = qr.id WHERE qrw.workshop_id = :workshop_id AND qr.status IN ('abierto', 'con_propuestas', 'en_evaluacion') ORDER BY qr.created_at DESC, qr.id DESC")
LIST_QUOTATION_REQUESTS_BY_TENANT_SQL = text(
    """
    SELECT
        qr.id,
        qr.emergency_id,
        qr.client_id,
        qr.status,
        qr.requested_workshops_count,
        qr.received_offers_count,
        qr.selected_offer_id,
        qr.requested_at,
        qr.expires_at,
        qr.created_at,
        qr.updated_at,
        c.full_name AS client_name,
        c.phone AS client_phone,
        STRING_AGG(DISTINCT wr.workshop_name, ' | ') AS workshop_names,
        COUNT(DISTINCT qrw.workshop_id) AS visible_workshops_count,
        CASE
            WHEN CAST(:sucursal_id AS BIGINT) IS NULL
              OR selected_wr.sucursal_id = CAST(:sucursal_id AS BIGINT)
            THEN selected_wr.workshop_name
            ELSE NULL
        END AS selected_workshop_name,
        CASE
            WHEN CAST(:sucursal_id AS BIGINT) IS NULL
              OR selected_wr.sucursal_id = CAST(:sucursal_id AS BIGINT)
            THEN selected_offer.price
            ELSE NULL
        END AS selected_offer_price
    FROM quotation_requests qr
    JOIN quotation_request_workshops qrw
      ON qrw.quotation_request_id = qr.id
    JOIN workshop_registrations wr
      ON wr.id = qrw.workshop_id
    LEFT JOIN clients c
      ON c.id = qr.client_id
    LEFT JOIN quotation_offers selected_offer
      ON selected_offer.id = qr.selected_offer_id
    LEFT JOIN workshop_registrations selected_wr
      ON selected_wr.id = selected_offer.workshop_id
    WHERE (CAST(:sucursal_id AS BIGINT) IS NULL OR wr.sucursal_id = CAST(:sucursal_id AS BIGINT))
    GROUP BY
        qr.id,
        qr.emergency_id,
        qr.client_id,
        qr.status,
        qr.requested_workshops_count,
        qr.received_offers_count,
        qr.selected_offer_id,
        qr.requested_at,
        qr.expires_at,
        qr.created_at,
        qr.updated_at,
        c.full_name,
        c.phone,
        selected_wr.sucursal_id,
        selected_wr.workshop_name,
        selected_offer.price
    ORDER BY qr.created_at DESC, qr.id DESC
    """
)
LIST_QUOTATION_OFFERS_BY_REQUEST_SQL = text("SELECT qo.id, qo.quotation_request_id, qo.workshop_id, qo.workshop_rating, qo.price, qo.service_description, qo.spare_parts, qo.labor_detail, qo.labor_cost, qo.spare_parts_cost, qo.estimated_service_time, qo.estimated_arrival_time, qo.warranty, qo.validity_days, qo.observations, qo.condiciones_servicio, qo.status, qo.created_at, qo.expires_at, wr.workshop_name FROM quotation_offers qo JOIN workshop_registrations wr ON wr.id = qo.workshop_id WHERE qo.quotation_request_id = :quotation_request_id ORDER BY qo.created_at ASC, qo.id ASC")
LIST_QUOTATION_OFFERS_BY_WORKSHOP_SQL = text("SELECT qo.id, qo.quotation_request_id, qo.workshop_id, qo.workshop_rating, qo.price, qo.service_description, qo.spare_parts, qo.labor_detail, qo.labor_cost, qo.spare_parts_cost, qo.estimated_service_time, qo.estimated_arrival_time, qo.warranty, qo.validity_days, qo.observations, qo.condiciones_servicio, qo.status, qo.created_at, qo.expires_at, qr.emergency_id, qr.status AS request_status, qr.client_id AS request_client_id FROM quotation_offers qo JOIN quotation_requests qr ON qr.id = qo.quotation_request_id WHERE qo.workshop_id = :workshop_id ORDER BY qo.created_at DESC, qo.id DESC")
LIST_QUOTATION_OFFERS_BY_TENANT_SQL = text(
    """
    SELECT
        qo.id,
        qo.quotation_request_id,
        qo.workshop_id,
        qo.workshop_rating,
        qo.price,
        qo.service_description,
        qo.spare_parts,
        qo.labor_detail,
        qo.labor_cost,
        qo.spare_parts_cost,
        qo.estimated_service_time,
        qo.estimated_arrival_time,
        qo.warranty,
        qo.validity_days,
        qo.observations,
        qo.condiciones_servicio,
        qo.status,
        qo.created_at,
        qo.expires_at,
        qr.emergency_id,
        qr.status AS request_status,
        qr.client_id AS request_client_id,
        wr.workshop_name,
        c.full_name AS client_name
    FROM quotation_offers qo
    JOIN quotation_requests qr
      ON qr.id = qo.quotation_request_id
    JOIN workshop_registrations wr
      ON wr.id = qo.workshop_id
    LEFT JOIN clients c
      ON c.id = qr.client_id
    WHERE (CAST(:sucursal_id AS BIGINT) IS NULL OR wr.sucursal_id = CAST(:sucursal_id AS BIGINT))
    ORDER BY qo.created_at DESC, qo.id DESC
    """
)
SELECT_QUOTATION_OFFER_SQL = text("UPDATE quotation_requests SET selected_offer_id = :offer_id, status = 'seleccionado', updated_at = NOW() WHERE id = :quotation_request_id AND status NOT IN ('seleccionado', 'cancelado', 'expirado') RETURNING id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at")
REFRESH_QUOTATION_REQUEST_AFTER_OFFER_SQL = text(
    """
    UPDATE quotation_requests qr
    SET
        received_offers_count = counts.total_offers,
        status = CASE
            WHEN qr.status IN ('seleccionado', 'cancelado', 'expirado', 'en_evaluacion') THEN qr.status
            WHEN counts.total_offers > 0 THEN 'con_propuestas'
            ELSE 'abierto'
        END,
        updated_at = NOW()
    FROM (
        SELECT COUNT(*)::INTEGER AS total_offers
        FROM quotation_offers
        WHERE quotation_request_id = :quotation_request_id
    ) counts
    WHERE qr.id = :quotation_request_id
    RETURNING id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at
    """
)
GET_QUOTATION_OFFER_BY_ID_SQL = text("SELECT qo.id, qo.quotation_request_id, qo.workshop_id, qo.workshop_rating, qo.price, qo.service_description, qo.spare_parts, qo.labor_detail, qo.labor_cost, qo.spare_parts_cost, qo.estimated_service_time, qo.estimated_arrival_time, qo.warranty, qo.validity_days, qo.observations, qo.condiciones_servicio, qo.status, qo.created_at, qo.expires_at, wr.workshop_name FROM quotation_offers qo JOIN workshop_registrations wr ON wr.id = qo.workshop_id WHERE qo.id = :id LIMIT 1")
GET_QUOTATION_REQUEST_WORKSHOP_SQL = text("SELECT id, quotation_request_id, workshop_id, status, notified_at, created_at FROM quotation_request_workshops WHERE quotation_request_id = :quotation_request_id AND workshop_id = :workshop_id LIMIT 1")
GET_QUOTATION_OFFER_BY_REQUEST_AND_WORKSHOP_SQL = text("SELECT id, quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, created_at, expires_at FROM quotation_offers WHERE quotation_request_id = :quotation_request_id AND workshop_id = :workshop_id ORDER BY created_at DESC, id DESC LIMIT 1")
UPDATE_QUOTATION_REQUEST_WORKSHOP_STATUS_SQL = text("UPDATE quotation_request_workshops SET status = :status WHERE quotation_request_id = :quotation_request_id AND workshop_id = :workshop_id RETURNING id, quotation_request_id, workshop_id, status, notified_at, created_at")
UPDATE_QUOTATION_REQUEST_STATUS_SQL = text("UPDATE quotation_requests SET status = :status, updated_at = NOW() WHERE id = :quotation_request_id RETURNING id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at")
UPDATE_QUOTATION_OFFER_STATUS_BY_ID_SQL = text("UPDATE quotation_offers SET status = :status WHERE id = :offer_id RETURNING id")
UPDATE_OTHER_QUOTATION_OFFERS_STATUS_SQL = text("UPDATE quotation_offers SET status = :status WHERE quotation_request_id = :quotation_request_id AND id <> :selected_offer_id")
INSERT_QUOTATION_REQUEST_HISTORY_SQL = text("INSERT INTO quotation_request_history (quotation_request_id, event_type, detail, actor_role, actor_user_id) VALUES (:quotation_request_id, :event_type, :detail, :actor_role, :actor_user_id) RETURNING id, quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at")
LIST_QUOTATION_REQUEST_HISTORY_SQL = text("SELECT id, quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at FROM quotation_request_history WHERE quotation_request_id = :quotation_request_id ORDER BY created_at ASC, id ASC")
LIST_REJECTED_OFFERS_FOR_REQUEST_SQL = text("SELECT id, workshop_id, quotation_request_id FROM quotation_offers WHERE quotation_request_id = :quotation_request_id AND status = 'rechazada'")
LIST_CONTRACTED_SERVICES_BY_WORKSHOP_SQL = text("SELECT qo.id, qo.quotation_request_id, qo.workshop_id, qo.price, qo.service_description, qo.spare_parts, qo.labor_detail, qo.labor_cost, qo.spare_parts_cost, qo.estimated_service_time, qo.estimated_arrival_time, qo.warranty, qo.validity_days, qo.observations, qo.condiciones_servicio, qo.status, qo.created_at AS offer_created_at, qo.expires_at AS offer_expires_at, qr.emergency_id, qr.client_id, qr.requested_at, qr.expires_at AS request_expires_at, er.vehicle_name, er.vehicle_plate, er.problem_type, er.address, er.zone, er.latitude, er.longitude, er.description AS emergency_description, er.emergency_status, er.created_at AS emergency_created_at, er.hora_llegada, er.latitud_llegada, er.longitud_llegada, c.full_name AS client_name, c.phone AS client_phone FROM quotation_offers qo JOIN quotation_requests qr ON qr.id = qo.quotation_request_id LEFT JOIN emergency_reports er ON er.id = qr.emergency_id LEFT JOIN clients c ON c.id = qr.client_id WHERE qo.workshop_id = :workshop_id AND qo.status = 'aceptada' ORDER BY qo.created_at DESC, qo.id DESC")
LIST_CONTRACTED_SERVICES_BY_TENANT_SQL = text(
    """
    SELECT
        qo.id,
        qo.quotation_request_id,
        qo.workshop_id,
        qo.price,
        qo.service_description,
        qo.spare_parts,
        qo.labor_detail,
        qo.labor_cost,
        qo.spare_parts_cost,
        qo.estimated_service_time,
        qo.estimated_arrival_time,
        qo.warranty,
        qo.validity_days,
        qo.observations,
        qo.condiciones_servicio,
        qo.status,
        qo.created_at AS offer_created_at,
        qo.expires_at AS offer_expires_at,
        qr.emergency_id,
        qr.client_id,
        qr.requested_at,
        qr.expires_at AS request_expires_at,
        er.vehicle_name,
        er.vehicle_plate,
        er.problem_type,
        er.address,
        er.zone,
        er.latitude,
        er.longitude,
        er.description AS emergency_description,
        er.emergency_status,
        er.created_at AS emergency_created_at,
        er.hora_llegada,
        er.latitud_llegada,
        er.longitud_llegada,
        c.full_name AS client_name,
        c.phone AS client_phone,
        wr.workshop_name
    FROM quotation_offers qo
    JOIN quotation_requests qr
      ON qr.id = qo.quotation_request_id
    JOIN workshop_registrations wr
      ON wr.id = qo.workshop_id
    LEFT JOIN emergency_reports er
      ON er.id = qr.emergency_id
    LEFT JOIN clients c
      ON c.id = qr.client_id
    WHERE (CAST(:sucursal_id AS BIGINT) IS NULL OR wr.sucursal_id = CAST(:sucursal_id AS BIGINT))
      AND qo.status = 'aceptada'
    ORDER BY qo.created_at DESC, qo.id DESC
    """
)
GET_CONTRACTED_SERVICE_BY_OFFER_SQL = text("SELECT qo.id, qo.quotation_request_id, qo.workshop_id, qo.price, qo.service_description, qo.spare_parts, qo.labor_detail, qo.labor_cost, qo.spare_parts_cost, qo.estimated_service_time, qo.estimated_arrival_time, qo.warranty, qo.validity_days, qo.observations, qo.condiciones_servicio, qo.status, qo.created_at AS offer_created_at, qo.expires_at AS offer_expires_at, qr.emergency_id, qr.client_id, qr.requested_at, qr.expires_at AS request_expires_at, er.vehicle_name, er.vehicle_plate, er.problem_type, er.address, er.zone, er.latitude, er.longitude, er.description AS emergency_description, er.emergency_status, er.created_at AS emergency_created_at, er.hora_llegada, er.latitud_llegada, er.longitud_llegada, c.full_name AS client_name, c.phone AS client_phone FROM quotation_offers qo JOIN quotation_requests qr ON qr.id = qo.quotation_request_id LEFT JOIN emergency_reports er ON er.id = qr.emergency_id LEFT JOIN clients c ON c.id = qr.client_id WHERE qo.id = :offer_id AND qo.workshop_id = :workshop_id AND qo.status = 'aceptada' LIMIT 1")
QUOTATION_REQUEST_VISIBLE_IN_SUCURSAL_SQL = text(
    """
    SELECT 1
    FROM quotation_request_workshops qrw
    JOIN workshop_registrations wr
      ON wr.id = qrw.workshop_id
    WHERE qrw.quotation_request_id = :quotation_request_id
      AND wr.sucursal_id = :sucursal_id
    LIMIT 1
    """
)
UPSERT_NOTIFICATION_SQL = text("INSERT INTO notifications (user_id, title, message, is_read, payload_json) VALUES (:user_id, :title, :message, FALSE, :payload_json) RETURNING id, user_id, title, message, is_read, payload_json, created_at")
EXPIRE_QUOTATION_OFFERS_SQL = text("UPDATE quotation_offers SET status = 'expirado' WHERE status IN ('enviada', 'actualizada') AND expires_at IS NOT NULL AND expires_at <= NOW()")
EXPIRE_QUOTATION_REQUESTS_SQL = text(
    """
    UPDATE quotation_requests
    SET status = 'expirado', updated_at = NOW()
    WHERE status IN ('abierto', 'con_propuestas', 'en_evaluacion')
      AND expires_at IS NOT NULL
      AND expires_at <= NOW()
    """
)
DELETE_DUPLICATE_QUOTATION_REQUEST_WORKSHOPS_SQL = text(
    """
    DELETE FROM quotation_request_workshops
    WHERE id IN (
        SELECT id
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY quotation_request_id, workshop_id
                    ORDER BY created_at DESC, id DESC
                ) AS row_number
            FROM quotation_request_workshops
        ) ranked
        WHERE ranked.row_number > 1
    )
    """
)
DELETE_DUPLICATE_QUOTATION_OFFERS_SQL = text(
    """
    DELETE FROM quotation_offers
    WHERE id IN (
        SELECT id
        FROM (
            SELECT
                qo.id,
                ROW_NUMBER() OVER (
                    PARTITION BY qo.quotation_request_id, qo.workshop_id
                    ORDER BY
                        CASE WHEN qr.selected_offer_id = qo.id THEN 1 ELSE 0 END DESC,
                        qo.created_at DESC,
                        qo.id DESC
                ) AS row_number
            FROM quotation_offers qo
            LEFT JOIN quotation_requests qr ON qr.id = qo.quotation_request_id
        ) ranked
        WHERE ranked.row_number > 1
    )
    """
)
REFRESH_ALL_QUOTATION_REQUEST_COUNTS_SQL = text(
    """
    UPDATE quotation_requests qr
    SET
        received_offers_count = COALESCE(counts.total_offers, 0),
        status = CASE
            WHEN qr.status IN ('seleccionado', 'cancelado', 'expirado', 'en_evaluacion') THEN qr.status
            WHEN COALESCE(counts.total_offers, 0) > 0 THEN 'con_propuestas'
            ELSE 'abierto'
        END,
        updated_at = NOW()
    FROM (
        SELECT quotation_request_id, COUNT(*)::INTEGER AS total_offers
        FROM quotation_offers
        GROUP BY quotation_request_id
    ) counts
    WHERE qr.id = counts.quotation_request_id
    """
)
RESET_EMPTY_QUOTATION_REQUEST_COUNTS_SQL = text(
    """
    UPDATE quotation_requests
    SET
        received_offers_count = 0,
        status = CASE
            WHEN status IN ('seleccionado', 'cancelado', 'expirado', 'en_evaluacion') THEN status
            ELSE 'abierto'
        END,
        updated_at = NOW()
    WHERE id NOT IN (SELECT DISTINCT quotation_request_id FROM quotation_offers)
    """
)


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def init_database() -> None:
    with engine.begin() as connection:
        connection.execute(CREATE_WORKSHOPS_TABLE_SQL)
        connection.execute(CREATE_WORKSHOP_SPECIALTIES_TABLE_SQL)
        connection.execute(CREATE_TECHNICIANS_TABLE_SQL)
        connection.execute(CREATE_CLIENTS_TABLE_SQL)
        connection.execute(CREATE_VEHICLES_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_REPORTS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_ASSIGNMENTS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_STATUS_HISTORY_TABLE_SQL)
        connection.execute(CREATE_DEVICE_FCM_TOKENS_TABLE_SQL)
        connection.execute(CREATE_NOTIFICATIONS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_TRACKING_POINTS_TABLE_SQL)
        connection.execute(text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS workshop_id BIGINT"))
        connection.execute(text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS usuario_tenant_id BIGINT"))
        connection.execute(text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS email VARCHAR(160)"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS timezone VARCHAR(120)"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS utc_offset_minutes INTEGER"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS approval_status VARCHAR(30) NOT NULL DEFAULT 'pendiente'"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS availability_status VARCHAR(30) NOT NULL DEFAULT 'disponible'"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS workshop_specialties_workshop_id_idx ON workshop_specialties (workshop_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS workshop_specialties_specialty_idx ON workshop_specialties (specialty)"))
        connection.execute(text("UPDATE workshop_registrations SET approval_status = 'pendiente' WHERE approval_status IS NULL OR approval_status = ''"))
        connection.execute(text("UPDATE workshop_registrations SET availability_status = 'disponible' WHERE availability_status IS NULL OR availability_status = ''"))
        connection.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS role VARCHAR(40) DEFAULT 'client'"))
        connection.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'active'"))
        connection.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS accepted_terms BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS client_id BIGINT"))
        connection.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255)"))
        connection.execute(text("ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS photo_url VARCHAR(255)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS client_id BIGINT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS vehicle_name VARCHAR(160)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS vehicle_plate VARCHAR(40)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS problem_type VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS price INTEGER"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS emergency_status VARCHAR(30) NOT NULL DEFAULT 'pendiente'"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS problem_type_standardized VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS photo_problem_type_standardized VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS photo_classification_confidence DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS photo_classification_error TEXT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS description TEXT"))
        connection.execute(text("ALTER TABLE emergency_reports ALTER COLUMN description DROP NOT NULL"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS address VARCHAR(255)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS zone VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS nearest_workshop_id BIGINT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS nearest_workshop_name VARCHAR(160)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS nearest_workshop_specialty VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS nearest_workshop_zone VARCHAR(120)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS nearest_workshop_distance_meters DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_duration_seconds DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_transcript TEXT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_transcript_status VARCHAR(30)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_transcript_error TEXT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS photo_paths TEXT NOT NULL DEFAULT '[]'"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS photo_urls TEXT NOT NULL DEFAULT '[]'"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_path VARCHAR(255)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS audio_url VARCHAR(255)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS rejection_reason TEXT"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS local_id VARCHAR(64)"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS hora_llegada TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS latitud_llegada DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS longitud_llegada DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS emergency_reports_local_id_key ON emergency_reports (local_id) WHERE local_id IS NOT NULL"))
        connection.execute(text("ALTER TABLE emergency_status_history ADD COLUMN IF NOT EXISTS previous_status VARCHAR(50)"))
        connection.execute(text("ALTER TABLE emergency_status_history ADD COLUMN IF NOT EXISTS changed_by_role VARCHAR(50)"))
        connection.execute(text("ALTER TABLE emergency_status_history ADD COLUMN IF NOT EXISTS changed_by_user_id BIGINT"))
        connection.execute(text("ALTER TABLE emergency_status_history ADD COLUMN IF NOT EXISTS observation TEXT"))
        connection.execute(text("ALTER TABLE emergency_status_history ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(BACKFILL_EMERGENCY_PRICES_SQL)
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS user_id BIGINT"))
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS fcm_token TEXT"))
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS platform VARCHAR(40)"))
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE device_fcm_tokens ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS device_fcm_tokens_fcm_token_key ON device_fcm_tokens (fcm_token)"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id BIGINT"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS title VARCHAR(160)"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS message TEXT"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS payload_json TEXT"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS technician_id BIGINT"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'system'"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(CREATE_QUOTATION_REQUESTS_TABLE_SQL)
        connection.execute(CREATE_QUOTATION_REQUEST_WORKSHOPS_TABLE_SQL)
        connection.execute(CREATE_QUOTATION_OFFERS_TABLE_SQL)
        connection.execute(CREATE_QUOTATION_REQUEST_HISTORY_TABLE_SQL)
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS emergency_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS client_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'abierto'"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS requested_workshops_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS received_offers_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS selected_offer_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE quotation_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS quotation_request_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS workshop_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'notificado'"))
        connection.execute(text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE quotation_request_workshops ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS quotation_request_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS workshop_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS workshop_rating DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS price NUMERIC(12, 2)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS service_description TEXT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS spare_parts TEXT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS labor_detail TEXT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS labor_cost NUMERIC(12, 2)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS spare_parts_cost NUMERIC(12, 2)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS estimated_service_time VARCHAR(80)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS estimated_arrival_time VARCHAR(80)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS warranty VARCHAR(255)"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS validity_days INTEGER"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS observations TEXT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS condiciones_servicio TEXT"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'pendiente'"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE quotation_offers ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE quotation_offers ALTER COLUMN status SET DEFAULT 'enviada'"))
        connection.execute(text("UPDATE quotation_offers SET status = 'enviada' WHERE status = 'pendiente'"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS quotation_request_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS event_type VARCHAR(50)"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS detail TEXT"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS actor_role VARCHAR(50)"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS actor_user_id BIGINT"))
        connection.execute(text("ALTER TABLE quotation_request_history ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(DELETE_DUPLICATE_QUOTATION_REQUEST_WORKSHOPS_SQL)
        connection.execute(DELETE_DUPLICATE_QUOTATION_OFFERS_SQL)
        connection.execute(EXPIRE_QUOTATION_OFFERS_SQL)
        connection.execute(EXPIRE_QUOTATION_REQUESTS_SQL)
        connection.execute(REFRESH_ALL_QUOTATION_REQUEST_COUNTS_SQL)
        connection.execute(RESET_EMPTY_QUOTATION_REQUEST_COUNTS_SQL)
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_requests_emergency_id ON quotation_requests (emergency_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_requests_client_id ON quotation_requests (client_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_request_workshops_workshop_id ON quotation_request_workshops (workshop_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_request_workshops_quotation_request_id ON quotation_request_workshops (quotation_request_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_offers_workshop_id ON quotation_offers (workshop_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_offers_quotation_request_id ON quotation_offers (quotation_request_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_quotation_request_history_request_id ON quotation_request_history (quotation_request_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_quotation_request_workshops_request_workshop ON quotation_request_workshops (quotation_request_id, workshop_id)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_quotation_offers_request_workshop ON quotation_offers (quotation_request_id, workshop_id)"))

        # ---------------------------------------------------------------
        # MULTI-TENANT: crear tabla tenants, agregar tenant_id a todas las
        # tablas operativas y migrar datos existentes al tenant por defecto
        # ---------------------------------------------------------------
        connection.execute(CREATE_TENANTS_TABLE_SQL)
        connection.execute(text(
            "INSERT INTO tenants (id, nombre, descripcion, estado) "
            "VALUES (1, :nombre, 'Tenant principal del sistema', 'activo') "
            "ON CONFLICT (id) DO NOTHING"
        ), {"nombre": settings.default_tenant_name})
        connection.execute(text(
            "SELECT setval('tenants_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM tenants), 1))"
        ))

        # Agregar tenant_id a tablas operativas
        for tbl in [
            "workshop_registrations",
            "technicians",
            "clients",
            "vehicles",
            "emergency_reports",
            "emergency_assignments",
            "emergency_status_history",
            "emergency_tracking_points",
            "device_fcm_tokens",
            "notifications",
            "quotation_requests",
            "quotation_request_workshops",
            "quotation_offers",
            "quotation_request_history",
        ]:
            connection.execute(text(
                f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS tenant_id BIGINT DEFAULT 1"
            ))
            connection.execute(text(
                f"UPDATE {tbl} SET tenant_id = 1 WHERE tenant_id IS NULL"
            ))
            connection.execute(text(
                f"CREATE INDEX IF NOT EXISTS idx_{tbl}_tenant_id ON {tbl} (tenant_id)"
            ))

        for tbl in ["workshop_registrations", "technicians", "emergency_reports"]:
            connection.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS sucursal_id BIGINT"))
            connection.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{tbl}_sucursal_id ON {tbl} (sucursal_id)"))

        connection.execute(text(
            "UPDATE technicians t SET sucursal_id = wr.sucursal_id "
            "FROM workshop_registrations wr "
            "WHERE t.workshop_id = wr.id AND t.sucursal_id IS DISTINCT FROM wr.sucursal_id"
        ))
        connection.execute(text(
            "UPDATE emergency_reports er SET sucursal_id = wr.sucursal_id "
            "FROM workshop_registrations wr "
            "WHERE er.nearest_workshop_id = wr.id AND er.sucursal_id IS DISTINCT FROM wr.sucursal_id"
        ))

        # Propagar tenant_id del taller a sus técnicos (consistencia)
        connection.execute(text(
            "UPDATE technicians t SET tenant_id = wr.tenant_id "
            "FROM workshop_registrations wr "
            "WHERE t.workshop_id = wr.id AND t.tenant_id IS DISTINCT FROM wr.tenant_id"
        ))


def _one(result):
    return dict(result.mappings().one())


def _one_or_none(result):
    row = result.mappings().one_or_none()
    return dict(row) if row else None


def _sync_usuario_tenant_sucursal(connection, technician_id: int, sucursal_id: int | None) -> None:
    connection.execute(
        text(
            """
            UPDATE usuarios_tenant u
            SET sucursal_id = :sucursal_id,
                updated_at = NOW()
            FROM technicians t
            WHERE t.id = :technician_id
              AND t.usuario_tenant_id = u.id
              AND (
                u.sucursal_id IS DISTINCT FROM :sucursal_id
              )
            """
        ),
        {"technician_id": technician_id, "sucursal_id": sucursal_id},
    )


def _table_has_column(connection, table_name: str, column_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                  AND column_name = :column_name
                LIMIT 1
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _table_exists(connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _get_emergency_report_by_id(connection, report_id: int, *, nearest_workshop_id: int | None = None) -> dict[str, object] | None:
    return _one_or_none(
        connection.execute(
            GET_EMERGENCY_REPORT_BY_ID_SQL,
            {"report_id": report_id, "nearest_workshop_id": nearest_workshop_id},
        )
    )


def create_workshop_registration(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        safe_payload = dict(payload)
        safe_payload.setdefault("sucursal_id", None)
        return _one(connection.execute(INSERT_WORKSHOP_SQL, safe_payload))


def list_workshop_registrations() -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(LIST_WORKSHOPS_SQL).mappings().all()]
        specialties_by_workshop = list_specialties_by_workshops([int(row["id"]) for row in rows if row.get("id") is not None])
        for row in rows:
            workshop_id = int(row["id"])
            specialties = specialties_by_workshop.get(workshop_id)
            if specialties:
                row["specialties"] = specialties
            elif row.get("specialty"):
                row["specialties"] = [str(row["specialty"])]
            else:
                row["specialties"] = []
        return rows


def update_workshop_registration(workshop_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_WORKSHOP_SQL, {"id": workshop_id, **payload}))


def get_workshop_by_email(email: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_WORKSHOP_BY_EMAIL_SQL, {"email": email}))


def get_workshop_by_id(workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": workshop_id}))


def get_workshop_by_sucursal(sucursal_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_WORKSHOP_BY_SUCURSAL_SQL, {"sucursal_id": sucursal_id}))


def get_sucursal_by_id(sucursal_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_SUCURSAL_BY_ID_SQL, {"id": sucursal_id}))


def list_workshop_specialties(workshop_id: int) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT specialty
                FROM workshop_specialties
                WHERE workshop_id = :workshop_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"workshop_id": workshop_id},
        ).scalars().all()
    return [str(row) for row in rows]


def replace_workshop_specialties(workshop_id: int, specialties: list[str]) -> list[str]:
    normalized = [str(specialty).strip() for specialty in specialties if str(specialty).strip()]
    deduped = list(dict.fromkeys(normalized))
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM workshop_specialties WHERE workshop_id = :workshop_id"),
            {"workshop_id": workshop_id},
        )
        for specialty in deduped:
            connection.execute(
                text(
                    """
                    INSERT INTO workshop_specialties (workshop_id, specialty)
                    VALUES (:workshop_id, :specialty)
                    ON CONFLICT (workshop_id, specialty) DO NOTHING
                    """
                ),
                {"workshop_id": workshop_id, "specialty": specialty},
            )
    return deduped


def list_specialties_by_workshops(workshop_ids: list[int]) -> dict[int, list[str]]:
    deduped_ids = list(dict.fromkeys(int(workshop_id) for workshop_id in workshop_ids if workshop_id is not None))
    if not deduped_ids:
        return {}
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT workshop_id, specialty
                FROM workshop_specialties
                WHERE workshop_id = ANY(:workshop_ids)
                ORDER BY workshop_id ASC, created_at ASC, id ASC
                """
            ),
            {"workshop_ids": deduped_ids},
        ).mappings().all()
    result: dict[int, list[str]] = {}
    for row in rows:
        workshop_id = int(row["workshop_id"])
        result.setdefault(workshop_id, []).append(str(row["specialty"]))
    return result


def find_workshops_by_specialty(specialty: str) -> list[dict[str, object]]:
    normalized = specialty.strip()
    if not normalized:
        return []
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT DISTINCT wr.id,
                       wr.workshop_name,
                       wr.contact_name,
                       wr.phone,
                       wr.email,
                       wr.zone,
                       wr.specialty,
                       wr.approval_status,
                       wr.availability_status,
                       wr.password_hash,
                       wr.latitude,
                       wr.longitude,
                       wr.timezone,
                       wr.utc_offset_minutes,
                       wr.sucursal_id,
                       wr.created_at
                FROM workshop_registrations wr
                LEFT JOIN workshop_specialties ws
                  ON ws.workshop_id = wr.id
                WHERE wr.specialty = :specialty OR ws.specialty = :specialty
                ORDER BY wr.created_at DESC, wr.id DESC
                """
            ),
            {"specialty": normalized},
        ).mappings().all()
    result = [dict(row) for row in rows]
    specialties_by_workshop = list_specialties_by_workshops([int(row["id"]) for row in result if row.get("id") is not None])
    for row in result:
        workshop_id = int(row["id"])
        row["specialties"] = specialties_by_workshop.get(workshop_id, [str(row["specialty"])] if row.get("specialty") else [])
    return result


def update_workshop_approval_status_with_password(workshop_id: int, approval_status: str, password_hash: str | None) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_WORKSHOP_APPROVAL_STATUS_SQL, {"id": workshop_id, "approval_status": approval_status, "password_hash": password_hash}))


def update_workshop_password(workshop_id: int, password_hash: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_WORKSHOP_PASSWORD_SQL, {"id": workshop_id, "password_hash": password_hash}))


def delete_workshop_registration(workshop_id: int) -> bool:
    with engine.begin() as connection:
        return connection.execute(DELETE_WORKSHOP_SQL, {"id": workshop_id}).mappings().one_or_none() is not None


def create_technician(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        safe_payload = {"usuario_tenant_id": None, **dict(payload)}
        if safe_payload.get("sucursal_id") is None and safe_payload.get("workshop_id") is not None:
            workshop = _one_or_none(
                connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": safe_payload["workshop_id"]})
            )
            if workshop:
                safe_payload["sucursal_id"] = workshop.get("sucursal_id")
        created = _one(connection.execute(INSERT_TECHNICIAN_SQL, safe_payload))
        _sync_usuario_tenant_sucursal(connection, int(created["id"]), created.get("sucursal_id"))
        return created


def list_technicians() -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_sucursales = _table_exists(connection, "sucursales")
        has_usuario_tenant_id = _table_has_column(connection, "technicians", "usuario_tenant_id")
        sql = text(
            "SELECT t.id, t.workshop_id, "
            f"{'t.usuario_tenant_id' if has_usuario_tenant_id else 'NULL::BIGINT AS usuario_tenant_id'}, "
            "t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, "
            f"{'s.nombre AS sucursal_nombre' if has_sucursales else 'NULL::VARCHAR AS sucursal_nombre'}, "
            "t.created_at, t.updated_at "
            "FROM technicians t "
            f"{'LEFT JOIN sucursales s ON s.id = t.sucursal_id ' if has_sucursales else ''}"
            "ORDER BY t.updated_at DESC, t.id DESC"
        )
        return [dict(row) for row in connection.execute(sql).mappings().all()]


def list_technicians_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_sucursales = _table_exists(connection, "sucursales")
        has_usuario_tenant_id = _table_has_column(connection, "technicians", "usuario_tenant_id")
        sql = text(
            "SELECT t.id, t.workshop_id, "
            f"{'t.usuario_tenant_id' if has_usuario_tenant_id else 'NULL::BIGINT AS usuario_tenant_id'}, "
            "t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, "
            f"{'s.nombre AS sucursal_nombre' if has_sucursales else 'NULL::VARCHAR AS sucursal_nombre'}, "
            "t.created_at, t.updated_at "
            "FROM technicians t "
            f"{'LEFT JOIN sucursales s ON s.id = t.sucursal_id ' if has_sucursales else ''}"
            "WHERE t.workshop_id = :workshop_id "
            "ORDER BY t.updated_at DESC, t.id DESC"
        )
        return [dict(row) for row in connection.execute(sql, {"workshop_id": workshop_id}).mappings().all()]


def get_technician_by_workshop(technician_id: int, workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        has_sucursales = _table_exists(connection, "sucursales")
        has_usuario_tenant_id = _table_has_column(connection, "technicians", "usuario_tenant_id")
        sql = text(
            "SELECT t.id, t.workshop_id, "
            f"{'t.usuario_tenant_id' if has_usuario_tenant_id else 'NULL::BIGINT AS usuario_tenant_id'}, "
            "t.full_name, t.phone, t.email, t.specialty, t.status, t.sucursal_id, "
            f"{'s.nombre AS sucursal_nombre' if has_sucursales else 'NULL::VARCHAR AS sucursal_nombre'}, "
            "t.created_at, t.updated_at "
            "FROM technicians t "
            f"{'LEFT JOIN sucursales s ON s.id = t.sucursal_id ' if has_sucursales else ''}"
            "WHERE t.id = :id AND t.workshop_id = :workshop_id "
            "LIMIT 1"
        )
        return _one_or_none(connection.execute(sql, {"id": technician_id, "workshop_id": workshop_id}))


def get_technician_by_id(technician_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        has_tenant_id = _table_has_column(connection, "technicians", "tenant_id")
        has_sucursal_id = _table_has_column(connection, "technicians", "sucursal_id")
        has_usuario_tenant_id = _table_has_column(connection, "technicians", "usuario_tenant_id")
        has_sucursales = _table_exists(connection, "sucursales")
        sql = text(
            "SELECT t.id, t.workshop_id, "
            f"{'t.usuario_tenant_id' if has_usuario_tenant_id else 'NULL::BIGINT AS usuario_tenant_id'}, "
            "t.full_name, t.phone, t.email, t.specialty, t.status, "
            f"{'tenant_id' if has_tenant_id else 'NULL::BIGINT AS tenant_id'}, "
            f"{'t.sucursal_id' if has_sucursal_id else 'NULL::BIGINT AS sucursal_id'}, "
            f"{'s.nombre AS sucursal_nombre' if has_sucursal_id and has_sucursales else 'NULL::VARCHAR AS sucursal_nombre'}, "
            "t.created_at, t.updated_at "
            "FROM technicians t "
            f"{'LEFT JOIN sucursales s ON s.id = t.sucursal_id ' if has_sucursales else ''}"
            "WHERE t.id = :id LIMIT 1"
        )
        return _one_or_none(connection.execute(sql, {"id": technician_id}))


def update_technician(technician_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        safe_payload = dict(payload)
        if safe_payload.get("sucursal_id") is None and safe_payload.get("workshop_id") is not None:
            workshop = _one_or_none(
                connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": safe_payload["workshop_id"]})
            )
            if workshop:
                safe_payload["sucursal_id"] = workshop.get("sucursal_id")
        updated = _one_or_none(connection.execute(UPDATE_TECHNICIAN_SQL, {"id": technician_id, **safe_payload}))
        if updated:
            _sync_usuario_tenant_sucursal(connection, technician_id, updated.get("sucursal_id"))
        return updated


def update_technician_for_workshop(technician_id: int, workshop_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        safe_payload = dict(payload)
        if safe_payload.get("sucursal_id") is None:
            workshop = _one_or_none(connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": workshop_id}))
            if workshop:
                safe_payload["sucursal_id"] = workshop.get("sucursal_id")
        updated = _one_or_none(connection.execute(UPDATE_TECHNICIAN_BY_WORKSHOP_SQL, {"id": technician_id, "workshop_id": workshop_id, **safe_payload}))
        if updated:
            _sync_usuario_tenant_sucursal(connection, technician_id, updated.get("sucursal_id"))
        return updated


def delete_technician(technician_id: int) -> bool:
    with engine.begin() as connection:
        return connection.execute(DELETE_TECHNICIAN_SQL, {"id": technician_id}).mappings().one_or_none() is not None


def delete_technician_for_workshop(technician_id: int, workshop_id: int) -> bool:
    with engine.begin() as connection:
        return connection.execute(DELETE_TECHNICIAN_BY_WORKSHOP_SQL, {"id": technician_id, "workshop_id": workshop_id}).mappings().one_or_none() is not None


def create_client(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_CLIENT_SQL, payload))


def list_clients() -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_CLIENTS_SQL).mappings().all()]


def get_client_by_email(email: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_CLIENT_BY_EMAIL_SQL, {"email": email}))


def get_client_by_id(client_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_CLIENT_BY_ID_SQL, {"id": client_id}))


def update_client_status(client_id: int, status: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_CLIENT_STATUS_SQL, {"id": client_id, "status": status}))


def update_client(client_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_CLIENT_SQL, {"id": client_id, **payload}))


def update_client_password(client_id: int, password_hash: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_CLIENT_PASSWORD_SQL, {"id": client_id, "password_hash": password_hash}))


def delete_client(client_id: int) -> bool:
    with engine.begin() as connection:
        connection.execute(DELETE_CLIENT_VEHICLES_SQL, {"client_id": client_id})
        return connection.execute(DELETE_CLIENT_SQL, {"id": client_id}).mappings().one_or_none() is not None


def create_vehicle(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_VEHICLE_SQL, payload))


def list_vehicles(client_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_VEHICLES_SQL, {"client_id": client_id}).mappings().all()]


def get_vehicle_by_id(vehicle_id: int, client_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_VEHICLE_BY_ID_SQL, {"id": vehicle_id, "client_id": client_id}))


def update_vehicle(vehicle_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_VEHICLE_SQL, {"id": vehicle_id, **payload}))


def delete_vehicle(vehicle_id: int, client_id: int) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(DELETE_VEHICLE_SQL, {"id": vehicle_id, "client_id": client_id}))


def create_emergency_report(
    payload: Mapping[str, object],
    *,
    initial_history_status: str | None = None,
    changed_by_role: str | None = None,
    changed_by_user_id: int | None = None,
    observation: str | None = None,
) -> dict[str, object]:
    with engine.begin() as connection:
        safe_payload = {**payload, "local_id": payload.get("local_id"), "sucursal_id": payload.get("sucursal_id")}
        created = _one(connection.execute(INSERT_EMERGENCY_REPORT_SQL, safe_payload))
        if initial_history_status:
            connection.execute(
                INSERT_EMERGENCY_STATUS_HISTORY_SQL,
                {
                    "emergency_id": created["id"],
                    "previous_status": None,
                    "new_status": initial_history_status,
                    "changed_by_role": changed_by_role,
                    "changed_by_user_id": changed_by_user_id,
                    "observation": observation,
                },
            )
        return created


def list_emergency_reports(
    *,
    nearest_workshop_id: int | None = None,
    emergency_status: str | None = None,
    client_id: int | None = None,
    technician_id: int | None = None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            LIST_EMERGENCY_REPORTS_SQL,
            {
                "nearest_workshop_id": nearest_workshop_id,
                "emergency_status": emergency_status,
                "client_id": client_id,
                "technician_id": technician_id,
            },
        ).mappings().all()
    return [dict(row) for row in rows]


def get_emergency_report_by_id(report_id: int, *, nearest_workshop_id: int | None = None) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _get_emergency_report_by_id(connection, report_id, nearest_workshop_id=nearest_workshop_id)


def update_emergency_status(
    report_id: int,
    emergency_status: str,
    *,
    nearest_workshop_id: int | None = None,
    changed_by_role: str | None = None,
    changed_by_user_id: int | None = None,
    observation: str | None = None,
    rejection_reason: str | None = None,
    rejected_at: object | None = None,
    clear_rejection_metadata: bool = False,
    latitud_llegada: float | None = None,
    longitud_llegada: float | None = None,
) -> dict[str, object] | None:
    with engine.begin() as connection:
        current = _one_or_none(
            connection.execute(
                GET_EMERGENCY_STATUS_FOR_UPDATE_SQL,
                {"report_id": report_id, "nearest_workshop_id": nearest_workshop_id},
            )
        )
        if not current:
            return None
        connection.execute(
            UPDATE_EMERGENCY_STATUS_SQL,
            {
                "report_id": report_id,
                "emergency_status": emergency_status,
                "nearest_workshop_id": nearest_workshop_id,
                "set_hora_llegada": emergency_status == "tecnico_en_sitio",
                "latitud_llegada": latitud_llegada,
                "longitud_llegada": longitud_llegada,
                "rejection_reason": rejection_reason,
                "rejected_at": rejected_at,
                "set_rejection_metadata": rejection_reason is not None or rejected_at is not None,
                "clear_rejection_metadata": clear_rejection_metadata,
            },
        )
        connection.execute(
            INSERT_EMERGENCY_STATUS_HISTORY_SQL,
            {
                "emergency_id": report_id,
                "previous_status": current.get("emergency_status"),
                "new_status": emergency_status,
                "changed_by_role": changed_by_role,
                "changed_by_user_id": changed_by_user_id,
                "observation": observation,
            },
        )
        return _get_emergency_report_by_id(connection, report_id, nearest_workshop_id=nearest_workshop_id)


def assign_emergency_technician(report_id: int, workshop_id: int, technician_id: int) -> dict[str, object]:
    with engine.begin() as connection:
        row = _one(connection.execute(ASSIGN_EMERGENCY_TECHNICIAN_SQL, {"report_id": report_id, "workshop_id": workshop_id, "technician_id": technician_id}))
        connection.execute(UPDATE_TECHNICIAN_STATUS_SQL, {"id": technician_id, "status": "ocupado"})
    return row


def clear_emergency_assignment(report_id: int) -> dict[str, object] | None:
    with engine.begin() as connection:
        deleted = _one_or_none(connection.execute(DELETE_EMERGENCY_ASSIGNMENT_SQL, {"report_id": report_id}))
        if not deleted:
            return None
        technician_id = deleted.get("technician_id")
        if technician_id is not None:
            connection.execute(UPDATE_TECHNICIAN_STATUS_SQL, {"id": technician_id, "status": "disponible"})
        return deleted


def reassign_emergency_report_to_workshop(
    report_id: int,
    *,
    nearest_workshop_id: int,
    nearest_workshop_name: str,
    nearest_workshop_specialty: str | None,
    nearest_workshop_zone: str | None,
    nearest_workshop_distance_meters: float | None,
    sucursal_id: int | None,
    emergency_status: str,
    previous_status: str | None,
    changed_by_role: str | None,
    changed_by_user_id: int | None,
    observation: str | None,
) -> dict[str, object] | None:
    with engine.begin() as connection:
        updated = _one_or_none(
            connection.execute(
                UPDATE_EMERGENCY_REASSIGNMENT_SQL,
                {
                    "report_id": report_id,
                    "nearest_workshop_id": nearest_workshop_id,
                    "nearest_workshop_name": nearest_workshop_name,
                    "nearest_workshop_specialty": nearest_workshop_specialty,
                    "nearest_workshop_zone": nearest_workshop_zone,
                    "nearest_workshop_distance_meters": nearest_workshop_distance_meters,
                    "sucursal_id": sucursal_id,
                    "emergency_status": emergency_status,
                },
            )
        )
        if not updated:
            return None
        connection.execute(
            INSERT_EMERGENCY_STATUS_HISTORY_SQL,
            {
                "emergency_id": report_id,
                "previous_status": previous_status,
                "new_status": emergency_status,
                "changed_by_role": changed_by_role,
                "changed_by_user_id": changed_by_user_id,
                "observation": observation,
            },
        )
        return _get_emergency_report_by_id(connection, report_id)


def delete_emergency_report(report_id: int, *, nearest_workshop_id: int | None = None) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(DELETE_EMERGENCY_REPORT_SQL, {"report_id": report_id, "nearest_workshop_id": nearest_workshop_id}))


def _legacy_upsert_device_fcm_token(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(UPSERT_DEVICE_FCM_TOKEN_SQL, payload))


def _list_device_fcm_tokens_with_engine(target_engine, user_id: int) -> list[dict[str, object]]:
    with target_engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_DEVICE_FCM_TOKENS_SQL, {"user_id": user_id}).mappings().all()]


def _list_active_device_fcm_tokens_with_engine(target_engine, user_id: int) -> list[dict[str, object]]:
    with target_engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL, {"user_id": user_id}).mappings().all()]


def list_device_fcm_tokens_default(user_id: int) -> list[dict[str, object]]:
    return _list_device_fcm_tokens_with_engine(_default_engine, user_id)


def list_active_device_fcm_tokens_default(user_id: int) -> list[dict[str, object]]:
    return _list_active_device_fcm_tokens_with_engine(_default_engine, user_id)


def upsert_device_fcm_token(payload: Mapping[str, object]) -> dict[str, object] | None:
    from app.saas_master import deactivate_device_fcm_token_global, register_device_fcm_token_global

    safe_payload = dict(payload)
    if bool(safe_payload.get("is_active", True)):
        return register_device_fcm_token_global(safe_payload)
    return deactivate_device_fcm_token_global(safe_payload)


def list_device_fcm_tokens(
    *,
    user_id: int,
    role: str,
    tenant_id: int | None = None,
    tenant_slug: str | None = None,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    from app.saas_master import list_device_fcm_tokens_global

    return list_device_fcm_tokens_global(
        user_id=user_id,
        role=role,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        sucursal_id=sucursal_id,
        only_active=False,
    )


def list_active_device_fcm_tokens(
    *,
    user_id: int,
    role: str,
    tenant_id: int | None = None,
    tenant_slug: str | None = None,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    from app.saas_master import list_device_fcm_tokens_global

    return list_device_fcm_tokens_global(
        user_id=user_id,
        role=role,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        sucursal_id=sucursal_id,
        only_active=True,
    )


def create_emergency_tracking_point(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_EMERGENCY_TRACKING_POINT_SQL, payload))


def get_latest_emergency_tracking_point(emergency_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_LATEST_EMERGENCY_TRACKING_POINT_SQL, {"emergency_id": emergency_id}))


def create_emergency_status_history(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_EMERGENCY_STATUS_HISTORY_SQL, payload))


def list_emergency_status_history(emergency_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_EMERGENCY_STATUS_HISTORY_SQL,
                {"emergency_id": emergency_id},
            ).mappings().all()
        ]


def get_emergency_report_by_local_id(local_id: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_EMERGENCY_BY_LOCAL_ID_SQL, {"local_id": local_id}))


def create_quotation_request(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        request = _one(connection.execute(INSERT_QUOTATION_REQUEST_SQL, payload))
        connection.execute(
            INSERT_QUOTATION_REQUEST_HISTORY_SQL,
            {
                "quotation_request_id": request["id"],
                "event_type": "solicitud_creada",
                "detail": "Solicitud de cotización creada y enviada a talleres compatibles",
                "actor_role": "system",
                "actor_user_id": payload.get("client_id"),
            },
        )
        return request


def create_quotation_request_workshop(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_QUOTATION_REQUEST_WORKSHOP_SQL, payload))


def create_quotation_offer(quotation_request_id: int, payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        offer = _one(connection.execute(INSERT_QUOTATION_OFFER_SQL, {"quotation_request_id": quotation_request_id, **payload}))
        connection.execute(
            UPDATE_QUOTATION_REQUEST_WORKSHOP_STATUS_SQL,
            {
                "quotation_request_id": quotation_request_id,
                "workshop_id": payload["workshop_id"],
                "status": "respondido",
            },
        )
        connection.execute(REFRESH_QUOTATION_REQUEST_AFTER_OFFER_SQL, {"quotation_request_id": quotation_request_id})
        connection.execute(
            INSERT_QUOTATION_REQUEST_HISTORY_SQL,
            {
                "quotation_request_id": quotation_request_id,
                "event_type": "cotizacion_enviada",
                "detail": f"Cotización enviada por el taller {payload['workshop_id']}",
                "actor_role": "workshop",
                "actor_user_id": payload["workshop_id"],
            },
        )
        return _one_or_none(connection.execute(GET_QUOTATION_OFFER_BY_ID_SQL, {"id": offer["id"]})) or offer


def get_quotation_request_by_id(quotation_id: int) -> dict[str, object] | None:
    expire_quotations()
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_QUOTATION_REQUEST_BY_ID_SQL, {"id": quotation_id}))


def list_quotation_requests_by_client(client_id: int) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_QUOTATION_REQUESTS_BY_CLIENT_SQL, {"client_id": client_id}).mappings().all()]


def list_quotation_requests_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_QUOTATION_REQUESTS_BY_WORKSHOP_SQL, {"workshop_id": workshop_id}).mappings().all()]


def list_quotation_requests_by_tenant(
    tenant_id: int,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_QUOTATION_REQUESTS_BY_TENANT_SQL,
                {"tenant_id": tenant_id, "sucursal_id": sucursal_id},
            ).mappings().all()
        ]


def list_quotation_offers_by_request(quotation_request_id: int) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_QUOTATION_OFFERS_BY_REQUEST_SQL, {"quotation_request_id": quotation_request_id}).mappings().all()]


def list_quotation_offers_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_QUOTATION_OFFERS_BY_WORKSHOP_SQL, {"workshop_id": workshop_id}).mappings().all()]


def list_quotation_offers_by_tenant(
    tenant_id: int,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_QUOTATION_OFFERS_BY_TENANT_SQL,
                {"tenant_id": tenant_id, "sucursal_id": sucursal_id},
            ).mappings().all()
        ]


def select_quotation_offer(quotation_request_id: int, offer_id: int) -> dict[str, object] | None:
    with engine.begin() as connection:
        updated = _one_or_none(connection.execute(SELECT_QUOTATION_OFFER_SQL, {"quotation_request_id": quotation_request_id, "offer_id": offer_id}))
        if not updated:
            return None
        connection.execute(UPDATE_QUOTATION_OFFER_STATUS_BY_ID_SQL, {"offer_id": offer_id, "status": "aceptada"})
        connection.execute(
            UPDATE_OTHER_QUOTATION_OFFERS_STATUS_SQL,
            {
                "quotation_request_id": quotation_request_id,
                "selected_offer_id": offer_id,
                "status": "rechazada",
            },
        )
        connection.execute(
            INSERT_QUOTATION_REQUEST_HISTORY_SQL,
            {
                "quotation_request_id": quotation_request_id,
                "event_type": "cotizacion_aceptada",
                "detail": f"Se aceptó la cotización {offer_id}",
                "actor_role": "client",
                "actor_user_id": updated.get("client_id"),
            },
        )
        return updated


def get_quotation_offer_by_id(offer_id: int) -> dict[str, object] | None:
    expire_quotations()
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_QUOTATION_OFFER_BY_ID_SQL, {"id": offer_id}))


def get_quotation_request_workshop(quotation_request_id: int, workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(
            connection.execute(
                GET_QUOTATION_REQUEST_WORKSHOP_SQL,
                {"quotation_request_id": quotation_request_id, "workshop_id": workshop_id},
            )
        )


def get_quotation_offer_by_request_and_workshop(quotation_request_id: int, workshop_id: int) -> dict[str, object] | None:
    expire_quotations()
    with engine.connect() as connection:
        return _one_or_none(
            connection.execute(
                GET_QUOTATION_OFFER_BY_REQUEST_AND_WORKSHOP_SQL,
                {"quotation_request_id": quotation_request_id, "workshop_id": workshop_id},
            )
        )


def update_quotation_offer(quotation_request_id: int, offer_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        updated = _one_or_none(
            connection.execute(
                UPDATE_QUOTATION_OFFER_SQL,
                {"quotation_request_id": quotation_request_id, "offer_id": offer_id, **payload},
            )
        )
        if not updated:
            return None
        connection.execute(
            INSERT_QUOTATION_REQUEST_HISTORY_SQL,
            {
                "quotation_request_id": quotation_request_id,
                "event_type": "cotizacion_actualizada",
                "detail": f"Cotización {offer_id} actualizada por el taller {payload['workshop_id']}",
                "actor_role": "workshop",
                "actor_user_id": payload["workshop_id"],
            },
        )
        return _one_or_none(connection.execute(GET_QUOTATION_OFFER_BY_ID_SQL, {"id": offer_id})) or updated


def update_quotation_request_status(quotation_request_id: int, status_value: str) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(
            connection.execute(
                UPDATE_QUOTATION_REQUEST_STATUS_SQL,
                {"quotation_request_id": quotation_request_id, "status": status_value},
            )
        )


def create_quotation_request_history(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_QUOTATION_REQUEST_HISTORY_SQL, payload))


def list_quotation_request_history(quotation_request_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_QUOTATION_REQUEST_HISTORY_SQL,
                {"quotation_request_id": quotation_request_id},
            ).mappings().all()
        ]


def list_rejected_offers_for_request(quotation_request_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_REJECTED_OFFERS_FOR_REQUEST_SQL,
                {"quotation_request_id": quotation_request_id},
            ).mappings().all()
        ]


def list_contracted_services(workshop_id: int) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_CONTRACTED_SERVICES_BY_WORKSHOP_SQL,
                {"workshop_id": workshop_id},
            ).mappings().all()
        ]


def list_contracted_services_by_tenant(
    tenant_id: int,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    expire_quotations()
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                LIST_CONTRACTED_SERVICES_BY_TENANT_SQL,
                {"tenant_id": tenant_id, "sucursal_id": sucursal_id},
            ).mappings().all()
        ]


def get_contracted_service(offer_id: int, workshop_id: int) -> dict[str, object] | None:
    expire_quotations()
    with engine.connect() as connection:
        return _one_or_none(
            connection.execute(
                GET_CONTRACTED_SERVICE_BY_OFFER_SQL,
                {"offer_id": offer_id, "workshop_id": workshop_id},
            )
        )


def quotation_request_visible_in_sucursal(quotation_id: int, sucursal_id: int) -> bool:
    expire_quotations()
    with engine.connect() as connection:
        return (
            connection.execute(
                QUOTATION_REQUEST_VISIBLE_IN_SUCURSAL_SQL,
                {"quotation_id": quotation_id, "sucursal_id": sucursal_id},
            ).scalar_one_or_none()
            is not None
        )


def create_notification(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(UPSERT_NOTIFICATION_SQL, payload))


def expire_quotations() -> None:
    with engine.begin() as connection:
        connection.execute(EXPIRE_QUOTATION_OFFERS_SQL)
        connection.execute(EXPIRE_QUOTATION_REQUESTS_SQL)


# =============================================================================
# MULTI-TENANT: funciones filtradas por tenant_id
# =============================================================================

def list_workshops_by_tenant(
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_tenant_id = _table_has_column(connection, "workshop_registrations", "tenant_id")
        has_sucursal_id = _table_has_column(connection, "workshop_registrations", "sucursal_id")
        where_parts: list[str] = []
        params: dict[str, object] = {}
        if tenant_id is not None and has_tenant_id:
            where_parts.append("tenant_id = CAST(:tenant_id AS BIGINT)")
            params["tenant_id"] = tenant_id
        if sucursal_id is not None and has_sucursal_id:
            where_parts.append("sucursal_id = CAST(:sucursal_id AS BIGINT)")
            params["sucursal_id"] = sucursal_id
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = text(
            "SELECT id, workshop_name, contact_name, phone, email, zone, specialty, "
            "approval_status, availability_status, password_hash, latitude, longitude, "
            "timezone, utc_offset_minutes, "
            f"{'tenant_id' if has_tenant_id else 'NULL::BIGINT AS tenant_id'}, "
            f"{'sucursal_id' if has_sucursal_id else 'NULL::BIGINT AS sucursal_id'}, "
            "created_at "
            "FROM workshop_registrations "
            f"{where_clause} "
            "ORDER BY created_at DESC, id DESC"
        )
        return [dict(row) for row in connection.execute(sql, params).mappings().all()]


def list_technicians_by_tenant(
    tenant_id: int | None = None,
    sucursal_id: int | None = None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_tenant_id = _table_has_column(connection, "technicians", "tenant_id")
        has_sucursal_id = _table_has_column(connection, "technicians", "sucursal_id")
        has_usuario_tenant_id = _table_has_column(connection, "technicians", "usuario_tenant_id")
        has_sucursales = _table_exists(connection, "sucursales")
        where_parts: list[str] = []
        params: dict[str, object] = {}
        if tenant_id is not None and has_tenant_id:
            where_parts.append("t.tenant_id = CAST(:tenant_id AS BIGINT)")
            params["tenant_id"] = tenant_id
        if sucursal_id is not None and has_sucursal_id:
            where_parts.append("t.sucursal_id = CAST(:sucursal_id AS BIGINT)")
            params["sucursal_id"] = sucursal_id
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = text(
            "SELECT t.id, t.workshop_id, "
            f"{'t.usuario_tenant_id' if has_usuario_tenant_id else 'NULL::BIGINT AS usuario_tenant_id'}, "
            "t.full_name, t.phone, t.email, t.specialty, t.status, "
            f"{'t.tenant_id' if has_tenant_id else 'NULL::BIGINT AS tenant_id'}, "
            f"{'t.sucursal_id' if has_sucursal_id else 'NULL::BIGINT AS sucursal_id'}, "
            f"{'s.nombre AS sucursal_nombre' if has_sucursal_id and has_sucursales else 'NULL::VARCHAR AS sucursal_nombre'}, "
            "t.created_at, t.updated_at "
            "FROM technicians t "
            f"{'LEFT JOIN sucursales s ON s.id = t.sucursal_id ' if has_sucursales else ''}"
            f"{where_clause} "
            "ORDER BY t.updated_at DESC, t.id DESC"
        )
        return [dict(row) for row in connection.execute(sql, params).mappings().all()]


def list_clients_by_tenant(tenant_id: int | None = None) -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_tenant_id = _table_has_column(connection, "clients", "tenant_id")
        where_clause = "WHERE tenant_id = CAST(:tenant_id AS BIGINT)" if tenant_id is not None and has_tenant_id else ""
        params = {"tenant_id": tenant_id} if tenant_id is not None and has_tenant_id else {}
        sql = text(
            "SELECT id, identity_card, full_name, email, phone, role, status, accepted_terms, "
            f"{'tenant_id' if has_tenant_id else 'NULL::BIGINT AS tenant_id'}, "
            "created_at, updated_at "
            "FROM clients "
            f"{where_clause} "
            "ORDER BY created_at DESC, id DESC"
        )
        return [dict(row) for row in connection.execute(sql, params).mappings().all()]


def list_emergency_reports_by_tenant(
    *,
    nearest_workshop_id: int | None = None,
    tenant_id: int | None = None,
    emergency_status: str | None = None,
    sucursal_id: int | None = None,
    client_id: int | None = None,
    technician_id: int | None = None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        has_tenant_id = _table_has_column(connection, "emergency_reports", "tenant_id")
        has_sucursal_id = _table_has_column(connection, "emergency_reports", "sucursal_id")
        where_parts = [
            "(CAST(:nearest_workshop_id AS BIGINT) IS NULL OR er.nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT))",
            "(CAST(:emergency_status AS VARCHAR(30)) IS NULL OR er.emergency_status = CAST(:emergency_status AS VARCHAR(30)))",
            "(CAST(:client_id AS BIGINT) IS NULL OR er.client_id = CAST(:client_id AS BIGINT))",
            "(CAST(:technician_id AS BIGINT) IS NULL OR ea.technician_id = CAST(:technician_id AS BIGINT))",
        ]
        params: dict[str, object] = {
            "nearest_workshop_id": nearest_workshop_id,
            "emergency_status": emergency_status,
            "client_id": client_id,
            "technician_id": technician_id,
        }
        if tenant_id is not None and has_tenant_id:
            where_parts.append("er.tenant_id = CAST(:tenant_id AS BIGINT)")
            params["tenant_id"] = tenant_id
        if sucursal_id is not None:
            where_parts.append(
                "er.sucursal_id = CAST(:sucursal_id AS BIGINT)"
                if has_sucursal_id
                else "wr.sucursal_id = CAST(:sucursal_id AS BIGINT)"
            )
            params["sucursal_id"] = sucursal_id
        sql = text(
            "SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, "
            "er.price, er.emergency_status, er.problem_type_standardized, er.photo_problem_type_standardized, "
            "er.photo_classification_confidence, er.photo_classification_error, er.description, "
            "er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, "
            "er.nearest_workshop_specialty, er.nearest_workshop_zone, er.nearest_workshop_distance_meters, "
            "er.audio_duration_seconds, er.audio_transcript, er.audio_transcript_status, er.audio_transcript_error, "
            "er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, "
            "er.hora_llegada, er.latitud_llegada, er.longitud_llegada, er.created_at, er.updated_at, "
            f"{'er.tenant_id' if has_tenant_id else 'NULL::BIGINT AS tenant_id'}, "
            f"{'er.sucursal_id' if has_sucursal_id else 'wr.sucursal_id AS sucursal_id'}, "
            "c.full_name AS client_name, "
            "ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, "
            "t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, "
            "t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty "
            "FROM emergency_reports er "
            "LEFT JOIN clients c ON c.id = er.client_id "
            "LEFT JOIN workshop_registrations wr ON wr.id = er.nearest_workshop_id "
            "LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id "
            "LEFT JOIN technicians t ON t.id = ea.technician_id "
            f"WHERE {' AND '.join(where_parts)} "
            "ORDER BY er.created_at DESC, er.id DESC"
        )
        rows = connection.execute(sql, params).mappings().all()
    return [dict(row) for row in rows]


# =============================================================================
# MULTI-TENANT: CRUD de tenants
# =============================================================================

def create_tenant(nombre: str, descripcion: str | None, estado: str = "activo") -> dict[str, object]:
    sql = text(
        "INSERT INTO tenants (nombre, descripcion, estado) VALUES (:nombre, :descripcion, :estado) "
        "RETURNING id, nombre, descripcion, estado, created_at, updated_at"
    )
    with engine.begin() as connection:
        return _one(connection.execute(sql, {"nombre": nombre, "descripcion": descripcion, "estado": estado}))


def list_tenants() -> list[dict[str, object]]:
    sql = text("SELECT id, nombre, descripcion, estado, created_at, updated_at FROM tenants ORDER BY id ASC")
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(sql).mappings().all()]


def get_tenant_by_id(tenant_id: int) -> dict[str, object] | None:
    sql = text("SELECT id, nombre, descripcion, estado, created_at, updated_at FROM tenants WHERE id = :id LIMIT 1")
    with engine.connect() as connection:
        return _one_or_none(connection.execute(sql, {"id": tenant_id}))


def update_tenant(tenant_id: int, nombre: str, descripcion: str | None, estado: str) -> dict[str, object] | None:
    sql = text(
        "UPDATE tenants SET nombre = :nombre, descripcion = :descripcion, estado = :estado, updated_at = NOW() "
        "WHERE id = :id "
        "RETURNING id, nombre, descripcion, estado, created_at, updated_at"
    )
    with engine.begin() as connection:
        return _one_or_none(connection.execute(sql, {"id": tenant_id, "nombre": nombre, "descripcion": descripcion, "estado": estado}))


def delete_tenant(tenant_id: int) -> bool:
    sql = text("DELETE FROM tenants WHERE id = :id AND id != 1 RETURNING id")
    with engine.begin() as connection:
        return connection.execute(sql, {"id": tenant_id}).mappings().one_or_none() is not None


def get_tenant_kpis(tenant_id: int) -> dict[str, object]:
    sql = text(
        "SELECT "
        "COUNT(*) FILTER (WHERE er.tenant_id = :tenant_id) AS total_emergencias, "
        "COUNT(*) FILTER (WHERE er.tenant_id = :tenant_id AND er.emergency_status IN ('solicitud_recibida','en_revision')) AS pendientes, "
        "COUNT(*) FILTER (WHERE er.tenant_id = :tenant_id AND er.emergency_status = 'servicio_finalizado') AS finalizadas, "
        "COUNT(*) FILTER (WHERE er.tenant_id = :tenant_id AND er.emergency_status = 'solicitud_cancelada') AS canceladas, "
        "COUNT(*) FILTER (WHERE er.tenant_id = :tenant_id AND er.emergency_status IN ('auxilio_asignado','auxilio_en_camino','servicio_en_proceso')) AS en_atencion, "
        "COALESCE(SUM(er.price) FILTER (WHERE er.tenant_id = :tenant_id AND er.emergency_status = 'servicio_finalizado'), 0) AS ingresos_total "
        "FROM emergency_reports er"
    )
    workshops_sql = text(
        "SELECT COUNT(*) AS total_talleres, "
        "COUNT(*) FILTER (WHERE approval_status = 'activo') AS talleres_activos "
        "FROM workshop_registrations WHERE tenant_id = :tenant_id"
    )
    technicians_sql = text(
        "SELECT COUNT(*) AS total_tecnicos, "
        "COUNT(*) FILTER (WHERE t.status = 'disponible') AS tecnicos_disponibles "
        "FROM technicians t WHERE t.tenant_id = :tenant_id"
    )
    quotations_sql = text(
        "SELECT "
        "COUNT(*) FILTER (WHERE qo.status = 'aceptada') AS cotizaciones_aceptadas, "
        "COUNT(*) FILTER (WHERE qo.status = 'rechazada') AS cotizaciones_rechazadas "
        "FROM quotation_offers qo "
        "JOIN quotation_requests qr ON qr.id = qo.quotation_request_id "
        "JOIN emergency_reports er ON er.id = qr.emergency_id "
        "WHERE er.tenant_id = :tenant_id"
    )
    with engine.connect() as connection:
        er_row = dict(connection.execute(sql, {"tenant_id": tenant_id}).mappings().one())
        ws_row = dict(connection.execute(workshops_sql, {"tenant_id": tenant_id}).mappings().one())
        tc_row = dict(connection.execute(technicians_sql, {"tenant_id": tenant_id}).mappings().one())
        qt_row = dict(connection.execute(quotations_sql, {"tenant_id": tenant_id}).mappings().one())
    return {**er_row, **ws_row, **tc_row, **qt_row}
