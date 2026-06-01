from collections.abc import Mapping
from datetime import datetime, timedelta
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

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.db import get_client_by_id, list_active_device_fcm_tokens

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


def send_push_to_client(client_id: int | None, title: str, body: str, data: dict[str, str]) -> None:
    if client_id is None:
        return
    try:
        devices = list_active_device_fcm_tokens(client_id)
    except Exception:
        logger.exception("No se pudieron consultar tokens FCM del cliente %s", client_id)
        return
    if not devices or not ensure_firebase_app() or messaging is None:
        return
    for device in devices:
        token = str(device.get("fcm_token", "")).strip()
        if not token:
            continue
        try:
            messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=data,
                    token=token,
                )
            )
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
