from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.dashboard import router as dashboard_router
from app.routes.devices import router as devices_router
from app.routes.emergencies import router as emergencies_router
from app.routes.health import router as health_router
from app.routes.technicians import router as technicians_router
from app.routes.vehicles import router as vehicles_router
from app.routes.workshops import router as workshops_router

route_routers = [
    health_router,
    dashboard_router,
    devices_router,
    workshops_router,
    clients_router,
    auth_router,
    technicians_router,
    vehicles_router,
    emergencies_router,
]
