from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.saas_master import get_tenant_by_slug_any
from app.tenant_manager import get_tenant_engine


class EmergencyWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        cls.mecanicos_tenant = get_tenant_by_slug_any("mecanicos_express")
        if not cls.auxilio_tenant or not cls.mecanicos_tenant:
            raise RuntimeError("Tenants seed requeridos no encontrados")

        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.mecanicos_engine = get_tenant_engine(cls.mecanicos_tenant)

        cls.superadmin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "superadmin@auxilionorte.com")
        cls.admin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "admin.norte@auxilionorte.com")
        cls.admin_sur = cls._tenant_user_by_email(cls.auxilio_engine, "admin.sur@auxilionorte.com")
        cls.client_a = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.a@auxilionorte.com")
        cls.client_b = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.b@auxilionorte.com")

        cls.workshop_norte = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_norte["sucursal_id"]))
        cls.workshop_sur = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_sur["sucursal_id"]))

        cls.technician_norte = cls._technician_user_by_email(cls.auxilio_engine, "tecnico.norte@auxilionorte.com")
        cls.other_technician = cls._find_other_technician(
            cls.auxilio_engine,
            excluded_technician_id=int(cls.technician_norte["technician_id"]),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def setUp(self) -> None:
        self._reset_technician_statuses()

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
    def _workshop_by_sucursal(engine, sucursal_id: int) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, workshop_name, specialty, zone, sucursal_id
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

    def _reset_technician_statuses(self) -> None:
        with self.auxilio_engine.begin() as conn:
            conn.execute(text("UPDATE technicians SET status = 'disponible', updated_at = NOW()"))

    def _ensure_workshop_specialty(self, workshop_id: int, specialty: str) -> None:
        with self.auxilio_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO workshop_specialties (workshop_id, specialty)
                    VALUES (:workshop_id, CAST(:specialty AS VARCHAR(120)))
                    ON CONFLICT (workshop_id, specialty) DO NOTHING
                    """
                ),
                {"workshop_id": workshop_id, "specialty": specialty},
            )

    def _set_workshop_location(self, workshop_id: int, latitude: float, longitude: float) -> None:
        with self.auxilio_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE workshop_registrations
                    SET latitude = :latitude,
                        longitude = :longitude
                    WHERE id = :workshop_id
                    """
                ),
                {"workshop_id": workshop_id, "latitude": latitude, "longitude": longitude},
            )

    def _remove_workshop_specialty(self, workshop_id: int, specialty: str) -> None:
        with self.auxilio_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM workshop_specialties
                    WHERE workshop_id = :workshop_id
                      AND specialty = CAST(:specialty AS VARCHAR(120))
                    """
                ),
                {"workshop_id": workshop_id, "specialty": specialty},
            )

    def login_headers(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def create_emergency(
        self,
        *,
        local_prefix: str,
        client: dict[str, object],
        workshop: dict[str, object],
        problem_type: str = "Batería",
    ) -> dict[str, object]:
        headers = self.login_headers(str(client["email"]), "ClienteAuxilio#2026")
        suffix = uuid.uuid4().hex[:8]
        response = self.client.post(
            "/api/emergencias",
            headers=headers,
            data={
                "local_id": f"{local_prefix}-{suffix}",
                "client_id": str(client["id"]),
                "vehicle_name": "Toyota Corolla",
                "vehicle_plate": f"QA{suffix[:6].upper()}",
                "problem_type": problem_type,
                "description": f"Emergencia automatizada {suffix}",
                "latitude": "-17.7641",
                "longitude": "-63.1729",
                "address": "4to anillo y San Martin",
                "zone": str(workshop["zone"] or "Norte"),
                "nearest_workshop_id": str(workshop["id"]),
                "nearest_workshop_name": str(workshop["workshop_name"]),
                "nearest_workshop_specialty": str(workshop["specialty"] or problem_type),
                "nearest_workshop_zone": str(workshop["zone"] or "Norte"),
                "nearest_workshop_distance_meters": "800",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def fetch_emergency_history(self, emergency_id: int) -> list[dict[str, object]]:
        with self.auxilio_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT previous_status, new_status, observation
                    FROM emergency_status_history
                    WHERE emergency_id = :emergency_id
                    ORDER BY id ASC
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().all()
        return [dict(row) for row in rows]

    def fetch_emergency_notifications(self, emergency_id: int) -> list[dict[str, object]]:
        with self.auxilio_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT event_type, recipient_user_id, recipient_role
                    FROM system_notifications
                    WHERE entity_type = 'emergency'
                      AND entity_id = :emergency_id
                    ORDER BY id ASC
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().all()
        return [dict(row) for row in rows]

    def fetch_emergency_row(self, emergency_id: int) -> dict[str, object]:
        with self.auxilio_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT emergency_status, hora_llegada, sucursal_id
                    FROM emergency_reports
                    WHERE id = :emergency_id
                    LIMIT 1
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().first()
        self.assertIsNotNone(row)
        return dict(row)

    def test_admin_sucursal_accepts_own_emergency(self) -> None:
        emergency = self.create_emergency(
            local_prefix="accept-own",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"emergency_status": "activo"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["emergency_status"], "activo")
        history = self.fetch_emergency_history(int(emergency["id"]))
        self.assertTrue(any(item["new_status"] == "activo" for item in history))

    def test_emergency_remains_visible_to_other_candidate_but_cannot_be_accepted_after_winner(self) -> None:
        self._ensure_workshop_specialty(int(self.workshop_norte["id"]), "Batería")
        self._ensure_workshop_specialty(int(self.workshop_sur["id"]), "Batería")
        self._set_workshop_location(int(self.workshop_norte["id"]), -17.7641, -63.1729)
        self._set_workshop_location(int(self.workshop_sur["id"]), -17.8100, -63.2100)

        emergency = self.create_emergency(
            local_prefix="branch-broadcast",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        norte_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        sur_headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")

        listed_before = self.client.get("/api/emergencias", headers=sur_headers)
        self.assertEqual(listed_before.status_code, 200, listed_before.text)
        before_row = next((item for item in listed_before.json() if int(item["id"]) == int(emergency["id"])), None)
        self.assertIsNotNone(before_row)
        self.assertTrue(before_row["can_accept"])

        accept_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=norte_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"emergency_status": "activo"},
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.text)

        listed_after = self.client.get("/api/emergencias", headers=sur_headers)
        self.assertEqual(listed_after.status_code, 200, listed_after.text)
        after_row = next((item for item in listed_after.json() if int(item["id"]) == int(emergency["id"])), None)
        self.assertIsNotNone(after_row)
        self.assertEqual(after_row["workshop_candidate_status"], "ACEPTADA_POR_OTRA_SUCURSAL")
        self.assertEqual(after_row["workshop_candidate_message"], "Esta solicitud ya fue aceptada por otra sucursal")
        self.assertFalse(after_row["can_accept"])

        blocked_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=sur_headers,
            params={"workshop_id": self.workshop_sur["id"]},
            json={"emergency_status": "activo"},
        )
        self.assertEqual(blocked_response.status_code, 409, blocked_response.text)
        self.assertEqual(blocked_response.json()["detail"], "Esta solicitud ya fue aceptada por otra sucursal")

    def test_admin_sucursal_cannot_accept_other_branch(self) -> None:
        problem_type = "Sistema eléctrico"
        self._ensure_workshop_specialty(int(self.workshop_norte["id"]), problem_type)
        self._remove_workshop_specialty(int(self.workshop_sur["id"]), problem_type)
        emergency = self.create_emergency(
            local_prefix="accept-other-branch",
            client=self.client_a,
            workshop=self.workshop_norte,
            problem_type=problem_type,
        )
        headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=headers,
            params={"workshop_id": self.workshop_sur["id"]},
            json={"emergency_status": "activo"},
        )

        self.assertIn(response.status_code, {403, 404}, response.text)

    def test_client_cannot_accept_request(self) -> None:
        emergency = self.create_emergency(
            local_prefix="client-cannot-accept",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=headers,
            json={"emergency_status": "activo"},
        )

        self.assertEqual(response.status_code, 403, response.text)

    def test_technician_assigned_can_mark_arrived(self) -> None:
        emergency = self.create_emergency(
            local_prefix="technician-arrived",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        admin_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        accept_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"emergency_status": "activo"},
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.text)

        assign_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/technician-assignment",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"technician_id": self.technician_norte["technician_id"]},
        )
        self.assertEqual(assign_response.status_code, 200, assign_response.text)

        tech_headers = self.login_headers("tecnico.norte@auxilionorte.com", "AuxilioNorte#2026")
        arrived_response = self.client.patch(
            f"/api/emergencias/{emergency['id']}/estado",
            headers=tech_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={
                "estado": "tecnico_llego",
                "observacion": "Llegada registrada por test",
                "latitud_llegada": -17.7642,
                "longitud_llegada": -63.1730,
            },
        )

        self.assertEqual(arrived_response.status_code, 200, arrived_response.text)
        self.assertEqual(arrived_response.json()["current_status"], "tecnico_en_sitio")
        history = self.fetch_emergency_history(int(emergency["id"]))
        self.assertTrue(any(item["new_status"] == "tecnico_en_sitio" for item in history))
        report_row = self.fetch_emergency_row(int(emergency["id"]))
        self.assertEqual(report_row["emergency_status"], "tecnico_en_sitio")
        self.assertIsNotNone(report_row["hora_llegada"])

    def test_technician_not_assigned_cannot_mark_arrived(self) -> None:
        if self.other_technician is None:
            self.skipTest("No hay otro técnico seed para validar acceso denegado")

        emergency = self.create_emergency(
            local_prefix="other-technician-cannot-arrive",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        admin_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        accept_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/status",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"emergency_status": "activo"},
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.text)

        assign_response = self.client.put(
            f"/api/emergencias/{emergency['id']}/technician-assignment",
            headers=admin_headers,
            params={"workshop_id": self.workshop_norte["id"]},
            json={"technician_id": self.technician_norte["technician_id"]},
        )
        self.assertEqual(assign_response.status_code, 200, assign_response.text)

        other_headers = self.login_headers(str(self.other_technician["email"]), "AuxilioNorte#2026")
        arrived_response = self.client.patch(
            f"/api/emergencias/{emergency['id']}/estado",
            headers=other_headers,
            params={"workshop_id": self.other_technician["workshop_id"]},
            json={"estado": "tecnico_llego", "observacion": "Intento no autorizado"},
        )

        self.assertIn(arrived_response.status_code, {403, 404}, arrived_response.text)

    def test_status_change_creates_notification_and_emits_realtime(self) -> None:
        emergency = self.create_emergency(
            local_prefix="accept-notify",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        with patch("app.routes.emergencies._emit_emergency_status_realtime_events") as emit_mock:
            response = self.client.put(
                f"/api/emergencias/{emergency['id']}/status",
                headers=headers,
                params={"workshop_id": self.workshop_norte["id"]},
                json={"emergency_status": "activo"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        emit_mock.assert_called_once()
        notifications = self.fetch_emergency_notifications(int(emergency["id"]))
        self.assertTrue(any(item["event_type"] == "REQUEST_ACCEPTED" for item in notifications))

    def test_other_tenant_cannot_access_emergency(self) -> None:
        emergency = self.create_emergency(
            local_prefix="other-tenant-access",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        headers = self.login_headers("superadmin@mecanicosexpress.com", "MecanicosExpress#2026")

        response = self.client.get(
            f"/api/emergencias/{emergency['id']}",
            headers=headers,
        )

        self.assertEqual(response.status_code, 404, response.text)

    def test_client_only_sees_own_emergencies(self) -> None:
        emergency_a = self.create_emergency(
            local_prefix="client-a-own",
            client=self.client_a,
            workshop=self.workshop_norte,
        )
        emergency_b = self.create_emergency(
            local_prefix="client-b-own",
            client=self.client_b,
            workshop=self.workshop_norte,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        list_response = self.client.get("/api/emergencias", headers=headers)
        self.assertEqual(list_response.status_code, 200, list_response.text)
        visible_ids = {int(item["id"]) for item in list_response.json()}
        self.assertIn(int(emergency_a["id"]), visible_ids)
        self.assertNotIn(int(emergency_b["id"]), visible_ids)

        detail_response = self.client.get(
            f"/api/emergencias/{emergency_b['id']}",
            headers=headers,
        )
        self.assertEqual(detail_response.status_code, 404, detail_response.text)


if __name__ == "__main__":
    unittest.main()
