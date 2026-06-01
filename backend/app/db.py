from collections.abc import Mapping

from sqlalchemy import create_engine, text

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": settings.postgres_connect_timeout},
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
        password_hash VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        timezone VARCHAR(120),
        utc_offset_minutes INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
)
CREATE_TECHNICIANS_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS technicians (
        id BIGSERIAL PRIMARY KEY,
        workshop_id BIGINT REFERENCES workshop_registrations(id) ON DELETE CASCADE,
        full_name VARCHAR(160) NOT NULL,
        phone VARCHAR(40) NOT NULL,
        email VARCHAR(160) NOT NULL DEFAULT '',
        specialty VARCHAR(120) NOT NULL,
        status VARCHAR(30) NOT NULL,
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
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

INSERT_WORKSHOP_SQL = text("INSERT INTO workshop_registrations (workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes) VALUES (:workshop_name, :contact_name, :phone, :email, :zone, :specialty, :approval_status, :password_hash, :latitude, :longitude, :timezone, :utc_offset_minutes) RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at")
LIST_WORKSHOPS_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at FROM workshop_registrations ORDER BY created_at DESC, id DESC")
UPDATE_WORKSHOP_SQL = text("UPDATE workshop_registrations SET workshop_name = :workshop_name, contact_name = :contact_name, phone = :phone, email = :email, zone = :zone, specialty = :specialty, approval_status = COALESCE(:approval_status, approval_status), password_hash = COALESCE(:password_hash, password_hash), latitude = :latitude, longitude = :longitude, timezone = :timezone, utc_offset_minutes = :utc_offset_minutes WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at")
UPDATE_WORKSHOP_APPROVAL_STATUS_SQL = text("UPDATE workshop_registrations SET approval_status = :approval_status, password_hash = COALESCE(:password_hash, password_hash) WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at")
UPDATE_WORKSHOP_PASSWORD_SQL = text("UPDATE workshop_registrations SET password_hash = :password_hash WHERE id = :id RETURNING id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at")
GET_WORKSHOP_BY_EMAIL_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at FROM workshop_registrations WHERE email = :email LIMIT 1")
GET_WORKSHOP_BY_ID_SQL = text("SELECT id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at FROM workshop_registrations WHERE id = :id LIMIT 1")
DELETE_WORKSHOP_SQL = text("DELETE FROM workshop_registrations WHERE id = :id RETURNING id")

INSERT_TECHNICIAN_SQL = text("INSERT INTO technicians (workshop_id, full_name, phone, email, specialty, status) VALUES (:workshop_id, :full_name, :phone, :email, :specialty, :status) RETURNING id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at")
LIST_TECHNICIANS_SQL = text("SELECT id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at FROM technicians ORDER BY updated_at DESC, id DESC")
LIST_TECHNICIANS_BY_WORKSHOP_SQL = text("SELECT id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at FROM technicians WHERE workshop_id = :workshop_id ORDER BY updated_at DESC, id DESC")
GET_TECHNICIAN_BY_WORKSHOP_SQL = text("SELECT id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at FROM technicians WHERE id = :id AND workshop_id = :workshop_id LIMIT 1")
UPDATE_TECHNICIAN_SQL = text("UPDATE technicians SET workshop_id = COALESCE(:workshop_id, workshop_id), full_name = :full_name, phone = :phone, email = :email, specialty = :specialty, status = :status, updated_at = NOW() WHERE id = :id RETURNING id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at")
UPDATE_TECHNICIAN_STATUS_SQL = text("UPDATE technicians SET status = :status, updated_at = NOW() WHERE id = :id RETURNING id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at")
UPDATE_TECHNICIAN_BY_WORKSHOP_SQL = text("UPDATE technicians SET full_name = :full_name, phone = :phone, email = :email, specialty = :specialty, status = :status, updated_at = NOW() WHERE id = :id AND workshop_id = :workshop_id RETURNING id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at")
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

INSERT_EMERGENCY_REPORT_SQL = text("INSERT INTO emergency_reports (local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at) VALUES (:local_id, :client_id, :vehicle_name, :vehicle_plate, :problem_type, :price, :emergency_status, :problem_type_standardized, :photo_problem_type_standardized, :photo_classification_confidence, :photo_classification_error, :description, :latitude, :longitude, :address, :zone, :nearest_workshop_id, :nearest_workshop_name, :nearest_workshop_specialty, :nearest_workshop_zone, :nearest_workshop_distance_meters, :audio_duration_seconds, :audio_transcript, :audio_transcript_status, :audio_transcript_error, :photo_paths, :photo_urls, :audio_path, :audio_url, :rejection_reason, :rejected_at) RETURNING id, local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at, created_at")
GET_EMERGENCY_BY_LOCAL_ID_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.created_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE er.local_id = :local_id LIMIT 1")
LIST_EMERGENCY_REPORTS_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.photo_problem_type_standardized, er.photo_classification_confidence, er.photo_classification_error, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.nearest_workshop_specialty, er.nearest_workshop_zone, er.nearest_workshop_distance_meters, er.audio_duration_seconds, er.audio_transcript, er.audio_transcript_status, er.audio_transcript_error, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.created_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR er.nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) AND (CAST(:emergency_status AS VARCHAR(30)) IS NULL OR er.emergency_status = CAST(:emergency_status AS VARCHAR(30))) ORDER BY er.created_at DESC, er.id DESC")
GET_EMERGENCY_REPORT_BY_ID_SQL = text("SELECT er.id, er.local_id, er.client_id, er.vehicle_name, er.vehicle_plate, er.problem_type, er.price, er.emergency_status, er.problem_type_standardized, er.photo_problem_type_standardized, er.photo_classification_confidence, er.photo_classification_error, er.description, er.latitude, er.longitude, er.address, er.zone, er.nearest_workshop_id, er.nearest_workshop_name, er.nearest_workshop_specialty, er.nearest_workshop_zone, er.nearest_workshop_distance_meters, er.audio_duration_seconds, er.audio_transcript, er.audio_transcript_status, er.audio_transcript_error, er.photo_paths, er.photo_urls, er.audio_path, er.audio_url, er.rejection_reason, er.rejected_at, er.created_at, c.full_name AS client_name, ea.id AS assignment_id, ea.assignment_status, ea.technician_id AS assigned_technician_id, t.full_name AS assigned_technician_name, t.phone AS assigned_technician_phone, t.email AS assigned_technician_email, t.specialty AS assigned_technician_specialty FROM emergency_reports er LEFT JOIN clients c ON c.id = er.client_id LEFT JOIN emergency_assignments ea ON ea.emergency_report_id = er.id LEFT JOIN technicians t ON t.id = ea.technician_id WHERE er.id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR er.nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) LIMIT 1")
GET_EMERGENCY_STATUS_FOR_UPDATE_SQL = text("SELECT id, emergency_status FROM emergency_reports WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) LIMIT 1")
UPDATE_EMERGENCY_STATUS_SQL = text("UPDATE emergency_reports SET emergency_status = :emergency_status, rejection_reason = CASE WHEN :set_rejection_metadata THEN :rejection_reason WHEN :clear_rejection_metadata THEN NULL ELSE rejection_reason END, rejected_at = CASE WHEN :set_rejection_metadata THEN :rejected_at WHEN :clear_rejection_metadata THEN NULL ELSE rejected_at END WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) RETURNING id")
UPDATE_EMERGENCY_REASSIGNMENT_SQL = text("UPDATE emergency_reports SET nearest_workshop_id = :nearest_workshop_id, nearest_workshop_name = :nearest_workshop_name, nearest_workshop_specialty = :nearest_workshop_specialty, nearest_workshop_zone = :nearest_workshop_zone, nearest_workshop_distance_meters = :nearest_workshop_distance_meters, emergency_status = :emergency_status WHERE id = :report_id RETURNING id")
ASSIGN_EMERGENCY_TECHNICIAN_SQL = text("INSERT INTO emergency_assignments (emergency_report_id, workshop_id, technician_id, assignment_status) VALUES (:report_id, :workshop_id, :technician_id, 'asignado') ON CONFLICT (emergency_report_id) DO UPDATE SET workshop_id = EXCLUDED.workshop_id, technician_id = EXCLUDED.technician_id, assignment_status = 'asignado', updated_at = NOW() RETURNING id, emergency_report_id, workshop_id, technician_id, assignment_status, created_at, updated_at")
DELETE_EMERGENCY_ASSIGNMENT_SQL = text("DELETE FROM emergency_assignments WHERE emergency_report_id = :report_id RETURNING id, technician_id")
DELETE_EMERGENCY_REPORT_SQL = text("DELETE FROM emergency_reports WHERE id = :report_id AND (CAST(:nearest_workshop_id AS BIGINT) IS NULL OR nearest_workshop_id = CAST(:nearest_workshop_id AS BIGINT)) RETURNING id, photo_paths, photo_urls, audio_path, audio_url")
BACKFILL_EMERGENCY_PRICES_SQL = text("UPDATE emergency_reports SET price = CASE WHEN COALESCE(problem_type_standardized, problem_type) = 'Batería' THEN 50 WHEN COALESCE(problem_type_standardized, problem_type) = 'Neumático' THEN 50 WHEN COALESCE(problem_type_standardized, problem_type) = 'Combustible' THEN 60 WHEN COALESCE(problem_type_standardized, problem_type) = 'Motor' THEN 100 WHEN COALESCE(problem_type_standardized, problem_type) = 'Sistema eléctrico' THEN 90 WHEN COALESCE(problem_type_standardized, problem_type) = 'Accidente' THEN 150 WHEN COALESCE(problem_type_standardized, problem_type) = 'Cerrajería / llaves' THEN 80 ELSE price END WHERE price IS NULL AND COALESCE(problem_type_standardized, problem_type) IN ('Batería','Neumático','Combustible','Motor','Sistema eléctrico','Accidente','Cerrajería / llaves')")
INSERT_EMERGENCY_STATUS_HISTORY_SQL = text("INSERT INTO emergency_status_history (emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation) VALUES (:emergency_id, :previous_status, :new_status, :changed_by_role, :changed_by_user_id, :observation) RETURNING id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at")
LIST_EMERGENCY_STATUS_HISTORY_SQL = text("SELECT id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at FROM emergency_status_history WHERE emergency_id = :emergency_id ORDER BY created_at ASC, id ASC")

UPSERT_DEVICE_FCM_TOKEN_SQL = text("INSERT INTO device_fcm_tokens (user_id, fcm_token, platform, is_active) VALUES (:user_id, :fcm_token, :platform, TRUE) ON CONFLICT (fcm_token) DO UPDATE SET user_id = EXCLUDED.user_id, platform = EXCLUDED.platform, is_active = TRUE, updated_at = NOW() RETURNING id, user_id, fcm_token, platform, is_active, created_at, updated_at")
LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL = text("SELECT id, user_id, fcm_token, platform, is_active, created_at, updated_at FROM device_fcm_tokens WHERE user_id = :user_id AND is_active = TRUE ORDER BY updated_at DESC, id DESC")
INSERT_EMERGENCY_TRACKING_POINT_SQL = text("INSERT INTO emergency_tracking_points (emergency_id, technician_id, latitude, longitude, source) VALUES (:emergency_id, :technician_id, :latitude, :longitude, :source) RETURNING id, emergency_id, technician_id, latitude, longitude, source, created_at")
GET_LATEST_EMERGENCY_TRACKING_POINT_SQL = text("SELECT id, emergency_id, technician_id, latitude, longitude, source, created_at FROM emergency_tracking_points WHERE emergency_id = :emergency_id ORDER BY created_at DESC, id DESC LIMIT 1")


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def init_database() -> None:
    with engine.begin() as connection:
        connection.execute(CREATE_WORKSHOPS_TABLE_SQL)
        connection.execute(CREATE_TECHNICIANS_TABLE_SQL)
        connection.execute(CREATE_CLIENTS_TABLE_SQL)
        connection.execute(CREATE_VEHICLES_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_REPORTS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_ASSIGNMENTS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_STATUS_HISTORY_TABLE_SQL)
        connection.execute(CREATE_DEVICE_FCM_TOKENS_TABLE_SQL)
        connection.execute(CREATE_EMERGENCY_TRACKING_POINTS_TABLE_SQL)
        connection.execute(text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS workshop_id BIGINT"))
        connection.execute(text("ALTER TABLE technicians ADD COLUMN IF NOT EXISTS email VARCHAR(160)"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS timezone VARCHAR(120)"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS utc_offset_minutes INTEGER"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS approval_status VARCHAR(30) NOT NULL DEFAULT 'pendiente'"))
        connection.execute(text("ALTER TABLE workshop_registrations ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))
        connection.execute(text("UPDATE workshop_registrations SET approval_status = 'pendiente' WHERE approval_status IS NULL OR approval_status = ''"))
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
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS technician_id BIGINT"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'system'"))
        connection.execute(text("ALTER TABLE emergency_tracking_points ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))


def _one(result):
    return dict(result.mappings().one())


def _one_or_none(result):
    row = result.mappings().one_or_none()
    return dict(row) if row else None


def _get_emergency_report_by_id(connection, report_id: int, *, nearest_workshop_id: int | None = None) -> dict[str, object] | None:
    return _one_or_none(
        connection.execute(
            GET_EMERGENCY_REPORT_BY_ID_SQL,
            {"report_id": report_id, "nearest_workshop_id": nearest_workshop_id},
        )
    )


def create_workshop_registration(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(INSERT_WORKSHOP_SQL, payload))


def list_workshop_registrations() -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_WORKSHOPS_SQL).mappings().all()]


def update_workshop_registration(workshop_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_WORKSHOP_SQL, {"id": workshop_id, **payload}))


def get_workshop_by_email(email: str) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_WORKSHOP_BY_EMAIL_SQL, {"email": email}))


def get_workshop_by_id(workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_WORKSHOP_BY_ID_SQL, {"id": workshop_id}))


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
        return _one(connection.execute(INSERT_TECHNICIAN_SQL, payload))


def list_technicians() -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_TECHNICIANS_SQL).mappings().all()]


def list_technicians_by_workshop(workshop_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_TECHNICIANS_BY_WORKSHOP_SQL, {"workshop_id": workshop_id}).mappings().all()]


def get_technician_by_workshop(technician_id: int, workshop_id: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        return _one_or_none(connection.execute(GET_TECHNICIAN_BY_WORKSHOP_SQL, {"id": technician_id, "workshop_id": workshop_id}))


def update_technician(technician_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_TECHNICIAN_SQL, {"id": technician_id, **payload}))


def update_technician_for_workshop(technician_id: int, workshop_id: int, payload: Mapping[str, object]) -> dict[str, object] | None:
    with engine.begin() as connection:
        return _one_or_none(connection.execute(UPDATE_TECHNICIAN_BY_WORKSHOP_SQL, {"id": technician_id, "workshop_id": workshop_id, **payload}))


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
        safe_payload = {**payload, "local_id": payload.get("local_id")}
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


def list_emergency_reports(*, nearest_workshop_id: int | None = None, emergency_status: str | None = None) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(LIST_EMERGENCY_REPORTS_SQL, {"nearest_workshop_id": nearest_workshop_id, "emergency_status": emergency_status}).mappings().all()
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


def upsert_device_fcm_token(payload: Mapping[str, object]) -> dict[str, object]:
    with engine.begin() as connection:
        return _one(connection.execute(UPSERT_DEVICE_FCM_TOKEN_SQL, payload))


def list_active_device_fcm_tokens(user_id: int) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(LIST_ACTIVE_DEVICE_FCM_TOKENS_SQL, {"user_id": user_id}).mappings().all()]


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
