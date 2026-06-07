from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.dashboard import router as dashboard_router
from app.routes.devices import router as devices_router
from app.routes.emergencies import router as emergencies_router
from app.routes.health import router as health_router
from app.routes.public import router as public_router
from app.routes.realtime import router as realtime_router
from app.routes.quotations import router as quotations_router
from app.routes.saas import router as saas_router
from app.routes.sucursales import router as sucursales_router
from app.routes.technicians import router as technicians_router
from app.routes.tenants import router as tenants_router
from app.routes.usuarios_tenant import router as usuarios_tenant_router
from app.routes.vehicles import router as vehicles_router
from app.routes.workshops import router as workshops_router

route_routers = [
    health_router,
    public_router,          # /api/public/* — sin autenticación
    realtime_router,
    tenants_router,         # /api/tenants (legacy multi-tenant)
    saas_router,            # /api/saas/* — SUPERADMIN_GLOBAL
    sucursales_router,      # /api/sucursales — gestión de sucursales
    usuarios_tenant_router, # /api/tenant/usuarios — usuarios por tenant
    dashboard_router,
    devices_router,
    workshops_router,
    clients_router,
    auth_router,
    technicians_router,
    vehicles_router,
    emergencies_router,
    quotations_router,
]
