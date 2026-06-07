from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import logging
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
from threading import Lock
import unicodedata
from urllib.parse import urlparse
from uuid import uuid4

import jwt as pyjwt
from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.db import create_notification, get_client_by_id, list_active_device_fcm_tokens, list_active_device_fcm_tokens_default

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None

logger = logging.getLogger(__name__)

PROTECTED_ADMIN_EMAIL = settings.protected_admin_email.lower().strip()
PROTECTED_ADMIN_ROLE = "admin"
PROTECTED_ADMIN_ID = 0
WORKSHOP_ROLE = "workshop"
LOGIN_MAX_ATTEMPTS = 3
LOGIN_LOCKOUT_MINUTES = 10

# Nuevos roles para la arquitectura Database-Per-Tenant
ROLE_SUPERADMIN_GLOBAL = "SUPERADMIN_GLOBAL"    # = admin global del sistema
ROLE_SUPERADMIN_TENANT = "SUPERADMIN_TENANT"    # dueño de una empresa/tenant
ROLE_ADMIN_SUCURSAL = "ADMIN_SUCURSAL"          # administra una sucursal
ROLE_TECNICO = "TECNICO"                        # técnico asignado a una sucursal
ROLE_CLIENTE = "CLIENTE"                        # cliente móvil de un tenant

# Conjunto de roles que pertenecen a un tenant específico
TENANT_ROLES = {ROLE_SUPERADMIN_TENANT, ROLE_ADMIN_SUCURSAL, ROLE_TECNICO, ROLE_CLIENTE}

UPLOADS_ROOT = Path(settings.uploads_dir)
VEHICLE_UPLOADS_DIR = UPLOADS_ROOT / "vehicles"
EMERGENCY_UPLOADS_DIR = UPLOADS_ROOT / "emergencias"
EMERGENCY_PHOTOS_DIR = EMERGENCY_UPLOADS_DIR / "photos"
EMERGENCY_AUDIO_DIR = EMERGENCY_UPLOADS_DIR / "audio"

MAX_EMERGENCY_PHOTOS = 6
MAX_EMERGENCY_PHOTO_BYTES = 20 * 1024 * 1024
MAX_EMERGENCY_AUDIO_BYTES = 40 * 1024 * 1024
ALLOWED_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_SUFFIXES = {".aac", ".m4a", ".mp3", ".wav", ".ogg", ".webm"}
ALLOWED_EMERGENCY_PROBLEM_TYPES = {
    "Batería",
    "Neumático",
    "Combustible",
    "Motor",
    "Sistema eléctrico",
    "Accidente",
    "Cerrajería / llaves",
    "Otro",
}
STANDARDIZED_EMERGENCY_PROBLEM_TYPES = ALLOWED_EMERGENCY_PROBLEM_TYPES - {"Otro"}
EMERGENCY_BASE_PRICES = {
    "Batería": 50,
    "Neumático": 50,
    "Combustible": 60,
    "Motor": 100,
    "Sistema eléctrico": 90,
    "Accidente": 150,
    "Cerrajería / llaves": 80,
}
EMERGENCY_STATUS_NOTIFICATION_LABELS = {
    "en_revision": "En revisión",
    "auxilio_asignado": "Auxilio asignado",
    "auxilio_en_camino": "Auxilio en camino",
    "tecnico_en_sitio": "Técnico en sitio",
    "servicio_en_proceso": "Servicio en proceso",
    "servicio_finalizado": "Servicio finalizado",
    "solicitud_cancelada": "Solicitud cancelada",
}

_login_attempts_lock = Lock()
_login_attempts: dict[str, dict[str, object]] = {}
_whisper_model = None
_whisper_model_lock = Lock()
_firebase_app_initialized = False

UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
VEHICLE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
EMERGENCY_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected_digest = password_hash.split("$", 1)
    except ValueError:
        return False
    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return secrets.compare_digest(candidate_digest, expected_digest)


def login_attempt_key(account_type: str, email: str) -> str:
    return f"{account_type}:{email.lower().strip()}"


def get_login_attempt_state(account_type: str, email: str) -> dict[str, object]:
    key = login_attempt_key(account_type, email)
    with _login_attempts_lock:
        state = _login_attempts.get(key)
        if not state:
            return {"attempts": 0, "locked_until": None}
        locked_until = state.get("locked_until")
        if isinstance(locked_until, datetime) and locked_until <= datetime.utcnow():
            _login_attempts.pop(key, None)
            return {"attempts": 0, "locked_until": None}
        return dict(state)


def ensure_login_not_locked(account_type: str, email: str) -> None:
    state = get_login_attempt_state(account_type, email)
    locked_until = state.get("locked_until")
    if not isinstance(locked_until, datetime):
        return
    remaining_seconds = max(1, int((locked_until - datetime.utcnow()).total_seconds()))
    remaining_minutes = max(1, (remaining_seconds + 59) // 60)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "message": f"Demasiados intentos fallidos. Intenta nuevamente en {remaining_minutes} min.",
            "code": "LOGIN_ATTEMPTS_EXCEEDED",
            "account_type": account_type,
            "remaining_attempts": 0,
            "locked_until": locked_until.isoformat() + "Z",
        },
    )


def register_failed_login_attempt(account_type: str, email: str) -> None:
    key = login_attempt_key(account_type, email)
    with _login_attempts_lock:
        state = _login_attempts.get(key, {"attempts": 0, "locked_until": None})
        attempts = int(state.get("attempts") or 0) + 1
        remaining_attempts = max(0, LOGIN_MAX_ATTEMPTS - attempts)
        if attempts >= LOGIN_MAX_ATTEMPTS:
            locked_until = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            _login_attempts[key] = {"attempts": attempts, "locked_until": locked_until}
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Demasiados intentos fallidos. Intenta nuevamente en {LOGIN_LOCKOUT_MINUTES} min.",
                    "code": "LOGIN_ATTEMPTS_EXCEEDED",
                    "account_type": account_type,
                    "remaining_attempts": 0,
                    "locked_until": locked_until.isoformat() + "Z",
                },
            )
        _login_attempts[key] = {"attempts": attempts, "locked_until": None}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "message": "Correo o contraseña incorrectos",
            "code": "INVALID_CREDENTIALS",
            "account_type": account_type,
            "remaining_attempts": remaining_attempts,
        },
    )


def reset_login_attempts(account_type: str, email: str) -> None:
    with _login_attempts_lock:
        _login_attempts.pop(login_attempt_key(account_type, email), None)


def is_protected_admin_email(email: str) -> bool:
    return email.lower().strip() == PROTECTED_ADMIN_EMAIL


def is_protected_admin_role(role: str) -> bool:
    return role.lower().strip() == PROTECTED_ADMIN_ROLE


def normalize_role(role: str | None) -> str:
    normalized = (role or "").strip()
    if not normalized:
        return ""
    if normalized == PROTECTED_ADMIN_ROLE:
        return ROLE_SUPERADMIN_GLOBAL
    return normalized


def is_superadmin_global(role: str | None) -> bool:
    return normalize_role(role) == ROLE_SUPERADMIN_GLOBAL


def is_legacy_workshop(role: str | None) -> bool:
    return (role or "").strip() == WORKSHOP_ROLE


def workshop_login_status(approval_status: object) -> str:
    return "active" if str(approval_status) == "activo" else "pending"


def ensure_client_exists(client_id: int) -> None:
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_problem_type(problem_type: str) -> str:
    normalized = problem_type.strip()
    if normalized not in ALLOWED_EMERGENCY_PROBLEM_TYPES:
        allowed_values = ", ".join(sorted(ALLOWED_EMERGENCY_PROBLEM_TYPES))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"problem_type invalido. Valores permitidos: {allowed_values}",
        )
    return normalized


def normalize_text_for_matching(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def standardize_problem_type(
    problem_type: str,
    description: str | None,
    audio_transcript: str | None = None,
    photo_problem_type_standardized: str | None = None,
) -> str | None:
    if problem_type != "Otro":
        return problem_type if problem_type in STANDARDIZED_EMERGENCY_PROBLEM_TYPES else None
    candidate_text = " ".join(
        part
        for part in [normalize_optional_text(description), normalize_optional_text(audio_transcript)]
        if part
    )
    haystack = normalize_text_for_matching(candidate_text)
    if not haystack:
        return None
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("Batería", ("bateria", "arranque", "no enciende", "no quiere encender", "no arranca", "sin corriente", "descargada", "pasar corriente", "se apago")),
        ("Neumático", ("neumatico", "llanta", "pinch", "rueda", "revent", "desinflad", "goma")),
        ("Combustible", ("combustible", "gasolina", "diesel", "tanque", "sin gasolina", "sin diesel", "sin nafta")),
        ("Motor", ("motor", "sobrecalent", "humo", "temperatura", "radiador", "recalent", "aceite")),
        ("Sistema eléctrico", ("electrico", "eléctrico", "fusible", "cable", "corto", "tablero", "luces", "alternador")),
        ("Accidente", ("accidente", "choque", "colision", "colisión", "impacto", "atropell")),
        ("Cerrajería / llaves", ("llave", "llaves", "cerrajer", "cerrajeria", "cerrado", "quedaron dentro")),
    ]
    best_match = None
    best_score = 0
    for category, keywords in rules:
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score > best_score:
            best_match = category
            best_score = score
    if best_match is not None:
        return best_match
    if photo_problem_type_standardized in STANDARDIZED_EMERGENCY_PROBLEM_TYPES:
        return photo_problem_type_standardized
    return None


def determine_standardized_problem_type(
    problem_type: str,
    description: str | None,
    audio_transcript: str | None = None,
    photo_problem_type_standardized: str | None = None,
) -> str | None:
    return standardize_problem_type(problem_type, description, audio_transcript, photo_problem_type_standardized)


def resolve_emergency_price(price: int | None, standardized_problem_type: str | None) -> int | None:
    if price is not None:
        return price
    if standardized_problem_type is None:
        return None
    return EMERGENCY_BASE_PRICES.get(standardized_problem_type)


def extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    output = getattr(response, "output", None)
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if not isinstance(content, list):
                continue
            for part in content:
                text = getattr(part, "text", None)
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    return ""


def build_data_url_for_image(relative_path: str) -> str:
    absolute_path = (UPLOADS_ROOT / relative_path).resolve()
    try:
        absolute_path.relative_to(UPLOADS_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("Ruta de imagen invalida") from exc
    if not absolute_path.is_file():
        raise RuntimeError("No se encontro la imagen a clasificar")
    mime_type, _ = mimetypes.guess_type(absolute_path.name)
    encoded = base64.b64encode(absolute_path.read_bytes()).decode("ascii")
    return f"data:{mime_type or 'application/octet-stream'};base64,{encoded}"


def classify_emergency_photos(photo_relative_paths: list[str]) -> tuple[str | None, float | None, str | None]:
    if not photo_relative_paths or not settings.photo_classification_enabled:
        return None, None, None
    if OpenAI is None:
        return None, None, "La dependencia openai no esta instalada"
    if not os.getenv("OPENAI_API_KEY"):
        return None, None, "OPENAI_API_KEY no esta configurada"
    try:
        content: list[dict[str, object]] = [{
            "type": "input_text",
            "text": "Clasifica estas fotos de una emergencia vehicular en exactamente una categoria. Categorias permitidas: Batería, Neumático, Combustible, Motor, Sistema eléctrico, Accidente, Cerrajería / llaves. Responde solo JSON con este formato exacto: {\"category\":\"<categoria>\",\"confidence\":0.0,\"reason\":\"<breve>\"}",
        }]
        for photo_relative_path in photo_relative_paths:
            content.append({"type": "input_image", "image_url": build_data_url_for_image(photo_relative_path), "detail": "low"})
        response = OpenAI().responses.create(model=settings.photo_classification_model, input=[{"role": "user", "content": content}])
        parsed = json.loads(extract_response_text(response))
        category = parsed.get("category")
        confidence_raw = parsed.get("confidence")
        if category not in STANDARDIZED_EMERGENCY_PROBLEM_TYPES:
            return None, None, "La clasificacion visual devolvio una categoria invalida"
        confidence = None
        if isinstance(confidence_raw, (int, float)):
            confidence = max(0.0, min(float(confidence_raw), 1.0))
        return str(category), confidence, None
    except Exception as exc:
        logger.exception("No se pudo clasificar visualmente la emergencia")
        return None, None, str(exc)


def get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    with _whisper_model_lock:
        if _whisper_model is None:
            if whisper is None:
                raise RuntimeError("La dependencia openai-whisper no esta instalada")
            _whisper_model = whisper.load_model(settings.whisper_model)
    return _whisper_model


def transcribe_emergency_audio(audio_relative_path: str | None) -> tuple[str | None, str | None, str | None]:
    if not audio_relative_path:
        return None, None, None
    if not settings.whisper_enabled:
        return None, "disabled", None
    if shutil.which("ffmpeg") is None:
        return None, "error", "ffmpeg no esta disponible en el contenedor"
    absolute_path = (UPLOADS_ROOT / audio_relative_path).resolve()
    try:
        absolute_path.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return None, "error", "Ruta de audio invalida"
    if not absolute_path.is_file():
        return None, "error", "No se encontro el archivo de audio"
    try:
        options: dict[str, object] = {"fp16": False}
        language = normalize_optional_text(settings.whisper_language)
        if language:
            options["language"] = language
        result = get_whisper_model().transcribe(str(absolute_path), **options)
        transcript = normalize_optional_text(str(result.get("text", "")))
        return transcript, "completed", None
    except Exception as exc:
        logger.exception("No se pudo transcribir el audio de la emergencia")
        return None, "error", str(exc)


def build_public_upload_url(relative_path: str) -> str:
    return f"/uploads/{relative_path}"


def remove_file_if_exists(path: Path) -> None:
    if path.is_file():
        path.unlink()


def save_upload_with_limit(
    upload: UploadFile,
    *,
    destination_dir: Path,
    relative_dir: str,
    allowed_suffixes: set[str],
    max_bytes: int | None,
    invalid_type_detail: str,
    too_large_detail: str | None = None,
) -> tuple[str, str]:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_type_detail)
    filename = f"{uuid4().hex}{suffix}"
    relative_path = f"{relative_dir}/{filename}"
    absolute_path = destination_dir / filename
    bytes_written = 0
    with absolute_path.open("wb") as buffer:
        while chunk := upload.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if max_bytes is not None and bytes_written > max_bytes:
                buffer.close()
                remove_file_if_exists(absolute_path)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=too_large_detail)
            buffer.write(chunk)
    return relative_path, build_public_upload_url(relative_path)


def remove_uploaded_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    candidate = (UPLOADS_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return
    remove_file_if_exists(candidate)


def cleanup_uploaded_files(*relative_paths: str | None) -> None:
    for relative_path in relative_paths:
        remove_uploaded_file(relative_path)


def save_vehicle_photo(photo: UploadFile | None) -> tuple[str | None, str | None]:
    if photo is None or not photo.filename:
        return None, None
    return save_upload_with_limit(
        photo,
        destination_dir=VEHICLE_UPLOADS_DIR,
        relative_dir="vehicles",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=None,
        invalid_type_detail="La foto debe ser JPG, JPEG, PNG o WEBP",
    )


def save_emergency_photo(photo: UploadFile) -> tuple[str, str]:
    return save_upload_with_limit(
        photo,
        destination_dir=EMERGENCY_PHOTOS_DIR,
        relative_dir="emergencias/photos",
        allowed_suffixes=ALLOWED_PHOTO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_PHOTO_BYTES,
        invalid_type_detail="Cada foto debe ser JPG, JPEG, PNG o WEBP",
        too_large_detail="Cada foto puede pesar como maximo 20 MB",
    )


def save_emergency_audio(audio: UploadFile | None) -> tuple[str | None, str | None]:
    if audio is None or not audio.filename:
        return None, None
    return save_upload_with_limit(
        audio,
        destination_dir=EMERGENCY_AUDIO_DIR,
        relative_dir="emergencias/audio",
        allowed_suffixes=ALLOWED_AUDIO_SUFFIXES,
        max_bytes=MAX_EMERGENCY_AUDIO_BYTES,
        invalid_type_detail="El audio debe ser AAC, M4A, MP3, WAV, OGG o WEBM",
        too_large_detail="El audio puede pesar como maximo 40 MB",
    )


def remove_vehicle_photo(photo_path: str | None) -> None:
    remove_uploaded_file(photo_path)


def parse_json_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(decoded, list):
            return [str(item) for item in decoded]
    return []


def relative_upload_path_from_url(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)
    if not normalized:
        return None
    parsed_path = urlparse(normalized).path if normalized.startswith(("http://", "https://")) else normalized
    parsed_path = parsed_path.lstrip("/")
    if parsed_path.startswith("uploads/"):
        parsed_path = parsed_path.removeprefix("uploads/")
    if not parsed_path:
        return None
    candidate = (UPLOADS_ROOT / parsed_path).resolve()
    try:
        candidate.relative_to(UPLOADS_ROOT.resolve())
    except ValueError:
        return None
    return parsed_path if candidate.is_file() else None


def existing_upload_urls_from_media_lists(photo_paths: object, photo_urls: object) -> tuple[list[str], list[str]]:
    existing_paths: list[str] = []
    for raw_value in [*parse_json_string_list(photo_paths), *parse_json_string_list(photo_urls)]:
        relative_path = relative_upload_path_from_url(raw_value)
        if relative_path and relative_path not in existing_paths:
            existing_paths.append(relative_path)
    return existing_paths, [build_public_upload_url(relative_path) for relative_path in existing_paths]


def normalize_emergency_media_fields(row: dict[str, object]) -> dict[str, object]:
    existing_photo_paths, existing_photo_urls = existing_upload_urls_from_media_lists(row.get("photo_paths"), row.get("photo_urls"))
    row["photo_paths"] = existing_photo_paths
    row["photo_urls"] = existing_photo_urls
    audio_path = relative_upload_path_from_url(str(row.get("audio_path"))) if row.get("audio_path") else None
    audio_url_path = relative_upload_path_from_url(str(row.get("audio_url"))) if row.get("audio_url") else None
    existing_audio_path = audio_path or audio_url_path
    row["audio_path"] = existing_audio_path
    row["audio_url"] = build_public_upload_url(existing_audio_path) if existing_audio_path else None
    return row


def ensure_firebase_app() -> bool:
    global _firebase_app_initialized
    if _firebase_app_initialized:
        return True
    if not settings.fcm_enabled:
        return False
    if firebase_admin is None or credentials is None:
        logger.warning("FCM habilitado, pero firebase-admin no esta instalado")
        return False
    credentials_path = normalize_optional_text(settings.firebase_credentials_path)
    if not credentials_path:
        logger.warning("FCM habilitado, pero FIREBASE_CREDENTIALS_PATH no esta configurado")
        return False
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))
        _firebase_app_initialized = True
        return True
    except Exception:
        logger.exception("No se pudo inicializar Firebase Admin SDK")
        return False


def firebase_push_is_ready() -> tuple[bool, str | None]:
    if not settings.fcm_enabled:
        return False, "FCM no está habilitado en este entorno"
    if firebase_admin is None or credentials is None or messaging is None:
        return False, "Firebase Admin SDK no está disponible"
    credentials_path = normalize_optional_text(settings.firebase_credentials_path)
    if not credentials_path:
        return False, "FIREBASE_CREDENTIALS_PATH no está configurado"
    if not ensure_firebase_app():
        return False, "No se pudo inicializar Firebase Admin SDK"
    return True, None


def is_sensitive_push_event(data: Mapping[str, str]) -> bool:
    push_type = str(data.get("type", "")).strip().lower()
    sensitive_prefixes = ("emergency_", "quotation_", "technician_", "payment_")
    if any(push_type.startswith(prefix) for prefix in sensitive_prefixes):
        return True
    sensitive_keys = {
        "emergency_id",
        "quotation_request_id",
        "quotation_id",
        "user_id",
        "tenant_id",
        "tenant_slug",
        "status",
        "status_label",
        "payment_id",
        "technician_id",
    }
    return any(key in data and str(data.get(key, "")).strip() != "" for key in sensitive_keys)


def build_push_delivery(
    *,
    title: str,
    body: str,
    data: Mapping[str, str],
    prefer_visible_notification: bool = False,
) -> dict[str, object]:
    normalized_data = {str(key): str(value) for key, value in data.items()}
    sensitive = is_sensitive_push_event(normalized_data)
    notification_title: str | None = title
    notification_body: str | None = body
    mode = "full_notification"

    if sensitive:
        if prefer_visible_notification:
            notification_title = "Tienes una actualización"
            notification_body = "Abre la app para revisar"
            mode = "generic_notification"
        else:
            notification_title = None
            notification_body = None
            mode = "data_only"

    return {
        "data": normalized_data,
        "notification_title": notification_title,
        "notification_body": notification_body,
        "mode": mode,
        "sensitive": sensitive,
    }


def send_push_to_device_token(
    *,
    token: str,
    title: str,
    body: str,
    data: Mapping[str, str],
    prefer_visible_notification: bool = False,
) -> tuple[str, dict[str, object]]:
    ready, error_detail = firebase_push_is_ready()
    if not ready or messaging is None:
        raise RuntimeError(error_detail or "Firebase Admin SDK no está disponible")
    delivery = build_push_delivery(
        title=title,
        body=body,
        data=data,
        prefer_visible_notification=prefer_visible_notification,
    )
    notification = None
    if delivery["notification_title"] is not None and delivery["notification_body"] is not None:
        notification = messaging.Notification(
            title=str(delivery["notification_title"]),
            body=str(delivery["notification_body"]),
        )
    message_id = str(
        messaging.send(
            messaging.Message(
                notification=notification,
                data=dict(delivery["data"]),
                token=token,
            )
        )
    )
    return message_id, delivery


def send_push_to_client(client_id: int | None, title: str, body: str, data: dict[str, str]) -> None:
    if client_id is None:
        return
    try:
        create_notification(
            {
                "user_id": client_id,
                "title": title,
                "message": body,
                "payload_json": json.dumps(data, ensure_ascii=False),
            }
        )
    except Exception:
        logger.exception("No se pudo persistir notificación para el usuario %s", client_id)
    try:
        from app.tenant_context import get_tenant

        tenant = get_tenant()
        if tenant is not None:
            devices = list_active_device_fcm_tokens(
                user_id=client_id,
                role=ROLE_CLIENTE,
                tenant_id=int(tenant["id"]) if tenant.get("id") is not None else None,
                tenant_slug=str(tenant["slug"]) if tenant.get("slug") is not None else None,
                sucursal_id=None,
            )
        else:
            devices = list_active_device_fcm_tokens(
                user_id=client_id,
                role="client",
                tenant_id=None,
                tenant_slug=None,
                sucursal_id=None,
            )
            if not devices:
                devices = list_active_device_fcm_tokens_default(client_id)
    except Exception:
        logger.exception("No se pudieron consultar tokens FCM del cliente %s", client_id)
        return
    ready, _ = firebase_push_is_ready()
    if not devices or not ready:
        return
    for device in devices:
        token = str(device.get("fcm_token", "")).strip()
        if not token:
            continue
        try:
            send_push_to_device_token(token=token, title=title, body=body, data=data)
        except Exception:
            logger.exception("No se pudo enviar push FCM al cliente %s", client_id)


def send_emergency_status_update_notification(
    client_id: int | None,
    emergency_id: int,
    status: str,
    status_label: str,
) -> None:
    if client_id is None:
        logger.warning(
            "No se enviara emergency_status_updated para emergencia %s porque no tiene client_id",
            emergency_id,
        )
        return
    logger.warning(
        "Intentando enviar emergency_status_updated para emergencia %s al cliente %s con estado %s",
        emergency_id,
        client_id,
        status,
    )
    send_push_to_client(
        client_id,
        "Estado actualizado",
        f"Tu solicitud ahora está: {status_label}",
        {
            "type": "emergency_status_updated",
            "emergency_id": str(emergency_id),
            "status": status,
            "status_label": status_label,
        },
    )


def send_emergency_rejected_notification(
    client_id: int | None,
    emergency_id: int,
    rejection_reason: str,
) -> None:
    if client_id is None:
        logger.warning(
            "No se enviara emergency_rejected para emergencia %s porque no tiene client_id",
            emergency_id,
        )
        return
    compact_reason = compact_push_text(rejection_reason, fallback="Sin motivo informado", max_length=140)
    logger.warning(
        "Intentando enviar emergency_rejected para emergencia %s al cliente %s",
        emergency_id,
        client_id,
    )
    send_push_to_client(
        client_id,
        "Solicitud rechazada",
        f"Tu solicitud fue rechazada: {compact_reason}",
        {
            "type": "emergency_rejected",
            "emergency_id": str(emergency_id),
            "status": "solicitud_cancelada",
            "status_label": "Solicitud rechazada",
            "rejection_reason": compact_reason,
        },
    )


def send_emergency_reassigned_notification(
    client_id: int | None,
    emergency_id: int,
    *,
    new_workshop_id: int,
    new_workshop_name: str,
) -> None:
    if client_id is None:
        logger.warning(
            "No se enviara emergency_reassigned para emergencia %s porque no tiene client_id",
            emergency_id,
        )
        return
    workshop_name = compact_push_text(new_workshop_name, fallback="Otro taller disponible", max_length=80)
    logger.warning(
        "Intentando enviar emergency_reassigned para emergencia %s al cliente %s hacia taller %s",
        emergency_id,
        client_id,
        new_workshop_id,
    )
    send_push_to_client(
        client_id,
        "Solicitud reasignada",
        "Tu solicitud fue enviada a otro taller disponible",
        {
            "type": "emergency_reassigned",
            "emergency_id": str(emergency_id),
            "status": "en_revision",
            "status_label": "En revisión",
            "new_workshop_id": str(new_workshop_id),
            "new_workshop_name": workshop_name,
            "message": "Tu solicitud fue enviada a otro taller disponible",
        },
    )


def send_quotation_request_sent(
    workshop_id: int,
    quotation_id: int,
    emergency_id: int | None,
    status: str,
) -> None:
    """Notifica al taller que recibió una nueva solicitud de cotización."""
    logger.warning(
        "Enviando quotation_request_sent: quotation=%s workshop=%s emergency=%s",
        quotation_id, workshop_id, emergency_id,
    )
    send_push_to_client(
        workshop_id,
        "Nueva solicitud de cotización",
        "Se te ha invitado a cotizar una emergencia vehicular.",
        {
            "type": "quotation_request_sent",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": status,
            "workshop_name": "",
            "price": "",
        },
    )


def send_quotation_offer_received(
    client_id: int | None,
    quotation_id: int,
    emergency_id: int | None,
    workshop_name: str,
    price: float | None,
) -> None:
    """Notifica al cliente que un taller envió una propuesta de cotización."""
    if client_id is None:
        logger.warning("quotation_offer_received: sin client_id para quotation %s", quotation_id)
        return
    wname = compact_push_text(workshop_name, fallback="Un taller", max_length=80)
    price_str = f"Bs. {price:.2f}" if price is not None else "—"
    logger.warning(
        "Enviando quotation_offer_received: quotation=%s client=%s taller=%s",
        quotation_id, client_id, wname,
    )
    send_push_to_client(
        client_id,
        "Nueva propuesta recibida",
        f"{wname} envió una cotización: {price_str}",
        {
            "type": "quotation_offer_received",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": "con_propuestas",
            "workshop_name": wname,
            "price": str(price) if price is not None else "",
        },
    )


def send_quotation_offer_selected(
    workshop_id: int,
    quotation_id: int,
    emergency_id: int | None,
    price: float | None,
) -> None:
    """Notifica al taller que su propuesta fue seleccionada."""
    logger.warning(
        "Enviando quotation_offer_selected: quotation=%s workshop=%s",
        quotation_id, workshop_id,
    )
    price_str = f"Bs. {price:.2f}" if price is not None else "—"
    send_push_to_client(
        workshop_id,
        "¡Propuesta seleccionada!",
        f"Tu cotización de {price_str} fue seleccionada por el cliente.",
        {
            "type": "quotation_offer_selected",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": "seleccionado",
            "workshop_name": "",
            "price": str(price) if price is not None else "",
        },
    )


def send_quotation_offer_not_selected(
    workshop_id: int,
    quotation_id: int,
    emergency_id: int | None,
) -> None:
    """Notifica al taller que su propuesta NO fue seleccionada por el cliente."""
    logger.warning(
        "Enviando quotation_offer_not_selected: quotation=%s workshop=%s",
        quotation_id, workshop_id,
    )
    send_push_to_client(
        workshop_id,
        "Cotización no seleccionada",
        "El cliente seleccionó otra propuesta para esta emergencia.",
        {
            "type": "quotation_offer_not_selected",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": "rechazada",
            "workshop_name": "",
            "price": "",
        },
    )


def send_quotation_expired(
    client_id: int | None,
    quotation_id: int,
    emergency_id: int | None,
) -> None:
    """Notifica al cliente que su solicitud de cotización expiró sin selección."""
    if client_id is None:
        logger.warning("quotation_expired: sin client_id para quotation %s", quotation_id)
        return
    logger.warning("Enviando quotation_expired: quotation=%s client=%s", quotation_id, client_id)
    send_push_to_client(
        client_id,
        "Cotización expirada",
        "Tu solicitud de cotización expiró sin propuesta seleccionada.",
        {
            "type": "quotation_expired",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": "expirado",
            "workshop_name": "",
            "price": "",
        },
    )


def send_quotation_request_cancelled(
    client_id: int | None,
    quotation_id: int,
    emergency_id: int | None,
) -> None:
    """Notifica al cliente que su solicitud de cotización fue cancelada."""
    if client_id is None:
        logger.warning("quotation_request_cancelled: sin client_id para quotation %s", quotation_id)
        return
    logger.warning("Enviando quotation_request_cancelled: quotation=%s client=%s", quotation_id, client_id)
    send_push_to_client(
        client_id,
        "Cotización cancelada",
        "Tu solicitud de cotización fue cancelada.",
        {
            "type": "quotation_request_cancelled",
            "quotation_id": str(quotation_id),
            "emergency_id": str(emergency_id) if emergency_id is not None else "",
            "status": "cancelado",
            "workshop_name": "",
            "price": "",
        },
    )


def compact_push_text(value: object, *, fallback: str, max_length: int = 120) -> str:
    text_value = normalize_optional_text(str(value)) if value is not None else None
    if not text_value:
        return fallback
    single_line = re.sub(r"\s+", " ", text_value)
    if len(single_line) <= max_length:
        return single_line
    return f"{single_line[: max_length - 3].rstrip()}..."


def calculate_distance_meters(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    earth_radius_meters = 6_371_000
    origin_latitude_radians = math.radians(origin_latitude)
    destination_latitude_radians = math.radians(destination_latitude)
    latitude_delta = math.radians(destination_latitude - origin_latitude)
    longitude_delta = math.radians(destination_longitude - origin_longitude)
    haversine_value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    angular_distance = 2 * math.atan2(math.sqrt(haversine_value), math.sqrt(1 - haversine_value))
    return earth_radius_meters * angular_distance


def emergency_incident_label(report: Mapping[str, object]) -> str:
    return compact_push_text(
        report.get("description")
        or report.get("problem_type_standardized")
        or report.get("problem_type")
        or report.get("vehicle_name"),
        fallback="Incidente reportado",
    )


def push_coordinate(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return None


def add_coordinate_pair(
    data: dict[str, str],
    *,
    latitude_key: str,
    longitude_key: str,
    latitude: object,
    longitude: object,
) -> None:
    normalized_latitude = push_coordinate(latitude)
    normalized_longitude = push_coordinate(longitude)
    if normalized_latitude is None or normalized_longitude is None:
        return
    data[latitude_key] = normalized_latitude
    data[longitude_key] = normalized_longitude


# =============================================================================
# JWT / MULTI-TENANT — autenticación real con claims de tenant
# =============================================================================

_http_bearer = HTTPBearer(auto_error=False)


class TokenPayload:
    """Payload extraído del JWT de acceso.

    Campos base (todos los roles):
      user_id, role, tenant_id

    Campos extendidos (roles Database-Per-Tenant):
      tenant_slug  → slug del tenant en saas_master (para resolver el engine)
      sucursal_id  → sucursal asignada (None para SUPERADMIN_TENANT)
    """

    def __init__(
        self,
        user_id: int,
        role: str,
        tenant_id: int | None,
        tenant_slug: str | None = None,
        sucursal_id: int | None = None,
        technician_id: int | None = None,
    ) -> None:
        self.user_id = user_id
        self.role = role
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.sucursal_id = sucursal_id
        self.technician_id = technician_id

    @property
    def is_tenant_user(self) -> bool:
        return normalize_role(self.role) in TENANT_ROLES

    @property
    def is_global_admin(self) -> bool:
        return is_superadmin_global(self.role)


def create_access_token(
    user_id: int,
    role: str,
    tenant_id: int | None,
    tenant_slug: str | None = None,
    sucursal_id: int | None = None,
    technician_id: int | None = None,
) -> str:
    """Genera un JWT firmado con claims multi-tenant."""
    now = datetime.now(timezone.utc)
    normalized_role = normalize_role(role)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "user_id": user_id,
        "role": normalized_role,
        "rol": normalized_role,
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug,
        "sucursal_id": sucursal_id,
        "technician_id": technician_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    """Decodifica y valida la firma del JWT. Lanza JWTError si no es válido."""
    return pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def _payload_to_token(payload: dict) -> TokenPayload:
    """Convierte un dict de JWT decodificado en TokenPayload."""
    resolved_role = normalize_role(str(payload.get("role") or payload.get("rol") or ""))
    token = TokenPayload(
        user_id=int(payload["user_id"]),
        role=resolved_role,
        tenant_id=int(payload["tenant_id"]) if payload.get("tenant_id") is not None else None,
        tenant_slug=str(payload["tenant_slug"]) if payload.get("tenant_slug") else None,
        sucursal_id=int(payload["sucursal_id"]) if payload.get("sucursal_id") is not None else None,
        technician_id=int(payload["technician_id"]) if payload.get("technician_id") is not None else None,
    )
    if token.is_tenant_user and (token.tenant_id is None or not token.tenant_slug):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOKEN_TENANT_INVALIDO",
        )
    return token


def get_effective_technician_id(current_user: TokenPayload | None) -> int | None:
    """Devuelve el ID operativo del técnico para filtros de emergencias/WS."""
    if current_user is None or normalize_role(current_user.role) != ROLE_TECNICO:
        return None
    if current_user.technician_id is not None:
        return current_user.technician_id
    return current_user.user_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> TokenPayload:
    """Dependencia FastAPI que extrae y valida el JWT del header Authorization."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOKEN_SIN_TENANT",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    role = normalize_role(str(payload.get("role") or payload.get("rol") or ""))
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_SIN_TENANT")
    return _payload_to_token(payload)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> TokenPayload | None:
    """Igual que get_current_user pero no falla si no hay token (endpoints públicos)."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return _payload_to_token(payload)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def require_admin(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Dependencia FastAPI: sólo permite rol 'admin'."""
    if not current_user.is_global_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACCESO_DENEGADO_TENANT")
    return current_user


def validate_tenant_access(record: dict[str, object], current_user: TokenPayload) -> None:
    """Valida que un registro pertenece al tenant del usuario autenticado.

    Admin puede acceder a todo. Workshop/client sólo a su propio tenant.
    """
    if current_user.is_global_admin:
        return
    record_tenant = record.get("tenant_id")
    if record_tenant is not None and int(record_tenant) != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="REGISTRO_NO_PERTENECE_AL_TENANT")


def get_tenant_id_for_query(current_user: TokenPayload | None) -> int | None:
    """Devuelve el tenant_id a usar en una consulta SQL.

    - admin / SUPERADMIN_GLOBAL (o sin token): None → sin filtro → ve todo
    - workshop / tenant roles: su propio tenant_id → filtro aplicado
    """
    if current_user is None or current_user.is_global_admin:
        return None
    return current_user.tenant_id


def require_superadmin_global(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Dependencia: solo SUPERADMIN_GLOBAL o admin clásico puede acceder."""
    if not current_user.is_global_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO_SUPERADMIN_GLOBAL")
    return current_user


def require_superadmin_tenant(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Dependencia: SUPERADMIN_TENANT o superior puede acceder."""
    allowed = {ROLE_SUPERADMIN_TENANT, ROLE_SUPERADMIN_GLOBAL}
    if normalize_role(current_user.role) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO_SUPERADMIN_TENANT")
    return current_user


def require_admin_sucursal(
    current_user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Dependencia: ADMIN_SUCURSAL o superior puede acceder."""
    allowed = {
        ROLE_ADMIN_SUCURSAL, ROLE_SUPERADMIN_TENANT, ROLE_SUPERADMIN_GLOBAL,
    }
    if normalize_role(current_user.role) not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SOLO_ADMIN_SUCURSAL")
    return current_user
