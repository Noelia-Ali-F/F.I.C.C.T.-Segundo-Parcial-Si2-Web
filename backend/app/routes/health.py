from fastapi import APIRouter

from app.config import settings
from app.db import check_database_connection

# =========================================================
# ARCHIVO DE RUTAS DE SALUD DEL BACKEND
# Aqui esta lo necesario para revisar si el backend esta funcionando.
# Este archivo contiene:
# - una ruta raiz simple
# - una ruta de healthcheck
# - una funcion para validar si la base de datos responde
# Palabras clave para buscar despues:
# HEALTH, HEALTHCHECK, ROOT, ESTADO BACKEND, BASE DE DATOS
# =========================================================
router = APIRouter(tags=["health"])


"""
Aqui esta la logica de salud del sistema que revisa
si el backend y la base de datos estan respondiendo correctamente.
"""
def health_status() -> dict[str, object]:
    try:
        database_ok = check_database_connection()
    except Exception:
        database_ok = False
    return {
        "status": "ok",
        "environment": settings.app_env,
        "database": "connected" if database_ok else "unavailable",
    }


# =========================================================
# CONTROLADORES HTTP DE SALUD DEL SISTEMA
# En esta seccion estan los endpoints de verificacion basica.
# Aqui vas a encontrar:
# - GET de la ruta raiz
# - GET de health para revisar estado del backend y la base de datos
# =========================================================
@router.get("/")
# Aqui esta el controlador GET de la ruta raiz que responde con un mensaje basico del backend.
def read_root() -> dict[str, str]:
    return {"message": "Backend running"}


@router.get(f"{settings.api_prefix}/health")
# Aqui esta el controlador GET de salud que verifica el estado del backend y la base de datos.
def healthcheck() -> dict[str, object]:
    return health_status()
