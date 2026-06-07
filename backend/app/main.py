import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.db import init_database
from app.routes import route_routers
from app.utils import UPLOADS_ROOT

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.app_debug, version="0.1.0")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_ROOT)), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^https?://("
        r"localhost|"
        r"127\.0\.0\.1|"
        r"10\.\d+\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+|"
        r"\d+\.\d+\.\d+\.\d+"
        r")(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware: resuelve el engine del tenant en cada request
#
# Si el JWT incluye tenant_slug, busca en saas_master y conecta al engine
# específico del tenant. El ContextVar se limpia después de cada request.
# Los roles legacy (admin, workshop, client) no tienen tenant_slug en su JWT
# y continúan usando el engine por defecto (diagramador).
# =============================================================================
@app.middleware("http")
async def tenant_engine_middleware(request: Request, call_next) -> Response:
    from app.tenant_context import clear_engine, set_context

    resolved = False
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from app.utils import _payload_to_token, decode_access_token
            payload = decode_access_token(token)
            current_user = _payload_to_token(payload)
            if current_user.is_tenant_user:
                from app.saas_master import get_tenant_by_slug_any
                from app.tenant_manager import get_tenant_engine
                tenant = get_tenant_by_slug_any(str(current_user.tenant_slug))
                if not tenant:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "TENANT_NO_ENCONTRADO"},
                    )
                if int(tenant["id"]) != int(current_user.tenant_id):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "TENANT_TOKEN_MISMATCH"},
                    )
                if tenant.get("estado") != "activo":
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "TENANT_INACTIVO"},
                    )
                engine = get_tenant_engine(tenant)
                set_context(engine, tenant)
                resolved = True
        except Exception as exc:
            detail = getattr(exc, "detail", None)
            status_code = getattr(exc, "status_code", None)
            if status_code is not None and detail is not None:
                return JSONResponse(status_code=status_code, content={"detail": detail})
            return JSONResponse(status_code=401, content={"detail": "Token inválido"})

    try:
        response = await call_next(request)
    finally:
        if resolved:
            clear_engine()

    return response


for router in route_routers:
    app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    # 1. BD principal (diagramador) — backward compatible
    try:
        init_database()
    except OperationalError:
        logger.exception("No se pudo inicializar la base de datos principal en startup")

    # 2. BD saas_master — tenant registry
    try:
        from app.saas_master import init_saas_master
        init_saas_master()
    except Exception:
        logger.exception("No se pudo inicializar saas_master en startup")
