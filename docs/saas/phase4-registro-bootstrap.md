# Fase 4 - Registro publico con bootstrap operativo

Fecha de ejecucion: 2026-06-06

## Objetivo

Completar el alta publica de empresa/taller para que el tenant nazca operativo:

- tenant en `saas_master`
- base de datos tenant
- schema tenant
- sucursal principal
- `SUPERADMIN_TENANT`
- taller principal
- suscripcion inicial

## Archivos ajustados

- `backend/app/routes/public.py`
- `backend/app/saas_master.py`
- `backend/app/tenant_manager.py`

## Cambios aplicados

### Registro publico

`POST /api/public/registro-taller` ahora:

1. crea la BD del tenant
2. registra el tenant en `saas_master`
3. inicializa el schema tenant
4. crea una sucursal principal
5. crea el `SUPERADMIN_TENANT`
6. crea un taller principal inicial
7. crea una suscripcion inicial en `saas_master`
8. devuelve `sucursal_principal_id` y `workshop_principal_id`

### Rollback basico

Si falla el bootstrap luego de crear la BD o el tenant:

- intenta borrar el tenant en `saas_master`
- intenta eliminar la BD tenant creada

### Helpers nuevos

En `saas_master.py`:

- `create_subscription(...)`
- `delete_saas_tenant(...)`

En `tenant_manager.py`:

- `drop_tenant_database(...)`

## Prueba real ejecutada

Se registro un tenant de prueba:

- nombre: `Tenant Bootstrap QA`
- tenant_id: `5`
- slug: `tenant_bootstrap_qa`
- database_name: `tenant_tenant_bootstrap_qa`

### Respuesta HTTP real

`POST /api/public/registro-taller` -> `201`

Incluyo:

- `tenant_id = 5`
- `sucursal_principal_id = 1`
- `workshop_principal_id = 1`

### Verificacion en `saas_master`

Se confirmo:

- `saas_tenants.id = 5`
- `plan_id = 1`
- `estado = activo`
- una fila en `suscripciones` con:
  - `tenant_id = 5`
  - `plan_id = 1`
  - `estado = activo`
  - `metodo_pago = registro_inicial`

### Verificacion en BD tenant

En `tenant_tenant_bootstrap_qa` se confirmo:

- 1 sucursal principal
- 1 usuario `SUPERADMIN_TENANT` con `sucursal_id = 1`
- 1 taller principal con:
  - `approval_status = activo`
  - `availability_status = disponible`

### Verificacion de login

`POST /api/auth/login` con el admin nuevo -> `200`

El JWT devuelto incluyo:

- `tenant_id = 5`
- `tenant_slug = tenant_bootstrap_qa`
- `sucursal_id = 1`

## Riesgos abiertos

1. El taller principal se crea con `specialty = General`, que sirve como bootstrap pero no reemplaza la configuracion operativa final.
2. El rollback es de mejor esfuerzo; no se forzo una falla controlada para probarlo.
3. Aun no se crea un conjunto inicial de tecnicos ni configuraciones avanzadas del tenant.

## Criterio de pase a Fase 5

Se puede pasar a Fase 5 porque:

- el tenant ya nace operativo
- ya existe sucursal principal real
- ya existe usuario dueño reutilizable por login
- ya existe taller base para comenzar la configuracion del tenant
