from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.saas_master import get_tenant_by_slug_any
from app.tenant_manager import get_tenant_engine
from app.utils import ROLE_CLIENTE, decode_access_token


class MobileClientFlowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        if not cls.auxilio_tenant:
            raise RuntimeError("Tenant auxilio_norte no encontrado")
        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.workshop_norte = cls._workshop_by_sucursal_name(cls.auxilio_engine, "Norte")
        cls.workshop_sur = cls._workshop_by_sucursal_name(cls.auxilio_engine, "Sur")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    @staticmethod
    def _workshop_by_sucursal_name(engine, sucursal_name: str) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT wr.id, wr.workshop_name, wr.specialty, wr.zone, wr.sucursal_id
                    FROM workshop_registrations wr
                    JOIN sucursales s
                      ON s.id = wr.sucursal_id
                    WHERE LOWER(s.nombre) LIKE LOWER(:sucursal_name)
                    ORDER BY wr.id ASC
                    LIMIT 1
                    """
                ),
                {"sucursal_name": f"%{sucursal_name}%"},
            ).mappings().first()
        if not row:
            raise RuntimeError(f"Taller no encontrado para sucursal {sucursal_name}")
        return dict(row)

    @staticmethod
    def _client_by_email(engine, email: str) -> dict[str, object] | None:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, email, role, status
                    FROM clients
                    WHERE email = :email
                    LIMIT 1
                    """
                ),
                {"email": email},
            ).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _emergency_by_local_id(engine, local_id: str) -> dict[str, object] | None:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, local_id, client_id, emergency_status
                    FROM emergency_reports
                    WHERE local_id = :local_id
                    LIMIT 1
                    """
                ),
                {"local_id": local_id},
            ).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _history_count_for_emergency(engine, emergency_id: int) -> int:
        with engine.connect() as conn:
            return int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM emergency_status_history
                        WHERE emergency_id = :emergency_id
                        """
                    ),
                    {"emergency_id": emergency_id},
                ).scalar_one()
            )

    @staticmethod
    def _ensure_workshop_specialty(engine, workshop_id: int, specialty: str) -> None:
        with engine.begin() as conn:
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

    @staticmethod
    def _set_workshop_location(engine, workshop_id: int, latitude: float, longitude: float) -> None:
        with engine.begin() as conn:
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

    def _register_mobile_client(self, *, role: str = "client") -> dict[str, str]:
        suffix = uuid.uuid4().hex[:8]
        email = f"movil.{suffix}@auxilionorte.com"
        payload = {
            "identity_card": f"CI{uuid.uuid4().hex[:10].upper()}",
            "full_name": f"Cliente Movil {suffix}",
            "email": email,
            "phone": f"700{suffix[:5]}",
            "password": "ClienteMovil#2026",
            "confirm_password": "ClienteMovil#2026",
            "role": role,
            "accepted_terms": True,
        }
        response = self.client.post(
            "/api/clientes",
            headers={"X-Tenant-Slug": "auxilio_norte"},
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return {"email": email, "password": payload["password"]}

    def _login(self, *, email: str, password: str):
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password, "account_type": "CLIENTE"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def _create_emergency(
        self,
        *,
        token: str,
        client_id: int | None,
        local_id: str,
        nearest_workshop_id: int | None = None,
        nearest_workshop_name: str | None = None,
        nearest_workshop_specialty: str | None = None,
        nearest_workshop_zone: str | None = None,
        nearest_workshop_distance_meters: float | None = None,
    ):
        data = {
            "local_id": local_id,
            "vehicle_name": "Toyota Yaris",
            "vehicle_plate": f"MC{uuid.uuid4().hex[:6].upper()}",
            "problem_type": "Batería",
            "description": f"Mobile flow test {local_id}",
            "latitude": "-17.7641",
            "longitude": "-63.1729",
            "address": "4to anillo y San Martin",
            "zone": str(self.workshop_norte.get("zone") or "Norte"),
        }
        if nearest_workshop_id is not None:
            data["nearest_workshop_id"] = str(nearest_workshop_id)
        if nearest_workshop_name is not None:
            data["nearest_workshop_name"] = nearest_workshop_name
        if nearest_workshop_specialty is not None:
            data["nearest_workshop_specialty"] = nearest_workshop_specialty
        if nearest_workshop_zone is not None:
            data["nearest_workshop_zone"] = nearest_workshop_zone
        if nearest_workshop_distance_meters is not None:
            data["nearest_workshop_distance_meters"] = str(nearest_workshop_distance_meters)
        if client_id is not None:
            data["client_id"] = str(client_id)
        with (
            patch("app.routes.emergencies.transcribe_emergency_audio", return_value=(None, None, None)),
            patch("app.routes.emergencies.classify_emergency_photos", return_value=(None, None, None)),
            patch("app.routes.emergencies.notify_emergency_event"),
            patch("app.routes.emergencies._emit_emergency_realtime_events"),
        ):
            return self.client.post(
                "/api/emergencias",
                headers={"Authorization": f"Bearer {token}"},
                data=data,
            )

    def test_mobile_client_registration_creates_cliente_role(self) -> None:
        credentials = self._register_mobile_client()
        row = self._client_by_email(self.auxilio_engine, credentials["email"])
        self.assertIsNotNone(row)
        self.assertEqual(row["role"], ROLE_CLIENTE)
        self.assertEqual(row["status"], "active")

    def test_mobile_can_preview_matching_sucursales_and_nearest_workshop(self) -> None:
        self._ensure_workshop_specialty(self.auxilio_engine, int(self.workshop_norte["id"]), "Batería")
        self._ensure_workshop_specialty(self.auxilio_engine, int(self.workshop_sur["id"]), "Batería")
        self._set_workshop_location(self.auxilio_engine, int(self.workshop_norte["id"]), -17.7641, -63.1729)
        self._set_workshop_location(self.auxilio_engine, int(self.workshop_sur["id"]), -17.8100, -63.2100)

        credentials = self._register_mobile_client()
        login = self._login(**credentials).json()
        response = self.client.get(
            "/api/emergencias/routing-preview",
            headers={"Authorization": f"Bearer {login['access_token']}"},
            params={
                "problem_type": "Batería",
                "latitude": -17.7641,
                "longitude": -63.1729,
                "description": "La batería se descargó por completo",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertGreaterEqual(body["total_matching_sucursales"], 2)
        self.assertEqual(body["nearest_workshop_id"], int(self.workshop_norte["id"]))
        self.assertGreaterEqual(len(body["candidates"]), 2)
        self.assertEqual(body["candidates"][0]["workshop_id"], int(self.workshop_norte["id"]))
        self.assertLessEqual(
            float(body["candidates"][0]["distance_meters"]),
            float(body["candidates"][1]["distance_meters"]),
        )

    def test_mobile_client_login_returns_cliente_jwt(self) -> None:
        credentials = self._register_mobile_client()
        response = self._login(**credentials)
        body = response.json()
        claims = decode_access_token(body["access_token"])

        self.assertEqual(body["role"], ROLE_CLIENTE)
        self.assertEqual(body["tenant_slug"], "auxilio_norte")
        self.assertEqual(body["tenant_id"], int(self.auxilio_tenant["id"]))
        self.assertEqual(claims["role"], ROLE_CLIENTE)
        self.assertEqual(claims["rol"], ROLE_CLIENTE)
        self.assertEqual(claims["tenant_slug"], "auxilio_norte")
        self.assertEqual(claims["tenant_id"], int(self.auxilio_tenant["id"]))

    def test_cliente_can_create_emergency(self) -> None:
        self._ensure_workshop_specialty(self.auxilio_engine, int(self.workshop_norte["id"]), "Batería")
        credentials = self._register_mobile_client()
        login = self._login(**credentials).json()
        local_id = f"mobile-{uuid.uuid4().hex[:10]}"
        response = self._create_emergency(
            token=login["access_token"],
            client_id=login["id"],
            local_id=local_id,
            nearest_workshop_id=int(self.workshop_norte["id"]),
            nearest_workshop_name=str(self.workshop_norte.get("workshop_name") or ""),
            nearest_workshop_specialty="Batería",
            nearest_workshop_zone=str(self.workshop_norte.get("zone") or "Norte"),
            nearest_workshop_distance_meters=700,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["client_id"], login["id"])

        row = self._emergency_by_local_id(self.auxilio_engine, local_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["client_id"], login["id"])
        self.assertIn(row["emergency_status"], {"pendiente", "solicitud_recibida"})
        self.assertGreaterEqual(self._history_count_for_emergency(self.auxilio_engine, int(row["id"])), 1)

    def test_cliente_can_create_emergency_without_nearest_workshop_and_backend_resolves_it(self) -> None:
        self._ensure_workshop_specialty(self.auxilio_engine, int(self.workshop_norte["id"]), "Batería")
        self._ensure_workshop_specialty(self.auxilio_engine, int(self.workshop_sur["id"]), "Batería")
        self._set_workshop_location(self.auxilio_engine, int(self.workshop_norte["id"]), -17.7641, -63.1729)
        self._set_workshop_location(self.auxilio_engine, int(self.workshop_sur["id"]), -17.8100, -63.2100)

        credentials = self._register_mobile_client()
        login = self._login(**credentials).json()
        local_id = f"mobile-auto-{uuid.uuid4().hex[:10]}"
        response = self._create_emergency(
            token=login["access_token"],
            client_id=login["id"],
            local_id=local_id,
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["nearest_workshop_id"], int(self.workshop_norte["id"]))
        self.assertEqual(body["nearest_workshop_specialty"], "Batería")
        self.assertIsNone(body["sucursal_id"])

    def test_cliente_cannot_create_for_other_client_id(self) -> None:
        credentials = self._register_mobile_client()
        login = self._login(**credentials).json()
        response = self._create_emergency(
            token=login["access_token"],
            client_id=int(login["id"]) + 99999,
            local_id=f"mobile-forbidden-{uuid.uuid4().hex[:8]}",
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"], "CLIENT_ID_AJENO_NO_PERMITIDO")

    def test_tecnico_cannot_create_emergency(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "tecnico.norte@auxilionorte.com", "password": "AuxilioNorte#2026"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        create_response = self._create_emergency(
            token=response.json()["access_token"],
            client_id=None,
            local_id=f"mobile-tech-{uuid.uuid4().hex[:8]}",
        )
        self.assertEqual(create_response.status_code, 403, create_response.text)
        self.assertEqual(create_response.json()["detail"], "ROL_NO_AUTORIZADO_PARA_CREAR_EMERGENCIA")

    def test_admin_sucursal_cannot_create_emergency_without_client_id(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "admin.norte@auxilionorte.com", "password": "AuxilioNorte#2026"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        create_response = self._create_emergency(
            token=response.json()["access_token"],
            client_id=None,
            local_id=f"mobile-admin-{uuid.uuid4().hex[:8]}",
        )
        self.assertEqual(create_response.status_code, 422, create_response.text)
        self.assertEqual(create_response.json()["detail"], "client_id es requerido")

    def test_superadmin_tenant_cannot_create_emergency_as_client(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "superadmin@auxilionorte.com", "password": "AuxilioNorte#2026"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        create_response = self._create_emergency(
            token=response.json()["access_token"],
            client_id=None,
            local_id=f"mobile-superadmin-{uuid.uuid4().hex[:8]}",
        )
        self.assertEqual(create_response.status_code, 422, create_response.text)
        self.assertEqual(create_response.json()["detail"], "client_id es requerido")

    def test_role_client_legacy_normalizes_to_cliente_if_supported(self) -> None:
        credentials = self._register_mobile_client(role="client")
        row = self._client_by_email(self.auxilio_engine, credentials["email"])
        self.assertIsNotNone(row)

        with self.auxilio_engine.begin() as conn:
            conn.execute(
                text("UPDATE clients SET role = 'client' WHERE id = :id"),
                {"id": int(row["id"])},
            )

        login = self._login(**credentials).json()
        claims = decode_access_token(login["access_token"])
        self.assertEqual(login["role"], ROLE_CLIENTE)
        self.assertEqual(claims["role"], ROLE_CLIENTE)
        self.assertEqual(claims["rol"], ROLE_CLIENTE)
