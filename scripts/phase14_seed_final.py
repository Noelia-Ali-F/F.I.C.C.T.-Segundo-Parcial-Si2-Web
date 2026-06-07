#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from phase14_common import (
    FINAL_TENANTS,
    MASTER_DB,
    ROLE_ADMIN_SUCURSAL,
    ROLE_CLIENTE,
    ROLE_SUPERADMIN_TENANT,
    ROLE_TECNICO,
    connect,
    fetch_all,
    hash_password,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def preview() -> None:
    print("Preview only. No data will be inserted.\n")
    for slug, seed in FINAL_TENANTS.items():
        print(f"- {slug}: {seed.nombre}")
        print(f"  plan: {seed.plan_nombre}")
        print(f"  branches: {', '.join(branch.nombre for branch in seed.branches)}")
    print("\nSUPERADMIN_GLOBAL:")
    print("- provisto por configuracion protegida, no por seed")
    print("- correo: administrador@acb.com")
    print("- password: 123ppp+++")
    print("\nCredentials to be created:")
    print("- auxilio_norte | SUPERADMIN_TENANT | superadmin@auxilionorte.com | AuxilioNorte#2026")
    print("- auxilio_norte | ADMIN_SUCURSAL Norte | admin.norte@auxilionorte.com | AuxilioNorte#2026")
    print("- auxilio_norte | ADMIN_SUCURSAL Sur | admin.sur@auxilionorte.com | AuxilioNorte#2026")
    print("- auxilio_norte | TECNICO Norte | tecnico.norte@auxilionorte.com | AuxilioNorte#2026")
    print("- auxilio_norte | TECNICO Sur | tecnico.sur@auxilionorte.com | AuxilioNorte#2026")
    print("- auxilio_norte | CLIENTE A | cliente.a@auxilionorte.com | ClienteAuxilio#2026")
    print("- auxilio_norte | CLIENTE B | cliente.b@auxilionorte.com | ClienteAuxilio#2026")
    print("- mecanicos_express | SUPERADMIN_TENANT | superadmin@mecanicosexpress.com | MecanicosExpress#2026")
    print("- mecanicos_express | ADMIN_SUCURSAL Central | admin.central@mecanicosexpress.com | MecanicosExpress#2026")
    print("- mecanicos_express | TECNICO Central | tecnico.central@mecanicosexpress.com | MecanicosExpress#2026")
    print("- mecanicos_express | CLIENTE | cliente@mecanicosexpress.com | ClienteExpress#2026")
    print("\nThe seed will create:")
    print("1. SUPERADMIN_TENANT, ADMIN_SUCURSAL and TECNICO users in usuarios_tenant.")
    print("2. CLIENTE users in clients.")
    print("3. Workshops, technicians, vehicles, emergencies, assignments, tracking, notifications and quotations.")


def master_tenant_map() -> dict[str, dict[str, Any]]:
    rows = fetch_all(
        MASTER_DB,
        "SELECT id, slug, nombre, database_name FROM saas_tenants WHERE slug = ANY(%(slugs)s)",
        {"slugs": list(FINAL_TENANTS)},
    )
    return {str(row["slug"]): row for row in rows}


def insert_branch(cur, branch) -> int:
    cur.execute(
        """
        INSERT INTO sucursales
            (nombre, direccion, zona, ciudad, latitud, longitud, telefono, responsable, estado)
        VALUES
            (%(nombre)s, %(direccion)s, %(zona)s, 'Santa Cruz', %(latitud)s, %(longitud)s, %(telefono)s, %(responsable)s, 'activo')
        RETURNING id
        """,
        {
            "nombre": branch.nombre,
            "direccion": branch.direccion,
            "zona": branch.zona,
            "latitud": branch.latitud,
            "longitud": branch.longitud,
            "telefono": branch.telefono,
            "responsable": branch.responsable,
        },
    )
    return int(cur.fetchone()["id"])


def insert_tenant_user(cur, *, email: str, full_name: str, phone: str, password: str, role: str, sucursal_id: int | None) -> int:
    cur.execute(
        """
        INSERT INTO usuarios_tenant
            (email, full_name, phone, password_hash, role, sucursal_id, estado)
        VALUES
            (%(email)s, %(full_name)s, %(phone)s, %(password_hash)s, %(role)s, %(sucursal_id)s, 'activo')
        RETURNING id
        """,
        {
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "password_hash": hash_password(password),
            "role": role,
            "sucursal_id": sucursal_id,
        },
    )
    return int(cur.fetchone()["id"])


def insert_client(cur, *, identity_card: str, full_name: str, email: str, phone: str, password: str) -> int:
    cur.execute(
        """
        INSERT INTO clients
            (identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at)
        VALUES
            (%(identity_card)s, %(full_name)s, %(email)s, %(phone)s, %(password_hash)s, %(role)s, 'active', TRUE, NOW(), NOW())
        RETURNING id
        """,
        {
            "identity_card": identity_card,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password_hash": hash_password(password),
            "role": ROLE_CLIENTE,
        },
    )
    return int(cur.fetchone()["id"])


def insert_vehicle(cur, *, client_id: int, brand: str, model: str, year: int, plate: str, color: str, is_primary: bool) -> int:
    cur.execute(
        """
        INSERT INTO vehicles
            (client_id, brand, model, year, plate, color, is_primary, created_at)
        VALUES
            (%(client_id)s, %(brand)s, %(model)s, %(year)s, %(plate)s, %(color)s, %(is_primary)s, NOW())
        RETURNING id
        """,
        {
            "client_id": client_id,
            "brand": brand,
            "model": model,
            "year": year,
            "plate": plate,
            "color": color,
            "is_primary": is_primary,
        },
    )
    return int(cur.fetchone()["id"])


def insert_workshop(cur, *, workshop_name: str, contact_name: str, phone: str, email: str, zone: str, specialty: str, password: str, sucursal_id: int, latitud: float, longitud: float) -> int:
    cur.execute(
        """
        INSERT INTO workshop_registrations
            (workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at)
        VALUES
            (%(workshop_name)s, %(contact_name)s, %(phone)s, %(email)s, %(zone)s, %(specialty)s, 'activo', 'disponible', %(password_hash)s, %(latitud)s, %(longitud)s, 'America/La_Paz', -240, %(sucursal_id)s, NOW())
        RETURNING id
        """,
        {
            "workshop_name": workshop_name,
            "contact_name": contact_name,
            "phone": phone,
            "email": email,
            "zone": zone,
            "specialty": specialty,
            "password_hash": hash_password(password),
            "latitud": latitud,
            "longitud": longitud,
            "sucursal_id": sucursal_id,
        },
    )
    return int(cur.fetchone()["id"])


def insert_technician(
    cur,
    *,
    workshop_id: int,
    usuario_tenant_id: int | None,
    full_name: str,
    phone: str,
    email: str,
    specialty: str,
    status: str,
    sucursal_id: int,
) -> int:
    cur.execute(
        """
        INSERT INTO technicians
            (workshop_id, usuario_tenant_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at)
        VALUES
            (%(workshop_id)s, %(usuario_tenant_id)s, %(full_name)s, %(phone)s, %(email)s, %(specialty)s, %(status)s, %(sucursal_id)s, NOW(), NOW())
        RETURNING id
        """,
        {
            "workshop_id": workshop_id,
            "usuario_tenant_id": usuario_tenant_id,
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "specialty": specialty,
            "status": status,
            "sucursal_id": sucursal_id,
        },
    )
    return int(cur.fetchone()["id"])


def insert_emergency(
    cur,
    *,
    local_id: str,
    client_id: int,
    vehicle_name: str,
    vehicle_plate: str,
    problem_type: str,
    price: int,
    emergency_status: str,
    description: str,
    latitud: float,
    longitud: float,
    address: str,
    zone: str,
    workshop_id: int | None,
    workshop_name: str | None,
    workshop_specialty: str | None,
    workshop_zone: str | None,
    distance_meters: float | None,
    sucursal_id: int | None,
    created_at: datetime,
    updated_at: datetime,
    hora_llegada: datetime | None = None,
    rejection_reason: str | None = None,
) -> int:
    rejected_at = updated_at if rejection_reason else None
    cur.execute(
        """
        INSERT INTO emergency_reports (
            local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status,
            problem_type_standardized, description, latitude, longitude, address, zone,
            nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone,
            nearest_workshop_distance_meters, photo_paths, photo_urls, rejection_reason, rejected_at,
            hora_llegada, sucursal_id, created_at, updated_at
        )
        VALUES (
            %(local_id)s, %(client_id)s, %(vehicle_name)s, %(vehicle_plate)s, %(problem_type)s, %(price)s, %(emergency_status)s,
            %(problem_type)s, %(description)s, %(latitud)s, %(longitud)s, %(address)s, %(zone)s,
            %(workshop_id)s, %(workshop_name)s, %(workshop_specialty)s, %(workshop_zone)s,
            %(distance_meters)s, '[]', '[]', %(rejection_reason)s,
            %(rejected_at)s,
            %(hora_llegada)s, %(sucursal_id)s, %(created_at)s, %(updated_at)s
        )
        RETURNING id
        """,
        {
            "local_id": local_id,
            "client_id": client_id,
            "vehicle_name": vehicle_name,
            "vehicle_plate": vehicle_plate,
            "problem_type": problem_type,
            "price": price,
            "emergency_status": emergency_status,
            "description": description,
            "latitud": latitud,
            "longitud": longitud,
            "address": address,
            "zone": zone,
            "workshop_id": workshop_id,
            "workshop_name": workshop_name,
            "workshop_specialty": workshop_specialty,
            "workshop_zone": workshop_zone,
            "distance_meters": distance_meters,
            "rejection_reason": rejection_reason,
            "rejected_at": rejected_at,
            "hora_llegada": hora_llegada,
            "sucursal_id": sucursal_id,
            "created_at": created_at,
            "updated_at": updated_at,
        },
    )
    return int(cur.fetchone()["id"])


def insert_status_history(cur, *, emergency_id: int, previous_status: str | None, new_status: str, changed_by_role: str, changed_by_user_id: int, created_at: datetime, observation: str | None = None) -> None:
    cur.execute(
        """
        INSERT INTO emergency_status_history
            (emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at)
        VALUES
            (%(emergency_id)s, %(previous_status)s, %(new_status)s, %(changed_by_role)s, %(changed_by_user_id)s, %(observation)s, %(created_at)s)
        """,
        {
            "emergency_id": emergency_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "changed_by_role": changed_by_role,
            "changed_by_user_id": changed_by_user_id,
            "observation": observation,
            "created_at": created_at,
        },
    )


def insert_assignment(cur, *, emergency_id: int, workshop_id: int, technician_id: int) -> None:
    cur.execute(
        """
        INSERT INTO emergency_assignments
            (emergency_report_id, workshop_id, technician_id, assignment_status, created_at, updated_at)
        VALUES
            (%(emergency_id)s, %(workshop_id)s, %(technician_id)s, 'asignado', NOW(), NOW())
        """,
        {"emergency_id": emergency_id, "workshop_id": workshop_id, "technician_id": technician_id},
    )


def insert_tracking(cur, *, emergency_id: int, technician_id: int, latitude: float, longitude: float, source: str, created_at: datetime) -> None:
    cur.execute(
        """
        INSERT INTO emergency_tracking_points
            (emergency_id, technician_id, latitude, longitude, source, created_at)
        VALUES
            (%(emergency_id)s, %(technician_id)s, %(latitude)s, %(longitude)s, %(source)s, %(created_at)s)
        """,
        {
            "emergency_id": emergency_id,
            "technician_id": technician_id,
            "latitude": latitude,
            "longitude": longitude,
            "source": source,
            "created_at": created_at,
        },
    )


def insert_notification(cur, *, user_id: int, title: str, message: str, is_read: bool, payload_json: str | None = None) -> None:
    cur.execute(
        """
        INSERT INTO notifications
            (user_id, title, message, is_read, payload_json, created_at)
        VALUES
            (%(user_id)s, %(title)s, %(message)s, %(is_read)s, %(payload_json)s, NOW())
        """,
        {
            "user_id": user_id,
            "title": title,
            "message": message,
            "is_read": is_read,
            "payload_json": payload_json,
        },
    )


def insert_quotation_request(cur, *, emergency_id: int, client_id: int, status: str, requested_count: int, received_count: int, selected_offer_id: int | None, requested_at: datetime, expires_at: datetime) -> int:
    cur.execute(
        """
        INSERT INTO quotation_requests
            (emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at)
        VALUES
            (%(emergency_id)s, %(client_id)s, %(status)s, %(requested_count)s, %(received_count)s, %(selected_offer_id)s, %(requested_at)s, %(expires_at)s, %(requested_at)s, %(requested_at)s)
        RETURNING id
        """,
        {
            "emergency_id": emergency_id,
            "client_id": client_id,
            "status": status,
            "requested_count": requested_count,
            "received_count": received_count,
            "selected_offer_id": selected_offer_id,
            "requested_at": requested_at,
            "expires_at": expires_at,
        },
    )
    return int(cur.fetchone()["id"])


def insert_quotation_workshop(cur, *, quotation_request_id: int, workshop_id: int, status: str, notified_at: datetime) -> int:
    cur.execute(
        """
        INSERT INTO quotation_request_workshops
            (quotation_request_id, workshop_id, status, notified_at, created_at)
        VALUES
            (%(quotation_request_id)s, %(workshop_id)s, %(status)s, %(notified_at)s, %(notified_at)s)
        RETURNING id
        """,
        {
            "quotation_request_id": quotation_request_id,
            "workshop_id": workshop_id,
            "status": status,
            "notified_at": notified_at,
        },
    )
    return int(cur.fetchone()["id"])


def insert_quotation_offer(cur, *, quotation_request_id: int, workshop_id: int, price: Decimal, service_description: str, estimated_service_time: str, estimated_arrival_time: str, warranty: str, validity_days: int, observations: str, status: str, created_at: datetime) -> int:
    cur.execute(
        """
        INSERT INTO quotation_offers
            (quotation_request_id, workshop_id, price, service_description, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, status, created_at, expires_at)
        VALUES
            (%(quotation_request_id)s, %(workshop_id)s, %(price)s, %(service_description)s, %(estimated_service_time)s, %(estimated_arrival_time)s, %(warranty)s, %(validity_days)s, %(observations)s, %(status)s, %(created_at)s, %(created_at)s + INTERVAL '2 days')
        RETURNING id
        """,
        {
            "quotation_request_id": quotation_request_id,
            "workshop_id": workshop_id,
            "price": price,
            "service_description": service_description,
            "estimated_service_time": estimated_service_time,
            "estimated_arrival_time": estimated_arrival_time,
            "warranty": warranty,
            "validity_days": validity_days,
            "observations": observations,
            "status": status,
            "created_at": created_at,
        },
    )
    return int(cur.fetchone()["id"])


def insert_quotation_history(cur, *, quotation_request_id: int, event_type: str, actor_role: str, actor_user_id: int, detail: str, created_at: datetime) -> None:
    cur.execute(
        """
        INSERT INTO quotation_request_history
            (quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at)
        VALUES
            (%(quotation_request_id)s, %(event_type)s, %(detail)s, %(actor_role)s, %(actor_user_id)s, %(created_at)s)
        """,
        {
            "quotation_request_id": quotation_request_id,
            "event_type": event_type,
            "actor_role": actor_role,
            "actor_user_id": actor_user_id,
            "detail": detail,
            "created_at": created_at,
        },
    )


def seed_auxilio_norte(database_name: str, seed) -> None:
    with connect(database_name) as conn, conn.cursor() as cur:
        branch_ids = {branch.key: insert_branch(cur, branch) for branch in seed.branches}

        superadmin_id = insert_tenant_user(
            cur,
            email="superadmin@auxilionorte.com",
            full_name="Superadmin Auxilio Norte",
            phone="70010021",
            password=seed.admin_password,
            role=ROLE_SUPERADMIN_TENANT,
            sucursal_id=None,
        )
        admin_norte_id = insert_tenant_user(
            cur,
            email="admin.norte@auxilionorte.com",
            full_name="Admin Sucursal Norte",
            phone="70010022",
            password=seed.admin_password,
            role=ROLE_ADMIN_SUCURSAL,
            sucursal_id=branch_ids["norte"],
        )
        admin_sur_id = insert_tenant_user(
            cur,
            email="admin.sur@auxilionorte.com",
            full_name="Admin Sucursal Sur",
            phone="70010023",
            password=seed.admin_password,
            role=ROLE_ADMIN_SUCURSAL,
            sucursal_id=branch_ids["sur"],
        )
        tenant_tech_norte_user_id = insert_tenant_user(
            cur,
            email="tecnico.norte@auxilionorte.com",
            full_name="Tecnico Norte",
            phone="70010024",
            password=seed.admin_password,
            role=ROLE_TECNICO,
            sucursal_id=branch_ids["norte"],
        )
        tenant_tech_sur_user_id = insert_tenant_user(
            cur,
            email="tecnico.sur@auxilionorte.com",
            full_name="Tecnico Sur",
            phone="70010025",
            password=seed.admin_password,
            role=ROLE_TECNICO,
            sucursal_id=branch_ids["sur"],
        )

        client_a_id = insert_client(
            cur,
            identity_card="AN-CL-1001",
            full_name="Cliente A Auxilio Norte",
            email="cliente.a@auxilionorte.com",
            phone="70010031",
            password=seed.client_password,
        )
        client_b_id = insert_client(
            cur,
            identity_card="AN-CL-1002",
            full_name="Cliente B Auxilio Norte",
            email="cliente.b@auxilionorte.com",
            phone="70010032",
            password=seed.client_password,
        )

        insert_vehicle(cur, client_id=client_a_id, brand="Toyota", model="Hilux", year=2021, plate="AN-1001", color="Blanco", is_primary=True)
        insert_vehicle(cur, client_id=client_b_id, brand="Suzuki", model="Swift", year=2020, plate="AN-1002", color="Rojo", is_primary=True)

        ws_norte_id = insert_workshop(
            cur,
            workshop_name="Auxilio Norte Taller Norte",
            contact_name="Rosa Perez",
            phone="70010041",
            email="taller.norte@auxilionorte.com",
            zone="Norte",
            specialty="Motor",
            password=seed.workshop_password,
            sucursal_id=branch_ids["norte"],
            latitud=-17.7534,
            longitud=-63.1768,
        )
        ws_sur_id = insert_workshop(
            cur,
            workshop_name="Auxilio Norte Taller Sur",
            contact_name="Luis Arce",
            phone="70010042",
            email="taller.sur@auxilionorte.com",
            zone="Sur",
            specialty="Bateria",
            password=seed.workshop_password,
            sucursal_id=branch_ids["sur"],
            latitud=-17.8348,
            longitud=-63.1902,
        )

        tech_norte_id = insert_technician(
            cur,
            workshop_id=ws_norte_id,
            usuario_tenant_id=tenant_tech_norte_user_id,
            full_name="Tecnico Norte",
            phone="70010051",
            email="tecnico.op.norte@auxilionorte.com",
            specialty="Motor",
            status="ocupado",
            sucursal_id=branch_ids["norte"],
        )
        tech_sur_id = insert_technician(
            cur,
            workshop_id=ws_sur_id,
            usuario_tenant_id=tenant_tech_sur_user_id,
            full_name="Tecnico Sur",
            phone="70010052",
            email="tecnico.op.sur@auxilionorte.com",
            specialty="Bateria",
            status="disponible",
            sucursal_id=branch_ids["sur"],
        )

        now = utc_now()
        emergency_specs = [
            {
                "local_id": "AN-E-001",
                "client_id": client_a_id,
                "vehicle_name": "Toyota Hilux",
                "vehicle_plate": "AN-1001",
                "problem_type": "Motor",
                "price": 120,
                "status": "pendiente",
                "description": "Vehiculo no enciende",
                "lat": -17.751,
                "lng": -63.177,
                "address": "Av. Banzer km 9",
                "zone": "Norte",
                "workshop_id": None,
                "workshop_name": None,
                "specialty": None,
                "workshop_zone": None,
                "distance": None,
                "sucursal_id": branch_ids["norte"],
                "created_at": now - timedelta(days=2, hours=6),
                "updated_at": now - timedelta(days=2, hours=6),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_a_id, now - timedelta(days=2, hours=6), "Pendiente inicial"),
                ],
            },
            {
                "local_id": "AN-E-002",
                "client_id": client_b_id,
                "vehicle_name": "Suzuki Swift",
                "vehicle_plate": "AN-1002",
                "problem_type": "Bateria",
                "price": 60,
                "status": "activo",
                "description": "Bateria descargada",
                "lat": -17.829,
                "lng": -63.188,
                "address": "Canal Cotoca 4to anillo",
                "zone": "Sur",
                "workshop_id": ws_sur_id,
                "workshop_name": "Auxilio Norte Taller Sur",
                "specialty": "Bateria",
                "workshop_zone": "Sur",
                "distance": 2300.0,
                "sucursal_id": branch_ids["sur"],
                "created_at": now - timedelta(days=1, hours=8),
                "updated_at": now - timedelta(days=1, hours=7, minutes=45),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_b_id, now - timedelta(days=1, hours=8), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_sur_id, now - timedelta(days=1, hours=7, minutes=45), "Buscando taller"),
                ],
            },
            {
                "local_id": "AN-E-003",
                "client_id": client_a_id,
                "vehicle_name": "Toyota Hilux",
                "vehicle_plate": "AN-1001",
                "problem_type": "Motor",
                "price": 140,
                "status": "auxilio_asignado",
                "description": "Falla electrica en ruta",
                "lat": -17.762,
                "lng": -63.171,
                "address": "Radial 26",
                "zone": "Norte",
                "workshop_id": ws_norte_id,
                "workshop_name": "Auxilio Norte Taller Norte",
                "specialty": "Motor",
                "workshop_zone": "Norte",
                "distance": 1500.0,
                "sucursal_id": branch_ids["norte"],
                "created_at": now - timedelta(days=1, hours=4),
                "updated_at": now - timedelta(days=1, hours=3, minutes=30),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_a_id, now - timedelta(days=1, hours=4), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(days=1, hours=3, minutes=45), "Buscando taller"),
                    ("auxilio_asignado", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(days=1, hours=3, minutes=30), "Taller asignado"),
                ],
            },
            {
                "local_id": "AN-E-004",
                "client_id": client_a_id,
                "vehicle_name": "Toyota Hilux",
                "vehicle_plate": "AN-1001",
                "problem_type": "Motor",
                "price": 150,
                "status": "auxilio_en_camino",
                "description": "Asistencia en desplazamiento",
                "lat": -17.764,
                "lng": -63.173,
                "address": "4to anillo y San Martin",
                "zone": "Norte",
                "workshop_id": ws_norte_id,
                "workshop_name": "Auxilio Norte Taller Norte",
                "specialty": "Motor",
                "workshop_zone": "Norte",
                "distance": 1200.0,
                "sucursal_id": branch_ids["norte"],
                "created_at": now - timedelta(hours=6),
                "updated_at": now - timedelta(hours=5, minutes=10),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_a_id, now - timedelta(hours=6), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(hours=5, minutes=40), "Buscando taller"),
                    ("auxilio_asignado", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(hours=5, minutes=25), "Tecnico asignado"),
                    ("auxilio_en_camino", ROLE_TECNICO, tenant_tech_norte_user_id, now - timedelta(hours=5, minutes=10), "En camino"),
                ],
                "assignment": (ws_norte_id, tech_norte_id),
                "tracking": [
                    (-17.761, -63.172, now - timedelta(hours=5)),
                    (-17.762, -63.1725, now - timedelta(hours=4, minutes=40)),
                ],
            },
            {
                "local_id": "AN-E-005",
                "client_id": client_b_id,
                "vehicle_name": "Suzuki Swift",
                "vehicle_plate": "AN-1002",
                "problem_type": "Bateria",
                "price": 80,
                "status": "servicio_en_proceso",
                "description": "Cambio de bateria en sitio",
                "lat": -17.831,
                "lng": -63.189,
                "address": "Av. Santos Dumont 6to anillo",
                "zone": "Sur",
                "workshop_id": ws_sur_id,
                "workshop_name": "Auxilio Norte Taller Sur",
                "specialty": "Bateria",
                "workshop_zone": "Sur",
                "distance": 900.0,
                "sucursal_id": branch_ids["sur"],
                "created_at": now - timedelta(hours=9),
                "updated_at": now - timedelta(hours=7, minutes=20),
                "hora_llegada": now - timedelta(hours=7, minutes=30),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_b_id, now - timedelta(hours=9), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_sur_id, now - timedelta(hours=8, minutes=30), "Buscando taller"),
                    ("auxilio_asignado", ROLE_ADMIN_SUCURSAL, admin_sur_id, now - timedelta(hours=8, minutes=5), "Taller asignado"),
                    ("auxilio_en_camino", ROLE_TECNICO, tenant_tech_sur_user_id, now - timedelta(hours=7, minutes=50), "En camino"),
                    ("tecnico_en_sitio", ROLE_TECNICO, tenant_tech_sur_user_id, now - timedelta(hours=7, minutes=30), "Tecnico en sitio"),
                    ("servicio_en_proceso", ROLE_TECNICO, tenant_tech_sur_user_id, now - timedelta(hours=7, minutes=20), "En atencion"),
                ],
                "assignment": (ws_sur_id, tech_sur_id),
            },
            {
                "local_id": "AN-E-006",
                "client_id": client_a_id,
                "vehicle_name": "Toyota Hilux",
                "vehicle_plate": "AN-1001",
                "problem_type": "Motor",
                "price": 190,
                "status": "servicio_finalizado",
                "description": "Servicio finalizado con exito",
                "lat": -17.770,
                "lng": -63.175,
                "address": "Av. Cristo Redentor",
                "zone": "Norte",
                "workshop_id": ws_norte_id,
                "workshop_name": "Auxilio Norte Taller Norte",
                "specialty": "Motor",
                "workshop_zone": "Norte",
                "distance": 700.0,
                "sucursal_id": branch_ids["norte"],
                "created_at": now - timedelta(days=3),
                "updated_at": now - timedelta(days=2, hours=23),
                "hora_llegada": now - timedelta(days=2, hours=23, minutes=30),
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_a_id, now - timedelta(days=3), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(days=2, hours=23, minutes=50), "Buscando taller"),
                    ("auxilio_asignado", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(days=2, hours=23, minutes=40), "Taller asignado"),
                    ("auxilio_en_camino", ROLE_TECNICO, tenant_tech_norte_user_id, now - timedelta(days=2, hours=23, minutes=35), "En camino"),
                    ("tecnico_en_sitio", ROLE_TECNICO, tenant_tech_norte_user_id, now - timedelta(days=2, hours=23, minutes=30), "Llegada"),
                    ("servicio_en_proceso", ROLE_TECNICO, tenant_tech_norte_user_id, now - timedelta(days=2, hours=23, minutes=25), "Atendiendo"),
                    ("servicio_finalizado", ROLE_ADMIN_SUCURSAL, admin_norte_id, now - timedelta(days=2, hours=23), "Caso finalizado"),
                ],
                "assignment": (ws_norte_id, tech_norte_id),
            },
            {
                "local_id": "AN-E-007",
                "client_id": client_b_id,
                "vehicle_name": "Suzuki Swift",
                "vehicle_plate": "AN-1002",
                "problem_type": "Bateria",
                "price": 0,
                "status": "solicitud_cancelada",
                "description": "Cliente cancelo la solicitud",
                "lat": -17.826,
                "lng": -63.185,
                "address": "Doble Via la Guardia",
                "zone": "Sur",
                "workshop_id": ws_sur_id,
                "workshop_name": "Auxilio Norte Taller Sur",
                "specialty": "Bateria",
                "workshop_zone": "Sur",
                "distance": 2100.0,
                "sucursal_id": branch_ids["sur"],
                "created_at": now - timedelta(days=1, hours=2),
                "updated_at": now - timedelta(days=1, hours=1, minutes=20),
                "rejection_reason": "Cliente resolvio por cuenta propia",
                "history": [
                    ("pendiente", ROLE_CLIENTE, client_b_id, now - timedelta(days=1, hours=2), "Solicitud creada"),
                    ("activo", ROLE_ADMIN_SUCURSAL, admin_sur_id, now - timedelta(days=1, hours=1, minutes=40), "Buscando taller"),
                    ("solicitud_cancelada", ROLE_CLIENTE, client_b_id, now - timedelta(days=1, hours=1, minutes=20), "Cancelada"),
                ],
            },
        ]

        emergency_ids: dict[str, int] = {}
        for spec in emergency_specs:
            emergency_id = insert_emergency(
                cur,
                local_id=spec["local_id"],
                client_id=spec["client_id"],
                vehicle_name=spec["vehicle_name"],
                vehicle_plate=spec["vehicle_plate"],
                problem_type=spec["problem_type"],
                price=spec["price"],
                emergency_status=spec["status"],
                description=spec["description"],
                latitud=spec["lat"],
                longitud=spec["lng"],
                address=spec["address"],
                zone=spec["zone"],
                workshop_id=spec["workshop_id"],
                workshop_name=spec["workshop_name"],
                workshop_specialty=spec["specialty"],
                workshop_zone=spec["workshop_zone"],
                distance_meters=spec["distance"],
                sucursal_id=spec["sucursal_id"],
                created_at=spec["created_at"],
                updated_at=spec["updated_at"],
                hora_llegada=spec.get("hora_llegada"),
                rejection_reason=spec.get("rejection_reason"),
            )
            emergency_ids[spec["local_id"]] = emergency_id
            previous_status = None
            for new_status, role, user_id, history_at, note in spec["history"]:
                insert_status_history(
                    cur,
                    emergency_id=emergency_id,
                    previous_status=previous_status,
                    new_status=new_status,
                    changed_by_role=role,
                    changed_by_user_id=user_id,
                    created_at=history_at,
                    observation=note,
                )
                previous_status = new_status
            if "assignment" in spec:
                insert_assignment(
                    cur,
                    emergency_id=emergency_id,
                    workshop_id=spec["assignment"][0],
                    technician_id=spec["assignment"][1],
                )
            for tracking in spec.get("tracking", []):
                insert_tracking(
                    cur,
                    emergency_id=emergency_id,
                    technician_id=tech_norte_id,
                    latitude=tracking[0],
                    longitude=tracking[1],
                    source="technician_app",
                    created_at=tracking[2],
                )

        insert_notification(cur, user_id=client_a_id, title="Tecnico asignado", message="Tu caso ya tiene tecnico asignado.", is_read=False)
        insert_notification(cur, user_id=client_a_id, title="Estado actualizado", message="La emergencia AN-E-004 esta en camino.", is_read=False)
        insert_notification(cur, user_id=client_b_id, title="Caso cancelado", message="La emergencia AN-E-007 fue cancelada.", is_read=True)

        request_created_at = now - timedelta(hours=3)
        quotation_request_id = insert_quotation_request(
            cur,
            emergency_id=emergency_ids["AN-E-004"],
            client_id=client_a_id,
            status="seleccionado",
            requested_count=2,
            received_count=2,
            selected_offer_id=None,
            requested_at=request_created_at,
            expires_at=request_created_at + timedelta(days=1),
        )
        insert_quotation_workshop(cur, quotation_request_id=quotation_request_id, workshop_id=ws_norte_id, status="respondido", notified_at=request_created_at)
        insert_quotation_workshop(cur, quotation_request_id=quotation_request_id, workshop_id=ws_sur_id, status="respondido", notified_at=request_created_at)
        winning_offer_id = insert_quotation_offer(
            cur,
            quotation_request_id=quotation_request_id,
            workshop_id=ws_norte_id,
            price=Decimal("180.00"),
            service_description="Diagnostico y reparacion de arranque",
            estimated_service_time="90 min",
            estimated_arrival_time="20 min",
            warranty="30 dias",
            validity_days=2,
            observations="Incluye prueba en ruta",
            status="aceptada",
            created_at=request_created_at + timedelta(minutes=15),
        )
        insert_quotation_offer(
            cur,
            quotation_request_id=quotation_request_id,
            workshop_id=ws_sur_id,
            price=Decimal("210.00"),
            service_description="Diagnostico y reparacion de arranque",
            estimated_service_time="120 min",
            estimated_arrival_time="30 min",
            warranty="15 dias",
            validity_days=2,
            observations="Sin repuestos premium",
            status="rechazada",
            created_at=request_created_at + timedelta(minutes=20),
        )
        cur.execute(
            "UPDATE quotation_requests SET selected_offer_id = %s WHERE id = %s",
            (winning_offer_id, quotation_request_id),
        )
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="solicitud_creada", actor_role="system", actor_user_id=client_a_id, detail="Solicitud de cotizacion creada", created_at=request_created_at)
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="cotizacion_enviada", actor_role="workshop", actor_user_id=ws_norte_id, detail="Oferta enviada por taller norte", created_at=request_created_at + timedelta(minutes=15))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="cotizacion_enviada", actor_role="workshop", actor_user_id=ws_sur_id, detail="Oferta enviada por taller sur", created_at=request_created_at + timedelta(minutes=20))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="cotizacion_aceptada", actor_role=ROLE_CLIENTE, actor_user_id=client_a_id, detail="Cliente acepta oferta ganadora", created_at=request_created_at + timedelta(minutes=35))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="taller_descartado", actor_role=ROLE_CLIENTE, actor_user_id=client_a_id, detail="Oferta de taller sur rechazada", created_at=request_created_at + timedelta(minutes=35))

        conn.commit()


def seed_mecanicos_express(database_name: str, seed) -> None:
    with connect(database_name) as conn, conn.cursor() as cur:
        branch_ids = {branch.key: insert_branch(cur, branch) for branch in seed.branches}
        central_id = branch_ids["central"]

        superadmin_id = insert_tenant_user(
            cur,
            email="superadmin@mecanicosexpress.com",
            full_name="Superadmin Mecanicos Express",
            phone="70020021",
            password=seed.admin_password,
            role=ROLE_SUPERADMIN_TENANT,
            sucursal_id=None,
        )
        admin_id = insert_tenant_user(
            cur,
            email="admin.central@mecanicosexpress.com",
            full_name="Admin Sucursal Central",
            phone="70020022",
            password=seed.admin_password,
            role=ROLE_ADMIN_SUCURSAL,
            sucursal_id=central_id,
        )
        tenant_tech_id = insert_tenant_user(
            cur,
            email="tecnico.central@mecanicosexpress.com",
            full_name="Tecnico Central",
            phone="70020023",
            password=seed.admin_password,
            role=ROLE_TECNICO,
            sucursal_id=central_id,
        )

        client_id = insert_client(
            cur,
            identity_card="ME-CL-2001",
            full_name="Cliente Mecanicos Express",
            email="cliente@mecanicosexpress.com",
            phone="70020031",
            password=seed.client_password,
        )
        insert_vehicle(cur, client_id=client_id, brand="Nissan", model="Frontier", year=2022, plate="ME-2001", color="Gris", is_primary=True)

        workshop_id = insert_workshop(
            cur,
            workshop_name="Mecanicos Express Central",
            contact_name="Javier Roca",
            phone="70020041",
            email="taller.central@mecanicosexpress.com",
            zone="Centro",
            specialty="General",
            password=seed.workshop_password,
            sucursal_id=central_id,
            latitud=-17.7792,
            longitud=-63.1824,
        )
        technician_id = insert_technician(
            cur,
            workshop_id=workshop_id,
            usuario_tenant_id=tenant_tech_id,
            full_name="Tecnico Central",
            phone="70020051",
            email="tecnico.op.central@mecanicosexpress.com",
            specialty="General",
            status="ocupado",
            sucursal_id=central_id,
        )

        now = utc_now()
        active_emergency_id = insert_emergency(
            cur,
            local_id="ME-E-001",
            client_id=client_id,
            vehicle_name="Nissan Frontier",
            vehicle_plate="ME-2001",
            problem_type="Motor",
            price=160,
            emergency_status="auxilio_asignado",
            description="Camioneta detenida en avenida principal",
            latitud=-17.7785,
            longitud=-63.1821,
            address="Av. Alemana y 2do anillo",
            zone="Centro",
            workshop_id=workshop_id,
            workshop_name="Mecanicos Express Central",
            workshop_specialty="General",
            workshop_zone="Centro",
            distance_meters=600.0,
            sucursal_id=central_id,
            created_at=now - timedelta(hours=5),
            updated_at=now - timedelta(hours=4, minutes=30),
        )
        insert_status_history(cur, emergency_id=active_emergency_id, previous_status=None, new_status="pendiente", changed_by_role=ROLE_CLIENTE, changed_by_user_id=client_id, created_at=now - timedelta(hours=5), observation="Solicitud creada")
        insert_status_history(cur, emergency_id=active_emergency_id, previous_status="pendiente", new_status="activo", changed_by_role=ROLE_ADMIN_SUCURSAL, changed_by_user_id=admin_id, created_at=now - timedelta(hours=4, minutes=45), observation="Buscando taller")
        insert_status_history(cur, emergency_id=active_emergency_id, previous_status="activo", new_status="auxilio_asignado", changed_by_role=ROLE_ADMIN_SUCURSAL, changed_by_user_id=admin_id, created_at=now - timedelta(hours=4, minutes=30), observation="Taller asignado")
        insert_assignment(cur, emergency_id=active_emergency_id, workshop_id=workshop_id, technician_id=technician_id)
        insert_tracking(cur, emergency_id=active_emergency_id, technician_id=technician_id, latitude=-17.7781, longitude=-63.1818, source="technician_app", created_at=now - timedelta(hours=4, minutes=10))

        finished_emergency_id = insert_emergency(
            cur,
            local_id="ME-E-002",
            client_id=client_id,
            vehicle_name="Nissan Frontier",
            vehicle_plate="ME-2001",
            problem_type="Motor",
            price=200,
            emergency_status="servicio_finalizado",
            description="Servicio de arranque completado",
            latitud=-17.7801,
            longitud=-63.1831,
            address="Av. Irala",
            zone="Centro",
            workshop_id=workshop_id,
            workshop_name="Mecanicos Express Central",
            workshop_specialty="General",
            workshop_zone="Centro",
            distance_meters=850.0,
            sucursal_id=central_id,
            created_at=now - timedelta(days=1, hours=3),
            updated_at=now - timedelta(days=1, hours=2, minutes=5),
            hora_llegada=now - timedelta(days=1, hours=2, minutes=30),
        )
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status=None, new_status="pendiente", changed_by_role=ROLE_CLIENTE, changed_by_user_id=client_id, created_at=now - timedelta(days=1, hours=3), observation="Solicitud creada")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="pendiente", new_status="activo", changed_by_role=ROLE_ADMIN_SUCURSAL, changed_by_user_id=admin_id, created_at=now - timedelta(days=1, hours=2, minutes=55), observation="Buscando taller")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="activo", new_status="auxilio_asignado", changed_by_role=ROLE_ADMIN_SUCURSAL, changed_by_user_id=admin_id, created_at=now - timedelta(days=1, hours=2, minutes=45), observation="Taller asignado")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="auxilio_asignado", new_status="auxilio_en_camino", changed_by_role=ROLE_TECNICO, changed_by_user_id=tenant_tech_id, created_at=now - timedelta(days=1, hours=2, minutes=40), observation="En camino")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="auxilio_en_camino", new_status="tecnico_en_sitio", changed_by_role=ROLE_TECNICO, changed_by_user_id=tenant_tech_id, created_at=now - timedelta(days=1, hours=2, minutes=30), observation="Llegada")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="tecnico_en_sitio", new_status="servicio_en_proceso", changed_by_role=ROLE_TECNICO, changed_by_user_id=tenant_tech_id, created_at=now - timedelta(days=1, hours=2, minutes=25), observation="En atencion")
        insert_status_history(cur, emergency_id=finished_emergency_id, previous_status="servicio_en_proceso", new_status="servicio_finalizado", changed_by_role=ROLE_ADMIN_SUCURSAL, changed_by_user_id=admin_id, created_at=now - timedelta(days=1, hours=2, minutes=5), observation="Caso cerrado")
        insert_assignment(cur, emergency_id=finished_emergency_id, workshop_id=workshop_id, technician_id=technician_id)

        quotation_request_id = insert_quotation_request(
            cur,
            emergency_id=finished_emergency_id,
            client_id=client_id,
            status="seleccionado",
            requested_count=1,
            received_count=1,
            selected_offer_id=None,
            requested_at=now - timedelta(days=1, hours=2, minutes=50),
            expires_at=now + timedelta(days=2),
        )
        insert_quotation_workshop(cur, quotation_request_id=quotation_request_id, workshop_id=workshop_id, status="respondido", notified_at=now - timedelta(days=1, hours=2, minutes=45))
        offer_id = insert_quotation_offer(
            cur,
            quotation_request_id=quotation_request_id,
            workshop_id=workshop_id,
            price=Decimal("200.00"),
            service_description="Reparacion de motor en sitio",
            estimated_service_time="2 horas",
            estimated_arrival_time="15 min",
            warranty="15 dias",
            validity_days=2,
            observations="Oferta directa del taller central",
            status="aceptada",
            created_at=now - timedelta(days=1, hours=2, minutes=40),
        )
        cur.execute("UPDATE quotation_requests SET selected_offer_id = %s WHERE id = %s", (offer_id, quotation_request_id))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="solicitud_creada", actor_role="system", actor_user_id=client_id, detail="Solicitud creada", created_at=now - timedelta(days=1, hours=2, minutes=50))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="cotizacion_enviada", actor_role="workshop", actor_user_id=workshop_id, detail="Oferta enviada", created_at=now - timedelta(days=1, hours=2, minutes=40))
        insert_quotation_history(cur, quotation_request_id=quotation_request_id, event_type="cotizacion_aceptada", actor_role=ROLE_CLIENTE, actor_user_id=client_id, detail="Oferta aceptada", created_at=now - timedelta(days=1, hours=2, minutes=35))

        insert_notification(cur, user_id=client_id, title="Emergencia asignada", message="Tu solicitud ya tiene taller asignado.", is_read=False)
        insert_notification(cur, user_id=client_id, title="Cotizacion aceptada", message="La cotizacion del taller central fue aceptada.", is_read=True)

        conn.commit()


def apply_seed() -> None:
    tenants = master_tenant_map()
    missing = sorted(set(FINAL_TENANTS) - set(tenants))
    if missing:
        raise SystemExit(f"Missing tenant records in saas_master: {', '.join(missing)}")

    seed_auxilio_norte(str(tenants["auxilio_norte"]["database_name"]), FINAL_TENANTS["auxilio_norte"])
    seed_mecanicos_express(str(tenants["mecanicos_express"]["database_name"]), FINAL_TENANTS["mecanicos_express"])
    print("Seed SaaS final aplicado para auxilio_norte y mecanicos_express.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 14 final SaaS seed")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert the final seed. Without this flag the script only prints the plan.",
    )
    args = parser.parse_args()
    if not args.apply:
        preview()
        return
    apply_seed()


if __name__ == "__main__":
    main()
