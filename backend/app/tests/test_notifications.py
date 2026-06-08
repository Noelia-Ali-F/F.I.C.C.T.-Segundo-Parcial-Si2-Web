from __future__ import annotations

import uuid
import unittest
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.saas_master import get_master_engine, get_tenant_by_slug_any, register_device_fcm_token_global
from app.services.notification_service import NotificationRecipient, notify_emergency_event, notify_event
from app.tenant_context import clear_engine, set_context
from app.tenant_manager import get_tenant_engine


class NotificationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.auxilio_tenant = get_tenant_by_slug_any("auxilio_norte")
        cls.mecanicos_tenant = get_tenant_by_slug_any("mecanicos_express")
        if not cls.auxilio_tenant or not cls.mecanicos_tenant:
            raise RuntimeError("Tenants seed requeridos no encontrados")
        cls.auxilio_engine = get_tenant_engine(cls.auxilio_tenant)
        cls.mecanicos_engine = get_tenant_engine(cls.mecanicos_tenant)
        cls.master_engine = get_master_engine()

        cls.superadmin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "superadmin@auxilionorte.com")
        cls.admin_norte = cls._tenant_user_by_email(cls.auxilio_engine, "admin.norte@auxilionorte.com")
        cls.admin_sur = cls._tenant_user_by_email(cls.auxilio_engine, "admin.sur@auxilionorte.com")
        cls.tecnico_norte = cls._tenant_user_by_email(cls.auxilio_engine, "tecnico.norte@auxilionorte.com")
        cls.client_a = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.a@auxilionorte.com")
        cls.client_b = cls._tenant_client_by_email(cls.auxilio_engine, "cliente.b@auxilionorte.com")

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
                    SELECT id, email, role, status
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

    @contextmanager
    def tenant_scope(self, tenant: dict[str, object]) -> Iterator[None]:
        engine = get_tenant_engine(tenant)
        set_context(engine, tenant)
        try:
            yield
        finally:
            clear_engine()

    @contextmanager
    def inactive_tokens_for_users(self, tenant_slug: str, user_ids: list[int]) -> Iterator[None]:
        with self.master_engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, is_active
                    FROM device_fcm_tokens
                    WHERE tenant_slug = :tenant_slug
                      AND user_id = ANY(:user_ids)
                    """
                ),
                {"tenant_slug": tenant_slug, "user_ids": user_ids},
            ).mappings().all()
            row_ids = [int(row["id"]) for row in rows]
            if row_ids:
                conn.execute(
                    text("UPDATE device_fcm_tokens SET is_active = FALSE, updated_at = NOW() WHERE id = ANY(:row_ids)"),
                    {"row_ids": row_ids},
                )
        try:
            yield
        finally:
            if not rows:
                return
            with self.master_engine.begin() as conn:
                for row in rows:
                    conn.execute(
                        text(
                            """
                            UPDATE device_fcm_tokens
                            SET is_active = :is_active,
                                updated_at = NOW()
                            WHERE id = :id
                            """
                        ),
                        {"id": int(row["id"]), "is_active": bool(row["is_active"])},
                    )

    def login_headers(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def register_active_token(
        self,
        *,
        tenant_id: int,
        tenant_slug: str,
        user_id: int,
        role: str,
        sucursal_id: int | None,
    ) -> dict[str, object]:
        return register_device_fcm_token_global(
            {
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "user_id": user_id,
                "role": role,
                "sucursal_id": sucursal_id,
                "fcm_token": f"test-token-{uuid.uuid4()}",
                "platform": "android",
                "is_active": True,
            }
        )

    def create_emergency(self, *, suffix: str, problem_type: str = "Batería") -> dict[str, object]:
        headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        response = self.client.post(
            "/api/emergencias",
            headers=headers,
            data={
                "local_id": f"notif-test-{suffix}",
                "client_id": str(self.client_a["id"]),
                "vehicle_name": "Toyota Corolla",
                "vehicle_plate": f"NT{suffix[:6].upper()}",
                "problem_type": problem_type,
                "description": f"Prueba automatizada {suffix}",
                "latitude": "-17.7641",
                "longitude": "-63.1729",
                "address": "4to anillo y San Martin",
                "zone": "Norte",
                "nearest_workshop_id": "1",
                "nearest_workshop_name": "Auxilio Norte Taller Norte",
                "nearest_workshop_specialty": problem_type,
                "nearest_workshop_zone": "Norte",
                "nearest_workshop_distance_meters": "800",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def fetch_notifications_by_entity(
        self,
        tenant_engine,
        *,
        entity_type: str,
        entity_id: int,
    ) -> list[dict[str, object]]:
        with tenant_engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT *
                    FROM system_notifications
                    WHERE entity_type = :entity_type
                      AND entity_id = :entity_id
                    ORDER BY id ASC
                    """
                ),
                {"entity_type": entity_type, "entity_id": entity_id},
            ).mappings().all()
        return [dict(row) for row in rows]

    def fetch_notification_by_id(self, tenant_engine, notification_id: int) -> dict[str, object]:
        with tenant_engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM system_notifications WHERE id = :notification_id"),
                {"notification_id": notification_id},
            ).mappings().first()
        self.assertIsNotNone(row)
        return dict(row)

    def find_notification(
        self,
        rows: list[dict[str, object]],
        *,
        recipient_user_id: int,
        recipient_role: str,
    ) -> dict[str, object]:
        for row in rows:
            if int(row["recipient_user_id"]) == recipient_user_id and str(row["recipient_role"]) == recipient_role:
                return row
        self.fail(f"No se encontró notificación para user_id={recipient_user_id} role={recipient_role}")

    def create_manual_notification(
        self,
        *,
        recipient: NotificationRecipient,
        event_type: str,
        entity_type: str,
        entity_id: int,
        sucursal_id: int | None,
        title: str = "Notificación de prueba",
        body: str = "Detalle de prueba",
    ) -> list[dict[str, object]]:
        with self.tenant_scope(self.auxilio_tenant), patch(
            "app.services.notification_service.list_active_device_fcm_tokens",
            return_value=[],
        ):
            return notify_event(
                event_type=event_type,
                event_source="tests",
                entity_type=entity_type,
                entity_id=entity_id,
                recipients=[recipient],
                data={"status": "test", "status_label": "test"},
                sucursal_id=sucursal_id,
                title=title,
                body=body,
                event_version="tests",
            )

    def test_a1_emergency_registered_targets_only_matching_sucursales(self) -> None:
        entity_id = 915000 + uuid.uuid4().int % 10000
        report = {
            "id": entity_id,
            "client_id": int(self.client_a["id"]),
            "sucursal_id": None,
            "nearest_workshop_id": 1,
            "nearest_workshop_name": "Auxilio Norte Taller Norte",
            "problem_type": "Batería",
            "description": "Filtrado por sucursales compatibles",
            "assigned_technician_id": None,
            "assigned_technician_name": None,
            "emergency_status": "pendiente",
        }
        with self.tenant_scope(self.auxilio_tenant), patch(
            "app.services.notification_service.list_active_device_fcm_tokens",
            return_value=[],
        ):
            notify_emergency_event(
                "EMERGENCY_REGISTERED",
                report,
                extra_data={"matching_sucursal_ids": [int(self.admin_norte["sucursal_id"])]},
                event_version="routing-scope",
            )
        rows = self.fetch_notifications_by_entity(
            self.auxilio_engine,
            entity_type="emergency",
            entity_id=entity_id,
        )
        self.find_notification(
            rows,
            recipient_user_id=int(self.superadmin_norte["id"]),
            recipient_role=str(self.superadmin_norte["role"]),
        )
        self.find_notification(
            rows,
            recipient_user_id=int(self.admin_norte["id"]),
            recipient_role=str(self.admin_norte["role"]),
        )
        self.assertFalse(
            any(
                int(row["recipient_user_id"]) == int(self.admin_sur["id"])
                and str(row["recipient_role"]) == str(self.admin_sur["role"])
                for row in rows
            )
        )

    def test_a_emergency_registered_creates_notifications_without_token_as_skipped(self) -> None:
        affected_users = [
            int(self.superadmin_norte["id"]),
            int(self.admin_norte["id"]),
            int(self.tecnico_norte["id"]),
            int(self.client_a["id"]),
        ]
        with self.inactive_tokens_for_users("auxilio_norte", affected_users):
            created = self.create_emergency(suffix=uuid.uuid4().hex[:8], problem_type="Batería")
        rows = self.fetch_notifications_by_entity(
            self.auxilio_engine,
            entity_type="emergency",
            entity_id=int(created["id"]),
        )
        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["event_type"], "EMERGENCY_REGISTERED")
            self.assertEqual(row["delivery_status"], "skipped")
            self.assertEqual(row["error_code"], "NO_ACTIVE_TOKEN")

    def test_b_emergency_registered_with_active_token_sets_sent(self) -> None:
        self.register_active_token(
            tenant_id=int(self.auxilio_tenant["id"]),
            tenant_slug=str(self.auxilio_tenant["slug"]),
            user_id=int(self.superadmin_norte["id"]),
            role=str(self.superadmin_norte["role"]),
            sucursal_id=None,
        )
        with patch("app.services.notification_service.firebase_push_is_ready", return_value=(True, None)), patch(
            "app.services.notification_service.send_push_to_device_token",
            return_value=("mock-message-id", {"status": "ok"}),
        ):
            created = self.create_emergency(suffix=uuid.uuid4().hex[:8], problem_type="Motor")
        rows = self.fetch_notifications_by_entity(
            self.auxilio_engine,
            entity_type="emergency",
            entity_id=int(created["id"]),
        )
        sent_row = self.find_notification(
            rows,
            recipient_user_id=int(self.superadmin_norte["id"]),
            recipient_role=str(self.superadmin_norte["role"]),
        )
        self.assertEqual(sent_row["delivery_status"], "sent")
        self.assertEqual(sent_row["fcm_message_id"], "mock-message-id")
        self.assertIsNotNone(sent_row["sent_at"])

    def test_c_fcm_failure_sets_failed(self) -> None:
        self.register_active_token(
            tenant_id=int(self.auxilio_tenant["id"]),
            tenant_slug=str(self.auxilio_tenant["slug"]),
            user_id=int(self.superadmin_norte["id"]),
            role=str(self.superadmin_norte["role"]),
            sucursal_id=None,
        )
        with patch("app.services.notification_service.firebase_push_is_ready", return_value=(True, None)), patch(
            "app.services.notification_service.send_push_to_device_token",
            side_effect=RuntimeError("mock fcm failure"),
        ):
            created = self.create_emergency(suffix=uuid.uuid4().hex[:8], problem_type="Otro")
        rows = self.fetch_notifications_by_entity(
            self.auxilio_engine,
            entity_type="emergency",
            entity_id=int(created["id"]),
        )
        failed_row = self.find_notification(
            rows,
            recipient_user_id=int(self.superadmin_norte["id"]),
            recipient_role=str(self.superadmin_norte["role"]),
        )
        self.assertEqual(failed_row["delivery_status"], "failed")
        self.assertEqual(failed_row["error_code"], "RuntimeError")
        self.assertIn("mock fcm failure", str(failed_row["error_message"]))

    def test_d_notification_idempotency_prevents_duplicates(self) -> None:
        entity_id = 910000 + uuid.uuid4().int % 10000
        report = {
            "id": entity_id,
            "client_id": int(self.client_a["id"]),
            "sucursal_id": 1,
            "nearest_workshop_id": 1,
            "nearest_workshop_name": "Auxilio Norte Taller Norte",
            "problem_type": "Motor",
            "description": "Idempotencia notificaciones",
            "assigned_technician_id": None,
            "assigned_technician_name": None,
            "emergency_status": "pendiente",
        }
        with self.tenant_scope(self.auxilio_tenant), patch(
            "app.services.notification_service.list_active_device_fcm_tokens",
            return_value=[],
        ):
            notify_emergency_event("EMERGENCY_REGISTERED", report, event_version="same-version")
            notify_emergency_event("EMERGENCY_REGISTERED", report, event_version="same-version")
        rows = self.fetch_notifications_by_entity(
            self.auxilio_engine,
            entity_type="emergency",
            entity_id=entity_id,
        )
        idempotency_keys = {str(row["idempotency_key"]) for row in rows}
        self.assertEqual(len(rows), len(idempotency_keys))

    def test_e_scope_admin_sucursal(self) -> None:
        entity_id = 920000 + uuid.uuid4().int % 10000
        self.create_manual_notification(
            recipient=NotificationRecipient(
                user_id=int(self.admin_norte["id"]),
                role=str(self.admin_norte["role"]),
                sucursal_id=int(self.admin_norte["sucursal_id"]),
                email=str(self.admin_norte["email"]),
            ),
            event_type="EMERGENCY_STATUS_CHANGED",
            entity_type="scope_admin",
            entity_id=entity_id,
            sucursal_id=1,
        )
        north_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        south_headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")
        north_response = self.client.get(
            "/api/notificaciones",
            headers=north_headers,
            params={"entity_type": "scope_admin", "entity_id": entity_id},
        )
        south_response = self.client.get(
            "/api/notificaciones",
            headers=south_headers,
            params={"entity_type": "scope_admin", "entity_id": entity_id},
        )
        self.assertEqual(north_response.status_code, 200, north_response.text)
        self.assertEqual(north_response.json()["total"], 1)
        self.assertEqual(south_response.status_code, 200, south_response.text)
        self.assertEqual(south_response.json()["total"], 0)

    def test_f_scope_cliente(self) -> None:
        entity_id = 930000 + uuid.uuid4().int % 10000
        created_rows = self.create_manual_notification(
            recipient=NotificationRecipient(
                user_id=int(self.client_a["id"]),
                role="CLIENTE",
                email=str(self.client_a["email"]),
            ),
            event_type="QUOTATION_RECEIVED",
            entity_type="scope_client",
            entity_id=entity_id,
            sucursal_id=None,
        )
        notification_id = int(created_rows[0]["id"])
        client_a_headers = self.login_headers("cliente.a@auxilionorte.com", "ClienteAuxilio#2026")
        client_b_headers = self.login_headers("cliente.b@auxilionorte.com", "ClienteAuxilio#2026")
        own_response = self.client.get(f"/api/notificaciones/{notification_id}", headers=client_a_headers)
        foreign_response = self.client.get(f"/api/notificaciones/{notification_id}", headers=client_b_headers)
        self.assertEqual(own_response.status_code, 200, own_response.text)
        self.assertEqual(foreign_response.status_code, 404, foreign_response.text)

    def test_g_scope_tenant(self) -> None:
        entity_id = 940000 + uuid.uuid4().int % 10000
        self.create_manual_notification(
            recipient=NotificationRecipient(
                user_id=int(self.superadmin_norte["id"]),
                role=str(self.superadmin_norte["role"]),
                email=str(self.superadmin_norte["email"]),
            ),
            event_type="EMERGENCY_STATUS_CHANGED",
            entity_type="scope_tenant",
            entity_id=entity_id,
            sucursal_id=1,
        )
        tenant_a_headers = self.login_headers("superadmin@auxilionorte.com", "AuxilioNorte#2026")
        tenant_b_headers = self.login_headers("superadmin@mecanicosexpress.com", "MecanicosExpress#2026")
        tenant_a_response = self.client.get(
            "/api/notificaciones",
            headers=tenant_a_headers,
            params={"entity_type": "scope_tenant", "entity_id": entity_id},
        )
        tenant_b_response = self.client.get(
            "/api/notificaciones",
            headers=tenant_b_headers,
            params={"entity_type": "scope_tenant", "entity_id": entity_id},
        )
        self.assertEqual(tenant_a_response.status_code, 200, tenant_a_response.text)
        self.assertEqual(tenant_a_response.json()["total"], 1)
        self.assertEqual(tenant_b_response.status_code, 200, tenant_b_response.text)
        self.assertEqual(tenant_b_response.json()["total"], 0)

    def test_h_mark_as_read(self) -> None:
        entity_id = 950000 + uuid.uuid4().int % 10000
        created_rows = self.create_manual_notification(
            recipient=NotificationRecipient(
                user_id=int(self.admin_norte["id"]),
                role=str(self.admin_norte["role"]),
                sucursal_id=int(self.admin_norte["sucursal_id"]),
                email=str(self.admin_norte["email"]),
            ),
            event_type="EMERGENCY_STATUS_CHANGED",
            entity_type="mark_read",
            entity_id=entity_id,
            sucursal_id=1,
        )
        notification_id = int(created_rows[0]["id"])
        headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        response = self.client.patch(f"/api/notificaciones/{notification_id}/read", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["read_status"], "read")
        self.assertIsNotNone(payload["read_at"])

    def test_i_retry_failed_notification(self) -> None:
        self.register_active_token(
            tenant_id=int(self.auxilio_tenant["id"]),
            tenant_slug=str(self.auxilio_tenant["slug"]),
            user_id=int(self.admin_norte["id"]),
            role=str(self.admin_norte["role"]),
            sucursal_id=int(self.admin_norte["sucursal_id"]),
        )
        entity_id = 960000 + uuid.uuid4().int % 10000
        with self.tenant_scope(self.auxilio_tenant), patch(
            "app.services.notification_service.firebase_push_is_ready",
            return_value=(True, None),
        ), patch(
            "app.services.notification_service.send_push_to_device_token",
            side_effect=RuntimeError("initial send failure"),
        ):
            rows = notify_event(
                event_type="EMERGENCY_STATUS_CHANGED",
                event_source="tests",
                entity_type="retry_case",
                entity_id=entity_id,
                recipients=[
                    NotificationRecipient(
                        user_id=int(self.admin_norte["id"]),
                        role=str(self.admin_norte["role"]),
                        sucursal_id=int(self.admin_norte["sucursal_id"]),
                        email=str(self.admin_norte["email"]),
                    )
                ],
                data={"status": "failed", "status_label": "failed"},
                sucursal_id=1,
                title="Retry test",
                body="Retry test body",
                event_version="failed-once",
            )
        notification_id = int(rows[0]["id"])
        failed_row = self.fetch_notification_by_id(self.auxilio_engine, notification_id)
        self.assertEqual(failed_row["delivery_status"], "failed")

        admin_sur_headers = self.login_headers("admin.sur@auxilionorte.com", "AuxilioNorte#2026")
        forbidden_response = self.client.post(f"/api/notificaciones/{notification_id}/reenviar", headers=admin_sur_headers)
        self.assertEqual(forbidden_response.status_code, 404, forbidden_response.text)

        admin_norte_headers = self.login_headers("admin.norte@auxilionorte.com", "AuxilioNorte#2026")
        with patch("app.services.notification_service.firebase_push_is_ready", return_value=(True, None)), patch(
            "app.services.notification_service.send_push_to_device_token",
            return_value=("retry-message-id", {"status": "ok"}),
        ):
            retry_response = self.client.post(
                f"/api/notificaciones/{notification_id}/reenviar",
                headers=admin_norte_headers,
            )
        self.assertEqual(retry_response.status_code, 200, retry_response.text)
        payload = retry_response.json()
        self.assertEqual(payload["delivery_status"], "retried")
        self.assertEqual(payload["retry_count"], 1)
        self.assertEqual(payload["fcm_message_id"], "retry-message-id")


if __name__ == "__main__":
    unittest.main()
