# Fase 7 — Adaptación de endpoints backend operativos

Fecha: 2026-06-06

## Objetivo

Extender el modelo `tenant + sucursal` al dominio operativo backend, empezando por:

- emergencias
- tracking / cambios de estado / asignación de técnico
- cotizaciones por taller

Además, corregir la desalineación entre el schema tenant y el schema operativo
real que ya usaba la base legacy.

## Archivos modificados

- `backend/app/db.py`
- `backend/app/routes/emergencies.py`
- `backend/app/routes/quotations.py`
- `backend/app/tenant_schema.py`
- `backend/app/tenant_manager.py`

## Cambios aplicados

### 1. Emergencias

Se agregó control de alcance por sucursal para roles de operación local:

- `ADMIN_SUCURSAL`
- `TECNICO`

Reglas aplicadas:

- listado de emergencias filtrado por `tenant_id` y `sucursal_id`
- detalle de emergencia restringido por `sucursal_id`
- tracking restringido por `sucursal_id`
- asignación de técnico restringida por `sucursal_id`
- rechazo / cambio de estado / eliminación restringidos por `sucursal_id`

También se normalizó la persistencia:

- `emergency_reports` ahora inserta y devuelve `sucursal_id`
- la reasignación automática de taller actualiza también `sucursal_id`

### 2. Cotizaciones

Se aplicó validación de sucursal sobre endpoints específicos de taller:

- `GET /api/cotizaciones/taller/{workshop_id}`
- `GET /api/cotizaciones/taller/{workshop_id}/historial`
- `GET /api/cotizaciones/taller/{workshop_id}/servicios-contratados`
- `GET /api/cotizaciones/taller/{workshop_id}/servicios-contratados/{offer_id}`
- `POST /api/cotizaciones/{quotation_id}/propuestas`
- `PUT /api/cotizaciones/{quotation_id}/propuestas/{offer_id}`

Resultado:

- `ADMIN_SUCURSAL` y `TECNICO` ya no pueden consultar ni operar cotizaciones de talleres fuera de su sucursal
- `SUPERADMIN_TENANT` mantiene visibilidad de todo el tenant

### 3. Schema tenant

Se sincronizó `tenant_schema.py` con el estado real del backend para cotizaciones:

- `quotation_offers.status`
- `estimated_arrival_time`
- `warranty`
- `validity_days`
- `observations`
- `condiciones_servicio`
- `expires_at`
- tabla `quotation_request_history`
- índices y restricciones únicas de cotización

Además, `tenant_manager.get_tenant_engine(...)` ahora ejecuta:

- creación idempotente de tablas tenant
- upgrades ligeros del schema tenant al primer uso

Eso evita que un tenant nuevo o viejo quede funcional solo “a medias”.

## Pruebas reales ejecutadas

Tenant de prueba:

- `tenant_id = 5`
- `tenant_slug = tenant_bootstrap_qa`

Usuarios:

- `SUPERADMIN_TENANT`
  - `admin.bootstrap.20260606@example.com`
- `ADMIN_SUCURSAL`
  - `admin.sucursal.qa@example.com`

Datos sembrados para validar alcance:

- emergencia `id = 1`, `sucursal_id = 1`
- emergencia `id = 2`, `sucursal_id = 2`
- taller `id = 2`, `sucursal_id = 2`

### Evidencia real

1. `ADMIN_SUCURSAL` listando emergencias:

- `GET /api/emergencias` -> `200`
- solo devolvió emergencias de sucursal `1`

2. `SUPERADMIN_TENANT` listando emergencias:

- `GET /api/emergencias` -> `200`
- devolvió emergencias de sucursal `1` y `2`

3. `ADMIN_SUCURSAL` consultando detalle de emergencia de sucursal 2:

- `GET /api/emergencias/2` -> `403`
- detalle: `ACCESO_DENEGADO_SUCURSAL`

4. `ADMIN_SUCURSAL` consultando tracking de emergencia de sucursal 2:

- `GET /api/emergencias/2/tracking` -> `403`

5. `ADMIN_SUCURSAL` intentando asignar técnico en taller de sucursal 2:

- `PUT /api/emergencias/2/technician-assignment?workshop_id=2` -> `403`

6. `SUPERADMIN_TENANT` consultando detalle de emergencia de sucursal 2:

- `GET /api/emergencias/2` -> `200`
- `sucursal_id = 2`

7. `ADMIN_SUCURSAL` consultando cotizaciones del taller de sucursal 2:

- `GET /api/cotizaciones/taller/2` -> `403`

8. `SUPERADMIN_TENANT` consultando cotizaciones del taller de sucursal 2:

- `GET /api/cotizaciones/taller/2` -> `200`

9. `ADMIN_SUCURSAL` consultando servicios contratados del taller de sucursal 2:

- `GET /api/cotizaciones/taller/2/servicios-contratados` -> `403`

## Hallazgo corregido durante la fase

Durante la prueba apareció una falla real:

- el tenant bootstrap no tenía el schema de cotizaciones actualizado
- eso provocaba error SQL en `quotation_offers.status`

Se corrigió unificando `tenant_schema.py` con el estado real del backend y
aplicando upgrades ligeros al primer uso del engine tenant.

## Resultado

- Fase 7: aprobada
- criterio de pase: cumplido

El backend operativo ya respeta `tenant + sucursal` en emergencias y
cotizaciones de taller, y el schema tenant quedó alineado con la evolución
real del sistema.
