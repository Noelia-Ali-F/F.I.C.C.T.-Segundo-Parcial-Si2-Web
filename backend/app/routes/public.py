"""
Rutas públicas (sin autenticación).

POST /api/public/registro-taller   → registra una nueva empresa como tenant
GET  /api/public/planes            → lista planes disponibles (para mostrar en la landing)
"""
import logging
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["public"])
DEFAULT_PUBLIC_SPECIALTY = "Mecánica general"


# =============================================================================
# Modelos
# =============================================================================

class RegistroTallerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Datos de la empresa
    nombre: str = Field(min_length=3, max_length=200)
    razon_social: str | None = Field(default=None, max_length=300)
    nit: str | None = Field(default=None, max_length=50)
    correo: EmailStr
    telefono: str | None = Field(default=None, max_length=50)
    direccion_principal: str | None = Field(default=None, max_length=400)
    zona: str | None = Field(default=None, max_length=120)
    ciudad: str = Field(default="Santa Cruz", max_length=120)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    plan_id: int | None = Field(default=None, ge=1)

    # Cuenta del SUPERADMIN_TENANT (primer usuario del taller)
    admin_nombre: str = Field(min_length=3, max_length=160)
    admin_email: EmailStr
    admin_password: str = Field(min_length=6, max_length=255)
    admin_confirm_password: str = Field(min_length=6, max_length=255)
    admin_telefono: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def passwords_deben_coincidir(self) -> "RegistroTallerRequest":
        if self.admin_password != self.admin_confirm_password:
            raise ValueError("Las contraseñas del administrador no coinciden")
        return self


class RegistroTallerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: int
    slug: str
    nombre: str
    database_name: str
    sucursal_principal_id: int | None = None
    workshop_principal_id: int | None = None
    admin_email: str
    mensaje: str


# =============================================================================
# Controladores
# =============================================================================

@router.post(
    f"{settings.api_prefix}/public/registro-taller",
    response_model=RegistroTallerResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_taller(payload: RegistroTallerRequest, request: Request) -> RegistroTallerResponse:
    """
    Registra una nueva empresa en el SaaS.

    Flujo:
      1. Valida que el correo no esté registrado en saas_master.
      2. Genera un slug único basado en el nombre.
      3. Crea la base de datos del tenant (ej: tenant_mecanicos_express).
      4. Ejecuta el schema completo en esa BD.
      5. Crea el SUPERADMIN_TENANT en usuarios_tenant.
      6. Registra el tenant en saas_master.tenants con connection info.
    """
    from app.saas_master import (
        create_saas_tenant,
        create_subscription,
        delete_saas_tenant,
        generate_unique_slug,
        get_tenant_by_correo,
        get_plan_by_id,
        list_planes,
        registrar_auditoria,
    )
    from app.tenant_manager import (
        create_tenant_database,
        drop_tenant_database,
        get_tenant_engine,
        init_tenant_schema,
    )
    from app.routes.sucursales import SucursalCreate, get_or_create_workshop_for_sucursal
    from app.utils import hash_password, ROLE_SUPERADMIN_TENANT

    correo_empresa = str(payload.correo).lower().strip()
    admin_email = str(payload.admin_email).lower().strip()

    # 1. Verificar unicidad de correo
    if get_tenant_by_correo(correo_empresa):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una empresa registrada con ese correo",
        )

    # 2. Validar plan (si se envió)
    plan_id = payload.plan_id
    if plan_id is not None:
        planes_activos = list_planes(solo_activos=True)
        if not any(p["id"] == plan_id for p in planes_activos):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan seleccionado no válido o inactivo",
            )

    plan = None
    if plan_id is not None:
        plan = get_plan_by_id(plan_id)

    # 3. Generar slug y nombre de BD
    slug = generate_unique_slug(payload.nombre)
    db_name = f"tenant_{slug}"

    logger.info("Registrando nuevo tenant: nombre=%s slug=%s bd=%s", payload.nombre, slug, db_name)

    # 4. Crear base de datos PostgreSQL del tenant
    try:
        create_tenant_database(db_name)
    except Exception as exc:
        logger.exception("Error creando BD del tenant: %s", db_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando base de datos del tenant: {exc}",
        ) from exc

    # 5. Registrar tenant en saas_master ANTES de crear el schema
    #    (necesitamos el tenant_id para relacionar suscripción si fuera necesario)
    tenant_info_data = {
        "nombre": payload.nombre,
        "slug": slug,
        "razon_social": payload.razon_social,
        "nit": payload.nit,
        "correo": correo_empresa,
        "telefono": payload.telefono,
        "direccion_principal": payload.direccion_principal,
        "zona": payload.zona,
        "ciudad": payload.ciudad,
        "latitud": payload.latitud,
        "longitud": payload.longitud,
        "database_name": db_name,
        "database_host": settings.postgres_host,
        "database_port": settings.postgres_port,
        "database_user": settings.postgres_user,
        "database_password": settings.postgres_password,
        "plan_id": plan_id,
    }
    tenant_record: dict | None = None
    created_tenant_id: int | None = None
    try:
        tenant_record = create_saas_tenant(tenant_info_data)
        created_tenant_id = int(tenant_record["id"])
    except Exception as exc:
        logger.exception("Error registrando tenant en saas_master")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registrando empresa en saas_master: {exc}",
        ) from exc

    # 6. Inicializar schema en la BD del tenant
    try:
        init_tenant_schema(tenant_record)
    except Exception as exc:
        logger.exception("Error inicializando schema del tenant: %s", db_name)
        if created_tenant_id is not None:
            try:
                delete_saas_tenant(created_tenant_id)
            except Exception:
                logger.exception("No se pudo eliminar tenant huérfano %s tras fallo de schema", created_tenant_id)
        try:
            drop_tenant_database(db_name)
        except Exception:
            logger.exception("No se pudo eliminar BD huérfana %s tras fallo de schema", db_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inicializando schema del tenant: {exc}",
        ) from exc

    # 7. Crear bootstrap operativo inicial del tenant:
    #    - sucursal principal
    #    - SUPERADMIN_TENANT
    #    - taller principal
    #    - suscripcion inicial
    from sqlalchemy import text

    password_hash = hash_password(payload.admin_password)
    sucursal_principal_id: int | None = None
    workshop_principal_id: int | None = None
    try:
        engine = get_tenant_engine(tenant_record)
        with engine.begin() as conn:
            sucursal_row = conn.execute(
                text("""
                    INSERT INTO sucursales (nombre, direccion, zona, ciudad, latitud, longitud, telefono, responsable, estado)
                    VALUES (:nombre, :direccion, :zona, :ciudad, :latitud, :longitud, :telefono, :responsable, 'activo')
                    RETURNING id
                """),
                {
                    "nombre": f"Sucursal Principal - {payload.nombre}",
                    "direccion": payload.direccion_principal or "",
                    "zona": payload.zona,
                    "ciudad": payload.ciudad,
                    "latitud": payload.latitud,
                    "longitud": payload.longitud,
                    "telefono": payload.telefono or payload.admin_telefono,
                    "responsable": payload.admin_nombre,
                },
            ).mappings().first()
            sucursal_principal_id = int(sucursal_row["id"]) if sucursal_row else None

            conn.execute(
                text("""
                    INSERT INTO usuarios_tenant (email, full_name, phone, password_hash, role, sucursal_id, estado)
                    VALUES (:email, :full_name, :phone, :password_hash, :role, :sucursal_id, 'activo')
                    ON CONFLICT (email) DO NOTHING
                """),
                {
                    "email": admin_email,
                    "full_name": payload.admin_nombre,
                    "phone": payload.admin_telefono or "",
                    "password_hash": password_hash,
                    "role": ROLE_SUPERADMIN_TENANT,
                    "sucursal_id": sucursal_principal_id,
                },
            )

            workshop_row = get_or_create_workshop_for_sucursal(
                conn,
                current_user=SimpleNamespace(tenant_slug=slug, role=ROLE_SUPERADMIN_TENANT),
                sucursal_id=int(sucursal_principal_id),
                payload=SucursalCreate(
                    nombre=f"Sucursal Principal - {payload.nombre}",
                    direccion=payload.direccion_principal or "",
                    zona=payload.zona,
                    ciudad=payload.ciudad,
                    latitud=payload.latitud,
                    longitud=payload.longitud,
                    telefono=payload.telefono or payload.admin_telefono,
                    responsable=payload.admin_nombre,
                    especialidades=[DEFAULT_PUBLIC_SPECIALTY],
                ),
            )
            if workshop_row:
                conn.execute(
                    text(
                        """
                        UPDATE workshop_registrations
                        SET email = :email
                        WHERE id = :id
                        """
                    ),
                    {"id": int(workshop_row["id"]), "email": correo_empresa},
                )
            workshop_principal_id = int(workshop_row["id"]) if workshop_row else None

        effective_plan_id = plan_id
        if effective_plan_id is None:
            planes_activos = list_planes(solo_activos=True)
            effective_plan_id = int(planes_activos[0]["id"]) if planes_activos else None
        if effective_plan_id is not None:
            create_subscription(
                tenant_id=int(tenant_record["id"]),
                plan_id=effective_plan_id,
                monto=float(plan["precio_mensual"]) if plan is not None and effective_plan_id == plan_id else 0,
                estado="activo",
                metodo_pago="registro_inicial",
            )
    except Exception as exc:
        logger.exception("Error creando SUPERADMIN_TENANT en tenant BD: %s", db_name)
        if created_tenant_id is not None:
            try:
                delete_saas_tenant(created_tenant_id)
            except Exception:
                logger.exception("No se pudo eliminar tenant huérfano %s tras fallo de bootstrap", created_tenant_id)
        try:
            drop_tenant_database(db_name)
        except Exception:
            logger.exception("No se pudo eliminar BD huérfana %s tras fallo de bootstrap", db_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando bootstrap inicial del tenant: {exc}",
        ) from exc

    # 8. Auditoría global
    client_ip = request.client.host if request.client else None
    registrar_auditoria(
        "TENANT_REGISTRADO",
        tenant_id=tenant_record["id"],
        descripcion=(
            f"Empresa '{payload.nombre}' registrada. Admin: {admin_email}. "
            f"Sucursal principal: {sucursal_principal_id}. Taller principal: {workshop_principal_id}"
        ),
        ip=client_ip,
    )

    logger.info(
        "Tenant registrado exitosamente: id=%s slug=%s", tenant_record["id"], slug
    )

    return RegistroTallerResponse(
        tenant_id=tenant_record["id"],
        slug=slug,
        nombre=payload.nombre,
        database_name=db_name,
        sucursal_principal_id=sucursal_principal_id,
        workshop_principal_id=workshop_principal_id,
        admin_email=admin_email,
        mensaje=(
            f"Empresa '{payload.nombre}' registrada correctamente. "
            f"Ya puedes iniciar sesión con {admin_email}."
        ),
    )


@router.get(f"{settings.api_prefix}/public/planes")
def listar_planes_publicos() -> list[dict]:
    """Lista los planes disponibles para mostrar en la página de registro."""
    from app.saas_master import list_planes
    planes = list_planes(solo_activos=True)
    # No exponer precios internos si fuera necesario — por ahora retorna todo
    return [
        {
            "id": p["id"],
            "nombre": p["nombre"],
            "descripcion": p["descripcion"],
            "precio_mensual": float(p["precio_mensual"]),
            "limite_sucursales": p["limite_sucursales"],
            "limite_tecnicos": p["limite_tecnicos"],
        }
        for p in planes
    ]
