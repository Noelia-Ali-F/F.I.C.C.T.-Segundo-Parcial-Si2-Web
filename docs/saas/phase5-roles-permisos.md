# Fase 5 - Roles y permisos

Fecha de ejecucion: 2026-06-06

## Objetivo

Cerrar las fugas mas claras de permisos por sucursal y endurecer reglas basicas
de roles para usuarios tenant.

## Archivos ajustados

- `backend/app/routes/sucursales.py`
- `backend/app/routes/usuarios_tenant.py`

## Cambios aplicados

### Sucursales

Se restringio el acceso para `ADMIN_SUCURSAL`:

- `GET /api/sucursales`
  - ahora solo devuelve su propia sucursal
- `GET /api/sucursales/{id}`
  - ahora devuelve `403 ACCESO_DENEGADO_SUCURSAL` si intenta consultar otra sucursal

### Usuarios del tenant

Se agregaron validaciones de alcance y consistencia:

- `GET /api/tenant/usuarios/{id}`
  - `ADMIN_SUCURSAL` no puede leer usuarios de otra sucursal
- `POST /api/tenant/usuarios`
  - `ADMIN_SUCURSAL` y `TECNICO` requieren `sucursal_id`
  - `SUPERADMIN_TENANT` no puede crearse con `sucursal_id`
  - se valida que la sucursal exista y esté activa
- `PUT /api/tenant/usuarios/{id}`
  - valida coherencia de rol y sucursal objetivo
- `POST /api/tenant/usuarios/{id}/change-password`
  - respeta alcance de sucursal cuando corresponde
- `DELETE /api/tenant/usuarios/{id}`
  - bloquea auto-eliminacion del propio `SUPERADMIN_TENANT`

## Pruebas reales ejecutadas

Se uso el tenant creado en Fase 4:

- tenant: `Tenant Bootstrap QA`
- tenant_id: `5`

### Datos de prueba creados

- sucursal 2: `Sucursal Sur QA`
- usuario `ADMIN_SUCURSAL` en sucursal 1
- usuario `TECNICO` en sucursal 2

### Casos validados

1. `ADMIN_SUCURSAL` lista sucursales:
   - `GET /api/sucursales`
   - resultado: `200`
   - devolvio solo la sucursal `1`

2. `ADMIN_SUCURSAL` consulta su sucursal:
   - `GET /api/sucursales/1`
   - resultado: `200`

3. `ADMIN_SUCURSAL` consulta otra sucursal:
   - `GET /api/sucursales/2`
   - resultado: `403`
   - detalle: `ACCESO_DENEGADO_SUCURSAL`

4. `ADMIN_SUCURSAL` consulta su propio usuario:
   - `GET /api/tenant/usuarios/2`
   - resultado: `200`

5. `ADMIN_SUCURSAL` consulta usuario de otra sucursal:
   - `GET /api/tenant/usuarios/3`
   - resultado: `403`
   - detalle: `ACCESO_DENEGADO_SUCURSAL`

6. Crear `ADMIN_SUCURSAL` sin sucursal:
   - resultado: `400`
   - detalle: `El rol ADMIN_SUCURSAL requiere sucursal_id`

7. Crear `SUPERADMIN_TENANT` con sucursal:
   - resultado: `400`
   - detalle: `SUPERADMIN_TENANT no debe estar asignado a una sucursal`

8. Auto eliminar el propio `SUPERADMIN_TENANT`:
   - resultado: `409`
   - detalle: `No puedes eliminar tu propio usuario SUPERADMIN_TENANT`

## Resultado

La separacion minima por sucursal ya es real en rutas SaaS clave.

## Riesgos abiertos

1. El resto de endpoints de negocio aun no aplica sucursal en forma transversal:
   - emergencias
   - dashboard
   - clientes
   - tecnicos legacy
   - cotizaciones

2. Angular todavia mezcla vistas legacy y SaaS en un dashboard monolitico.

## Criterio de pase a Fase 6

Se puede pasar a Fase 6 porque:

- `ADMIN_SUCURSAL` ya no puede navegar libremente fuera de su sucursal en rutas SaaS base
- la consistencia minima entre rol y `sucursal_id` ya se valida en backend
