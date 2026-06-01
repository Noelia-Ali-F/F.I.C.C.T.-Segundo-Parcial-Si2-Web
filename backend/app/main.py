import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

for router in route_routers:
    app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    try:
        init_database()
    except OperationalError:
        logger.exception("No se pudo inicializar la base de datos en startup")
