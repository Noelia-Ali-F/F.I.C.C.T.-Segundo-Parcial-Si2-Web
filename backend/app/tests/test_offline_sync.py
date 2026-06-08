from __future__ import annotations

import io
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.saas_master import get_tenant_by_slug_any
from app.tenant_manager import get_tenant_engine


class OfflineSyncIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        cls.other_tenant = get_tenant_by_slug_any("mecanicos_express")
        if not cls.auxilio_tenant or not cls.other_tenant:
            raise RuntimeError("Tenants seed requeridos no encontrados")

        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.other_engine = get_tenant_engine(cls.other_tenant)

        cls.client_a = cls._client_by_email(cls.auxilio_engine, "cliente.a@auxilionorte.com")
        cls.client_b = cls._client_by_email(cls.auxilio_engine, "cliente.b@auxilionorte.com")
        cls.admin_other_tenant = cls._tenant_user_by_email(cls.other_engine, "superadmin@mecanicosexpress.com")
        cls.other_tenant_client = cls._first_client(cls.other_engine)
        cls.workshop_norte = cls._workshop_by_sucursal_name(cls.auxilio_engine, "Norte")
        cls.other_tenant_workshop = cls._first_workshop(cls.other_engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    @staticmethod
    def _client_by_email(engine, email: str) -> dict[str, object]:
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
            raise RuntimeError(f"Cliente no encontrado: {email}")
        return dict(row)

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
    def _first_client(engine) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, email, role
                    FROM clients
                    ORDER BY id ASC
                    LIMIT 1
                    """
                )
            ).mappings().first()
        if not row:
            raise RuntimeError("No se encontró cliente en tenant alterno")
        return dict(row)

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
    def _first_workshop(engine) -> dict[str, object]:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, workshop_name, specialty, zone, sucursal_id
                    FROM workshop_registrations
                    ORDER BY id ASC
                    LIMIT 1
                    """
                )
            ).mappings().first()
        if not row:
            raise RuntimeError("No se encontró taller en tenant alterno")
        return dict(row)

    def login_headers(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def emergency_payload(
        self,
        *,
        local_id: str,
        client_id: int | None,
        workshop: dict[str, object],
    ) -> dict[str, str]:
        payload = {
            "local_id": local_id,
            "vehicle_name": "Suzuki Swift",
            "vehicle_plate": f"OF{uuid.uuid4().hex[:6].upper()}",
            "problem_type": "Batería",
            "description": f"Offline sync test {local_id}",
            "latitude": "-17.7641",
            "longitude": "-63.1729",
            "address": "4to anillo y San Martin",
            "zone": str(workshop.get("zone") or "Norte"),
            "nearest_workshop_id": str(workshop["id"]),
            "nearest_workshop_name": str(workshop.get("workshop_name") or ""),
            "nearest_workshop_specialty": str(workshop.get("specialty") or "Batería"),
            "nearest_workshop_zone": str(workshop.get("zone") or "Norte"),
            "nearest_workshop_distance_meters": "750",
        }
        if client_id is not None:
            payload["client_id"] = str(client_id)
        return payload

    def post_emergency(
        self,
        *,
        headers: dict[str, str] | None,
        data: dict[str, str],
        files: list[tuple[str, tuple[str, io.BytesIO, str]]] | None = None,
    ):
        with (
            patch("app.routes.emergencies.transcribe_emergency_audio", return_value=(None, None, None)),
            patch("app.routes.emergencies.classify_emergency_photos", return_value=(None, None, None)),
            patch("app.routes.emergencies.notify_emergency_event"),
            patch("app.routes.emergencies._emit_emergency_realtime_events"),
        ):
            return self.client.post(
                "/api/emergencias",
                headers=headers or {},
                data=data,
                files=files,
            )

    def post_emergency_with_mocks(
        self,
        *,
        headers: dict[str, str] | None,
        data: dict[str, str],
    ):
        with (
            patch("app.routes.emergencies.transcribe_emergency_audio", return_value=(None, None, None)),
            patch("app.routes.emergencies.classify_emergency_photos", return_value=(None, None, None)),
            patch("app.routes.emergencies.notify_emergency_event") as notify_mock,
            patch("app.routes.emergencies._emit_emergency_realtime_events") as realtime_mock,
        ):
            response = self.client.post(
                "/api/emergencias",
                headers=headers or {},
                data=data,
            )
        return response, notify_mock, realtime_mock

    def fetch_report_by_local_id(self, engine, local_id: str) -> dict[str, object] | None:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, local_id, client_id, nearest_workshop_id, nearest_workshop_name,
                           nearest_workshop_specialty, nearest_workshop_zone, photo_paths, audio_path
                    FROM emergency_reports
                    WHERE local_id = :local_id
                    LIMIT 1
                    """
                ),
                {"local_id": local_id},
            ).mappings().first()
        return dict(row) if row else None

    def count_reports_by_local_id(self, engine, local_id: str) -> int:
        with engine.connect() as conn:
            return int(
                conn.execute(
                    text("SELECT COUNT(*) FROM emergency_reports WHERE local_id = :local_id"),
                    {"local_id": local_id},
                ).scalar_one()
            )

    def fetch_history(self, engine, emergency_id: int) -> list[dict[str, object]]:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT previous_status, new_status, changed_by_role, changed_by_user_id
                    FROM emergency_status_history
                    WHERE emergency_id = :emergency_id
                    ORDER BY id ASC
                    """
                ),
                {"emergency_id": emergency_id},
            ).mappings().all()
        return [dict(row) for row in rows]

    def count_history_rows(self, engine, emergency_id: int) -> int:
        with engine.connect() as conn:
            return int(
                conn.execute(
                    text("SELECT COUNT(*) FROM emergency_status_history WHERE emergency_id = :emergency_id"),
                    {"emergency_id": emergency_id},
                ).scalar_one()
            )

    def test_offline_create_emergency_with_local_id(self) -> None:
        local_id = f"offline-create-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.post_emergency(
            headers=headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["local_id"], local_id)
        self.assertEqual(body["client_id"], int(self.client_a["id"]))
        persisted = self.fetch_report_by_local_id(self.auxilio_engine, local_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(int(persisted["nearest_workshop_id"]), int(self.workshop_norte["id"]))

    def test_duplicate_local_id_returns_existing_record_or_conflict(self) -> None:
        local_id = f"offline-dup-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        payload = self.emergency_payload(
            local_id=local_id,
            client_id=int(self.client_a["id"]),
            workshop=self.workshop_norte,
        )

        first = self.post_emergency(headers=headers, data=payload)
        second = self.post_emergency(headers=headers, data=payload)

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(self.count_history_rows(self.auxilio_engine, int(first.json()["id"])), 1)
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 1)

    def test_same_local_id_other_tenant_creates_new_record(self) -> None:
        local_id = f"offline-cross-tenant-{uuid.uuid4().hex[:10]}"
        client_headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        other_tenant_headers = self.login_headers("superadmin@mecanicosexpress.com", "MecanicosExpress#2026")

        north_response = self.post_emergency(
            headers=client_headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )
        other_response = self.post_emergency(
            headers=other_tenant_headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.other_tenant_client["id"]),
                workshop=self.other_tenant_workshop,
            ),
        )

        self.assertEqual(north_response.status_code, 201, north_response.text)
        self.assertEqual(other_response.status_code, 201, other_response.text)
        self.assertNotEqual(north_response.json()["id"], other_response.json()["id"])
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 1)
        self.assertEqual(self.count_reports_by_local_id(self.other_engine, local_id), 1)

    def test_client_cannot_create_for_other_client_id(self) -> None:
        local_id = f"offline-client-mismatch-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.post_emergency(
            headers=headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_b["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"], "CLIENT_ID_AJENO_NO_PERMITIDO")
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 0)

    def test_same_local_id_other_client_same_tenant_returns_conflict(self) -> None:
        local_id = f"offline-collision-{uuid.uuid4().hex[:10]}"
        headers_a = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        headers_b = self.login_headers("cliente.b@auxilionorte.com", "ClienteAuxilio#2026")

        created = self.post_emergency(
            headers=headers_a,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )
        collided = self.post_emergency(
            headers=headers_b,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_b["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(collided.status_code, 409, collided.text)
        self.assertEqual(
            collided.json(),
            {
                "error_code": "LOCAL_ID_YA_EXISTE_PARA_OTRO_CLIENTE",
                "message": "El local_id ya fue sincronizado por otro cliente del mismo tenant",
                "local_id": local_id,
                "duplicated": False,
                "emergency_id": created.json()["id"],
            },
        )
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 1)

    def test_sync_creation_writes_initial_history(self) -> None:
        local_id = f"offline-history-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.post_emergency(
            headers=headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        history = self.fetch_history(self.auxilio_engine, int(response.json()["id"]))
        self.assertTrue(history)
        self.assertEqual(history[0]["new_status"], "solicitud_recibida")
        self.assertEqual(history[0]["changed_by_role"], "client")
        self.assertEqual(history[0]["changed_by_user_id"], int(self.client_a["id"]))

    def test_sync_creation_notifies_once_and_duplicate_does_not_repeat_side_effects(self) -> None:
        local_id = f"offline-hooks-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        payload = self.emergency_payload(
            local_id=local_id,
            client_id=int(self.client_a["id"]),
            workshop=self.workshop_norte,
        )

        created, notify_created, realtime_created = self.post_emergency_with_mocks(headers=headers, data=payload)
        duplicate, notify_duplicate, realtime_duplicate = self.post_emergency_with_mocks(headers=headers, data=payload)

        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(duplicate.status_code, 200, duplicate.text)
        notify_created.assert_called_once()
        realtime_created.assert_called_once()
        notify_duplicate.assert_not_called()
        realtime_duplicate.assert_not_called()

    def test_sync_creation_persists_media_when_present(self) -> None:
        local_id = f"offline-media-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        files = [
            ("photos", ("evidence.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakepng"), "image/png")),
            ("audio", ("note.webm", io.BytesIO(b"fake-webm-audio"), "audio/webm")),
        ]

        response = self.post_emergency(
            headers=headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
            files=files,
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(len(body["photo_paths"]), 1)
        self.assertIsNotNone(body["audio_path"])
        persisted = self.fetch_report_by_local_id(self.auxilio_engine, local_id)
        self.assertIsNotNone(persisted)
        self.assertIn("emergencias/photos/", str(persisted["photo_paths"]))
        self.assertIn("emergencias/audio/", str(persisted["audio_path"]))

    def test_sync_creation_without_media_still_works(self) -> None:
        local_id = f"offline-no-media-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")

        response = self.post_emergency(
            headers=headers,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["photo_paths"], [])
        self.assertIsNone(body["audio_path"])

    def test_invalid_workshop_id_returns_controlled_error(self) -> None:
        local_id = f"offline-bad-workshop-{uuid.uuid4().hex[:10]}"
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        payload = self.emergency_payload(
            local_id=local_id,
            client_id=int(self.client_a["id"]),
            workshop=self.workshop_norte,
        )
        payload["nearest_workshop_id"] = "99999999"

        response = self.post_emergency(headers=headers, data=payload)

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            response.json(),
            {
                "error_code": "WORKSHOP_NO_ENCONTRADO_EN_TENANT",
                "message": "El taller indicado no existe dentro del tenant activo",
            },
        )
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 0)

    def test_create_requires_jwt(self) -> None:
        local_id = f"offline-no-jwt-{uuid.uuid4().hex[:10]}"

        response = self.post_emergency(
            headers=None,
            data=self.emergency_payload(
                local_id=local_id,
                client_id=int(self.client_a["id"]),
                workshop=self.workshop_norte,
            ),
        )

        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self.count_reports_by_local_id(self.auxilio_engine, local_id), 0)


if __name__ == "__main__":
    unittest.main()
