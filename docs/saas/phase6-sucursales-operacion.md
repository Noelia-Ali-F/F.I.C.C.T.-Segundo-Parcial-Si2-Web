# Fase 6 — Propagación operativa de sucursales

Fecha: 2026-06-06

## Objetivo

Propagar `sucursal_id` al dominio operativo inmediato para que el alcance de
`ADMIN_SUCURSAL` ya no dependa solo del módulo de sucursales/usuarios, sino
también de:

- talleres
- técnicos
- dashboard operativo

## Archivos modificados

- `backend/app/db.py`
- `backend/app/routes/workshops.py`
- `backend/app/routes/technicians.py`
- `backend/app/routes/dashboard.py`

## Cambios aplicados

### 1. Persistencia

En `db.py` se reforzó el esquema operativo para soportar `sucursal_id` en:

- `workshop_registrations`
- `technicians`
- `emergency_reports`

También se agregaron:

- índices por `sucursal_id`
- propagación de `sucursal_id` desde taller hacia técnicos
- propagación de `sucursal_id` desde taller más cercano hacia emergencias

Además, las funciones multi-tenant ahora son adaptativas y funcionan tanto en:

- base legacy compartida con `tenant_id`
- base dedicada por tenant sin `tenant_id`

Funciones ajustadas:

- `list_workshops_by_tenant(...)`
- `list_technicians_by_tenant(...)`
- `list_clients_by_tenant(...)`
- `list_emergency_reports_by_tenant(...)`

### 2. Talleres

Se incorporó `sucursal_id` al contrato de talleres y se aplicó alcance por
sucursal cuando el usuario autenticado es `ADMIN_SUCURSAL`.

Comportamiento:

- `SUPERADMIN_TENANT` puede ver/crear talleres de varias sucursales
- `ADMIN_SUCURSAL` solo puede operar sobre su propia sucursal
- el endpoint público `GET /api/workshops` se mantiene compatible para el home/mapa

### 3. Técnicos

Se incorporó `sucursal_id` al contrato de técnicos y se aplicó alcance por
sucursal para `ADMIN_SUCURSAL`.

Comportamiento:

- si el técnico se crea con `workshop_id`, hereda la sucursal del taller
- `ADMIN_SUCURSAL` solo ve y administra técnicos de su sucursal
- consultar técnicos de otra sucursal por `workshop_id` devuelve `403`

### 4. Dashboard operativo

El dashboard operativo ya usa `sucursal_id` cuando el usuario autenticado es
`ADMIN_SUCURSAL`.

Comportamiento:

- `SUPERADMIN_TENANT` ve el tenant completo
- `ADMIN_SUCURSAL` ve solo talleres/técnicos de su sucursal
- si intenta consultar un `workshop_id` de otra sucursal, devuelve `403`

## Pruebas reales ejecutadas

Tenant de prueba:

- `tenant_id = 5`
- `tenant_slug = tenant_bootstrap_qa`

Usuarios:

- `SUPERADMIN_TENANT`
  - `admin.bootstrap.20260606@example.com`
- `ADMIN_SUCURSAL`
  - `admin.sucursal.qa@example.com`

### Evidencia principal

1. Login real:

- `POST /api/auth/login` `200` para ambos usuarios

2. Creación de taller en sucursal 2 por `SUPERADMIN_TENANT`:

- `POST /api/workshops` `201`
- taller creado:
  - `id = 2`
  - `sucursal_id = 2`

3. Creación de técnico en sucursal 1 por `ADMIN_SUCURSAL`:

- `POST /api/technicians` `201`
- técnico creado con:
  - `sucursal_id = 1`

4. Creación de técnico en sucursal 2 por `SUPERADMIN_TENANT`:

- `POST /api/technicians?workshop_id=2` `201`
- técnico creado con:
  - `sucursal_id = 2`

5. Listado de talleres con `ADMIN_SUCURSAL`:

- `GET /api/workshops` `200`
- solo devolvió la sucursal 1

6. Listado de talleres con `SUPERADMIN_TENANT`:

- `GET /api/workshops` `200`
- devolvió sucursal 1 y sucursal 2

7. Listado de técnicos con `ADMIN_SUCURSAL`:

- `GET /api/technicians` `200`
- solo devolvió técnicos de sucursal 1

8. Intento de consultar técnicos de taller de sucursal 2 con `ADMIN_SUCURSAL`:

- `GET /api/technicians?workshop_id=2` `403`
- detalle:
  - `ACCESO_DENEGADO_SUCURSAL`

9. Dashboard operativo con `ADMIN_SUCURSAL`:

- `GET /api/dashboard/operational-overview` `200`
- ranking visible solo con talleres de sucursal 1

## Riesgos y observaciones

- El `SUPERADMIN_TENANT` bootstrap todavía llega con `sucursal_id = 1` en el
  token por compatibilidad previa. Para evitar romper el tenant completo, el
  alcance por sucursal en esta fase se aplicó explícitamente solo a
  `ADMIN_SUCURSAL`.
- Aún falta propagar esta misma disciplina a más módulos operativos:
  emergencias, asignaciones, tracking, cotizaciones y reportes detallados.

## Resultado

- Fase 6: aprobada
- criterio de pase: cumplido

La base operativa inmediata ya respeta sucursales en talleres, técnicos y
dashboard para `ADMIN_SUCURSAL`, sin romper la visibilidad completa del
`SUPERADMIN_TENANT`.
