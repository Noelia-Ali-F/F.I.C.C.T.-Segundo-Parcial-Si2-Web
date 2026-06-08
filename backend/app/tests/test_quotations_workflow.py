from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.saas_master import get_tenant_by_slug_any
from app.tenant_manager import get_tenant_engine


class QuotationsWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        cls.other_tenant = get_tenant_by_slug_any("mecanicos_express")
        if not cls.auxilio_tenant or not cls.other_tenant:
            raise RuntimeError("Tenants seed requeridos no encontrados")

        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.other_engine = get_tenant_engine(cls.other_tenant)

        cls.admin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "admin.norte@auxilionorte.com")
        cls.admin_sur = cls._tenant_user_by_email(cls.auxilio_engine, "admin.sur@auxilionorte.com")
        cls.client_a = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.a@auxilionorte.com")
        cls.client_b = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.b@auxilionorte.com")
        cls.workshop_norte = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_norte["sucursal_id"]))
        cls.workshop_sur = cls._workshop_by_sucursal(cls.auxilio_engine, int(cls.admin_sur["sucursal_id"]))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

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

    def login_headers(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def create_emergency(
        self,
        *,
        client: dict[str, object],
        workshop: dict[str, object],
        local_prefix: str,
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
                "vehicle_name": "Mazda 3",
                "vehicle_plate": f"QT{suffix[:6].upper()}",
                "problem_type": problem_type,
                "description": f"Quotation flow {suffix}",
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

    def request_quote(self, *, client: dict[str, object], emergency_id: int, max_workshops: int = 1) -> dict[str, object]:
        headers = self.login_headers(str(client["email"]), "ClienteAuxilio#2026")
        response = self.client.post(
            "/api/cotizaciones/solicitar",
            headers=headers,
            json={"emergency_id": emergency_id, "max_workshops": max_workshops, "expires_hours": 24},
        )
        self.assertIn(response.status_code, {200, 201}, response.text)
        return response.json()

    def create_offer(self, *, admin_email: str, workshop_id: int, quotation_id: int, price: float) -> dict[str, object]:
        headers = self.login_headers(admin_email, "AuxilioNorte#2026")
        response = self.client.post(
            f"/api/cotizaciones/{quotation_id}/propuestas",
            headers=headers,
            json={
                "workshop_id": workshop_id,
                "price": price,
                "service_description": f"Oferta {price}",
                "estimated_service_time": "2 horas",
                "validity_days": 3,
                "observations": "Incluye diagnóstico",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def fetch_notifications(self, engine, quotation_id: int) -> list[dict[str, object]]:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT event_type, recipient_user_id, recipient_role, entity_id
                    FROM system_notifications
                    WHERE entity_type = 'quotation_request'
                      AND entity_id = :quotation_id
                    ORDER BY id ASC
                    """
                ),
                {"quotation_id": quotation_id},
            ).mappings().all()
        return [dict(row) for row in rows]

    def fetch_request(self, quotation_id: int) -> dict[str, object]:
        with self.auxilio_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, emergency_id, client_id, status, selected_offer_id, received_offers_count
                    FROM quotation_requests
                    WHERE id = :quotation_id
                    LIMIT 1
                    """
                ),
                {"quotation_id": quotation_id},
            ).mappings().first()
        self.assertIsNotNone(row)
        return dict(row)

    def fetch_offer(self, offer_id: int) -> dict[str, object]:
        with self.auxilio_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, quotation_request_id, workshop_id, status, price
                    FROM quotation_offers
                    WHERE id = :offer_id
                    LIMIT 1
                    """
                ),
                {"offer_id": offer_id},
            ).mappings().first()
        self.assertIsNotNone(row)
        return dict(row)

    def test_client_can_request_quote_for_own_emergency(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-own")

        response = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)

        quotation = response["request"]
        self.assertEqual(quotation["emergency_id"], int(emergency["id"]))
        self.assertEqual(quotation["client_id"], int(self.client_a["id"]))
        self.assertEqual(quotation["status"], "abierto")

    def test_client_cannot_request_quote_for_other_client_emergency(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-other")
        headers = self.login_headers("cliente.b@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.post(
            "/api/cotizaciones/solicitar",
            headers=headers,
            json={"emergency_id": int(emergency["id"]), "max_workshops": 1, "expires_hours": 24},
        )

        self.assertEqual(response.status_code, 404, response.text)

    def test_admin_branch_lists_only_own_quote_requests(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-branch")
        created = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)
        quotation_id = created["request"]["id"]

        north_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        south_headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")

        north_response = self.client.get(f"/api/cotizaciones/taller/{self.workshop_norte['id']}", headers=north_headers)
        south_response = self.client.get(f"/api/cotizaciones/taller/{self.workshop_sur['id']}", headers=south_headers)

        self.assertEqual(north_response.status_code, 200, north_response.text)
        self.assertTrue(any(item["id"] == quotation_id for item in north_response.json()))
        self.assertEqual(south_response.status_code, 200, south_response.text)
        self.assertFalse(any(item["id"] == quotation_id for item in south_response.json()))

    def test_admin_branch_cannot_quote_other_branch_request(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-denied")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]
        headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")

        response = self.client.post(
            f"/api/cotizaciones/{quotation['id']}/propuestas",
            headers=headers,
            json={
                "workshop_id": self.workshop_sur["id"],
                "price": 500,
                "service_description": "Oferta sucursal Sur",
                "validity_days": 3,
            },
        )

        self.assertEqual(response.status_code, 403, response.text)

    def test_admin_branch_can_create_offer(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-offer")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]

        offer = self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=650,
        )

        persisted = self.fetch_offer(int(offer["id"]))
        self.assertEqual(persisted["status"], "enviada")
        request_row = self.fetch_request(int(quotation["id"]))
        self.assertEqual(request_row["status"], "con_propuestas")

    def test_client_owner_can_list_offers(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-list-owner")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]
        offer = self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=700,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.get(f"/api/cotizaciones/{quotation['id']}/propuestas", headers=headers)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any(item["id"] == offer["id"] for item in response.json()))

    def test_client_other_cannot_list_offers(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-list-other")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]
        self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=710,
        )
        headers = self.login_headers("cliente.b@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.get(f"/api/cotizaciones/{quotation['id']}/propuestas", headers=headers)

        self.assertEqual(response.status_code, 404, response.text)

    def test_client_owner_can_accept_offer_once(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-accept")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=2)["request"]
        north_offer = self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=800,
        )
        south_offer = self.create_offer(
            admin_email="admin.sur@auxilionorte.com",
            workshop_id=int(self.workshop_sur["id"]),
            quotation_id=int(quotation["id"]),
            price=780,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.post(
            f"/api/cotizaciones/{quotation['id']}/seleccionar-propuesta",
            headers=headers,
            json={"offer_id": north_offer["id"]},
        )

        self.assertEqual(response.status_code, 200, response.text)
        request_row = self.fetch_request(int(quotation["id"]))
        self.assertEqual(request_row["status"], "seleccionado")
        self.assertEqual(request_row["selected_offer_id"], int(north_offer["id"]))
        self.assertEqual(self.fetch_offer(int(north_offer["id"]))["status"], "aceptada")
        self.assertEqual(self.fetch_offer(int(south_offer["id"]))["status"], "rechazada")

    def test_client_cannot_accept_second_offer(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-second")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=2)["request"]
        north_offer = self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=900,
        )
        south_offer = self.create_offer(
            admin_email="admin.sur@auxilionorte.com",
            workshop_id=int(self.workshop_sur["id"]),
            quotation_id=int(quotation["id"]),
            price=880,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        first = self.client.post(
            f"/api/cotizaciones/{quotation['id']}/seleccionar-propuesta",
            headers=headers,
            json={"offer_id": north_offer["id"]},
        )
        second = self.client.post(
            f"/api/cotizaciones/{quotation['id']}/seleccionar-propuesta",
            headers=headers,
            json={"offer_id": south_offer["id"]},
        )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 409, second.text)

    def test_other_tenant_cannot_access_quote_request(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-tenant")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]
        headers = self.login_headers("superadmin@mecanicosexpress.com", "MecanicosExpress#2026")

        response = self.client.get(f"/api/cotizaciones/{quotation['id']}", headers=headers)

        self.assertEqual(response.status_code, 404, response.text)

    def test_quote_request_creates_notification(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-notif-request")

        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]

        notifications = self.fetch_notifications(self.auxilio_engine, int(quotation["id"]))
        self.assertTrue(any(item["event_type"] == "REQUEST_SENT_TO_WORKSHOPS" for item in notifications))

    def test_offer_creates_notification(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-notif-offer")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]

        self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=640,
        )

        notifications = self.fetch_notifications(self.auxilio_engine, int(quotation["id"]))
        self.assertTrue(any(item["event_type"] == "QUOTATION_RECEIVED" for item in notifications))

    def test_accept_offer_creates_notification(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-notif-accept")
        quotation = self.request_quote(client=self.client_a, emergency_id=int(emergency["id"]), max_workshops=1)["request"]
        offer = self.create_offer(
            admin_email="admin.norte@auxilionorte.com",
            workshop_id=int(self.workshop_norte["id"]),
            quotation_id=int(quotation["id"]),
            price=620,
        )
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.client.post(
            f"/api/cotizaciones/{quotation['id']}/seleccionar-propuesta",
            headers=headers,
            json={"offer_id": offer["id"]},
        )

        self.assertEqual(response.status_code, 200, response.text)
        notifications = self.fetch_notifications(self.auxilio_engine, int(quotation["id"]))
        self.assertTrue(any(item["event_type"] == "QUOTATION_ACCEPTED" for item in notifications))

    def test_quote_events_emit_realtime_if_mock_available(self) -> None:
        emergency = self.create_emergency(client=self.client_a, workshop=self.workshop_norte, local_prefix="quote-rt")
        client_headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        admin_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")

        with patch("app.routes.quotations._emit_quotation_realtime_events") as realtime_mock:
            request_response = self.client.post(
                "/api/cotizaciones/solicitar",
                headers=client_headers,
                json={"emergency_id": int(emergency["id"]), "max_workshops": 1, "expires_hours": 24},
            )
            self.assertEqual(request_response.status_code, 201, request_response.text)
            quotation_id = int(request_response.json()["request"]["id"])

            offer_response = self.client.post(
                f"/api/cotizaciones/{quotation_id}/propuestas",
                headers=admin_headers,
                json={
                    "workshop_id": int(self.workshop_norte["id"]),
                    "price": 605,
                    "service_description": "Oferta realtime",
                    "validity_days": 3,
                },
            )
            self.assertEqual(offer_response.status_code, 201, offer_response.text)
            offer_id = int(offer_response.json()["id"])

            accept_response = self.client.post(
                f"/api/cotizaciones/{quotation_id}/seleccionar-propuesta",
                headers=client_headers,
                json={"offer_id": offer_id},
            )
            self.assertEqual(accept_response.status_code, 200, accept_response.text)

        event_types = [call.args[0] for call in realtime_mock.call_args_list]
        self.assertIn("quotation_requested", event_types)
        self.assertIn("quotation_submitted", event_types)
        self.assertIn("quotation_accepted", event_types)


if __name__ == "__main__":
    unittest.main()
