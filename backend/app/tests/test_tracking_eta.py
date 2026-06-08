from __future__ import annotations

import unittest
import uuid
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.routes.emergencies import _build_emergency_realtime_events
from app.saas_master import get_tenant_by_slug_any
from app.tenant_context import clear_engine, set_context
from app.tenant_manager import get_tenant_engine


class TrackingEtaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        cls.other_tenant = get_tenant_by_slug_any("mecanicos_express")
        if not cls.auxilio_tenant or not cls.other_tenant:
            raise RuntimeError("Tenants seed requeridos no encontrados")

        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.admin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "admin.norte@auxilionorte.com")
        cls.admin_sur = cls._tenant_user_by_email(cls.auxilio_engine, "admin.sur@auxilionorte.com")
        cls.client_a = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.a@auxilionorte.com")
        cls.client_b = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.b@auxilionorte.com")
        cls.technician_norte = cls._technician_user_by_email(cls.auxilio_engine, "tecnico.norte@auxilionorte.com")
        cls.other_technician = cls._find_other_technician(
            cls.auxilio_engine,
            excluded_technician_id=int(cls.technician_norte["technician_id"]),
        )
        cls.workshop_norte = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_norte["sucursal_id"]))
        cls.workshop_sur = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_sur["sucursal_id"]))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def setUp(self) -> None:
        with self.auxilio_engine.begin() as conn:
            conn.execute(text("UPDATE technicians SET status = 'disponible', updated_at = NOW()"))

    @staticmethod
    def _tenant_user_by_email(engine, email: str) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, email, role, sucursal_id
                    FROM usuarios_tenant
                    WHERE email = :email
                    LIMIT 1
                    """
                ),
                {"email": email},
            ).mappings().first()
        if not row:
            raise RuntimeError(f"Usuario tenant no encontrado: {email}")
        return dict(row)

    @staticmethod
    def _tenant_client_by_email(engine, email: str) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, email, role
                    FROM clients
                    WHERE email = :email
                    LIMIT 1
                    """
                ),
                {"email": email},
            ).mappings().first()
        if not row:
            raise RuntimeError(f"Cliente tenant no encontrado: {email}")
        return dict(row)

    @staticmethod
    def _technician_user_by_email(engine, email: str) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT u.id AS user_id,
                           u.email,
                           u.sucursal_id,
                           t.id AS technician_id,
                           t.workshop_id
                    FROM usuarios_tenant u
                    JOIN technicians t
                      ON t.usuario_tenant_id = u.id
                    WHERE u.email = :email
                    LIMIT 1
                    """
                ),
                {"email": email},
            ).mappings().first()
        if not row:
            raise RuntimeError(f"Técnico no encontrado: {email}")
        return dict(row)

    @staticmethod
    def _find_other_technician(engine, *, excluded_technician_id: int) -> dict[str, object] | None:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT u.id AS user_id,
                           u.email,
                           u.sucursal_id,
                           t.id AS technician_id,
                           t.workshop_id
                    FROM usuarios_tenant u
                    JOIN technicians t
                      ON t.usuario_tenant_id = u.id
                    WHERE u.role = 'TECNICO'
                      AND t.id <> :technician_id
                    ORDER BY t.id ASC
                    LIMIT 1
                    """
                ),
                {"technician_id": excluded_technician_id},
            ).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _workshop_by_sucursal(engine, sucursal_id: int) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, workshop_name, specialty, zone, sucursal_id, latitude, longitude
                    FROM workshop_registrations
                    WHERE sucursal_id = :sucursal_id
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ),
                {"sucursal_id": sucursal_id},
            ).mappings().first()
        if not row:
            raise RuntimeError(f"Taller no encontrado para sucursal {sucursal_id}")
        return dict(row)

    @contextmanager
    def tenant_scope(self, tenant: dict[str, object]) -> Iterator[None]:
        engine = get_tenant_engine(tenant)
        set_context(engine, tenant)
        try:
            yield
        finally:
            clear_engine()

    def login_headers(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def create_emergency(self, *, client: dict[str, object], workshop: dict[str, object], local_prefix: str) -> dict[str, object]:
        headers = self.login_headers(str(client["email"]), "ClienteAuxilio#2026")
        suffix = uuid.uuid4().hex[:8]
        response = self.client.post(
            "/api/emergencias",
            headers=headers,
            data={
                "local_id": f"{local_prefix}-{suffix}",
                "client_id": str(client["id"]),
                "vehicle_name": "Nissan Versa",
                "vehicle_plate": f"TR{suffix[:6].upper()}",
                "problem_type": "Batería",
                "description": f"Tracking test {suffix}",
                "latitude": "-17.7641",
                "longitude": "-63.1729",
                "address": "4to anillo y San Martin",
                "zone": str(workshop["zone"] or "Norte"),
                "nearest_workshop_id": str(workshop["id"]),
                "nearest_workshop_name": str(workshop["workshop_name"]),
                "nearest_workshop_specialty": str(workshop["specialty"] or "Batería"),
                "nearest_workshop_zone": str(workshop["zone"] or "Norte"),
                "nearest_workshop_distance_meters": "800",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def accept_and_assign(self, emergency_id: int) -> None:
        admin_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        accept_response = self.client.put(
            f"/api/emergencias/{emergency_id}/status",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"emergency_status": "activo"},
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.text)
        assign_response = self.client.put(
            f"/api/emergencias/{emergency_id}/technician-assignment",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"technician_id": self.technician_norte["technician_id"]},
        )
        self.assertEqual(assign_response.status_code, 200, assign_response.text)

    def fetch_latest_tracking_row(self, emergency_id: int) -> dict[str, object] | None:
        with self.auxilio_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                    FROM emergency_tracking_points
                    WHERE emergency_id = :emergency_id
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().first()
        return dict(row) if row else None

    def fetch_report(self, emergency_id: int) -> dict[str, object]:
        with self.auxilio_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                    FROM emergency_reports
                    WHERE id = :emergency_id
                    LIMIT 1
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().first()
        self.assertIsNotNone(row)
        return dict(row)

    def test_assigned_technician_can_post_tracking(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-ok")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("tecnico.norte@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.post(
            f"/api/emergencias/{emergency['id']}/tracking/location",
            headers=headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={
                "latitude": -17.765,
                "longitude": -63.171,
                "source": "gps",
                "heading": 120,
                "speed": 11.5,
                "accuracy": 6.2,
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        tracking_row = self.fetch_latest_tracking_row(int(emergency["id"]))
        self.assertIsNotNone(tracking_row)
        self.assertEqual(int(tracking_row["technician_id"]), int(self.technician_norte["technician_id"]))
        self.assertEqual(str(tracking_row["source"]), "gps")
        if tracking_row.get("heading") is not None:
            self.assertAlmostEqual(float(tracking_row["heading"]), 120.0)

    def test_unassigned_technician_cannot_post_tracking(self) -> None:
        if self.other_technician is None:
            self.skipTest("No hay otro técnico seed para validar acceso denegado")

        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-denied")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers(str(self.other_technician["email"]), "AuxilioNorte#2026")

        before_row = self.fetch_latest_tracking_row(int(emergency["id"]))
        response = self.client.post(
            f"/api/emergencias/{emergency['id']}/tracking/location",
            headers=headers,
            params={"workshop_id": self.other_technician["workshop_id"]},
            json={"latitude": -17.76, "longitude": -63.17, "source": "gps"},
        )

        self.assertIn(response.status_code, {403, 404, 409}, response.text)
        after_row = self.fetch_latest_tracking_row(int(emergency["id"]))
        self.assertEqual(before_row, after_row)

    def test_client_owner_can_get_tracking(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-owner")
        self.accept_and_assign(int(emergency["id"]))
        technician_headers = self.login_headers("tecnico.norte@auxilionorte.com", "AuxilioNorte#2026")
        self.client.post(
            f"/api/emergencias/{emergency['id']}/tracking/location",
            headers=technician_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"latitude": -17.765, "longitude": -63.171, "source": "gps"},
        )

        client_headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        response = self.client.get(f"/api/emergencias/{emergency['id']}/tracking", headers=client_headers)

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["tenant_slug"], "auxilio_norte")
        self.assertEqual(body["sucursal_id"], self.workshop_norte["sucursal_id"])
        self.assertEqual(body["technician"]["source"], "gps")

    def test_client_other_cannot_get_tracking(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-other-client")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("cliente.b@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.get(f"/api/emergencias/{emergency['id']}/tracking", headers=headers)
        self.assertEqual(response.status_code, 404, response.text)

    def test_admin_branch_can_get_tracking_own_branch(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-admin-branch")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.get(
            f"/api/emergencias/{emergency['id']}/tracking",
            headers=headers,
            params={"workshop_id": self.workshop_norte["id"]},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_admin_branch_cannot_get_tracking_other_branch(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-admin-other-branch")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.get(
            f"/api/emergencias/{emergency['id']}/tracking",
            headers=headers,
            params={"workshop_id": self.workshop_sur["id"]},
        )
        self.assertIn(response.status_code, {403, 404}, response.text)

    def test_other_tenant_cannot_get_tracking(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-other-tenant")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("superadmin@mecanicosexpress.com", "MecanicosExpress#2026")

        response = self.client.get(f"/api/emergencias/{emergency['id']}/tracking", headers=headers)
        self.assertEqual(response.status_code, 404, response.text)

    def test_tracking_location_emits_realtime_event(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-realtime")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("tecnico.norte@auxilionorte.com", "AuxilioNorte#2026")

        with patch("app.routes.emergencies._emit_emergency_realtime_events") as emit_mock:
            response = self.client.post(
                f"/api/emergencias/{emergency['id']}/tracking/location",
                headers=headers,
                params={"workshop_id": self.workshop_norte["id"]},
                json={"latitude": -17.765, "longitude": -63.171, "source": "gps"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        emit_mock.assert_called_once()
        self.assertEqual(emit_mock.call_args.args[0], "tracking_location_updated")

    def test_tracking_payload_contains_tenant_and_sucursal(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-payload")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("tecnico.norte@auxilionorte.com", "AuxilioNorte#2026")
        response = self.client.post(
            f"/api/emergencias/{emergency['id']}/tracking/location",
            headers=headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"latitude": -17.765, "longitude": -63.171, "source": "gps"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        report = self.fetch_report(int(emergency["id"]))
        with self.tenant_scope(self.auxilio_tenant):
            events = _build_emergency_realtime_events(
                "tracking_location_updated",
                report,
                include_technician=False,
                payload={
                    "technician_id": self.technician_norte["technician_id"],
                    "tracking_latitude": -17.765,
                    "tracking_longitude": -63.171,
                    "tracking_source": "gps",
                },
            )

        self.assertTrue(events)
        event_payload = events[0].payload
        self.assertEqual(event_payload["tenant_slug"], "auxilio_norte")
        self.assertEqual(event_payload["sucursal_id"], self.workshop_norte["sucursal_id"])

    def test_nearest_workshop_distance_is_saved_or_exposed(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="trk-distance")
        self.accept_and_assign(int(emergency["id"]))
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.get(f"/api/emergencias/{emergency['id']}/tracking", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertIsNotNone(emergency["nearest_workshop_distance_meters"])
        self.assertEqual(body["nearest_workshop_id"], self.workshop_norte["id"])
        self.assertIsNotNone(body["nearest_workshop_distance_meters"])
        self.assertGreater(body["route"]["distance_meters"], 0)
        self.assertTrue(body["route"]["distance_text"])
        self.assertTrue(body["route"]["duration_text"])


if __name__ == "__main__":
    unittest.main()
