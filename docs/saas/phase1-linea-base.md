# Fase 1 - Linea Base SaaS

Fecha de ejecucion: 2026-06-06

## Objetivo

Congelar el estado actual del proyecto antes de continuar con la migracion SaaS multi-tenant.

## Respaldos generados

- `backups/phase1/diagramador_phase1.sql`
- `backups/phase1/saas_master_phase1.sql`

## Estado del entorno

- Backend Docker: arriba
- Frontend Docker: arriba
- PostgreSQL Docker: arriba y saludable

## Estado Git detectado

El repositorio ya estaba en estado hibrido y con cambios sin consolidar:

- cambios modificados en backend legacy
- nuevos archivos SaaS sin integrar del todo
- frontend Angular mezclando panel legacy y panel SaaS

## Bases de datos detectadas

- `diagramador`
- `saas_master`
- `tenant_auxilio_norte`
- `tenant_mecanicos_express`
- `tenant_taller_sur_premium`
- `tenant_taller_verificacion_test`

## Tablas reales detectadas

### Base `diagramador`

- `clients`
- `device_fcm_tokens`
- `emergency_assignments`
- `emergency_reports`
- `emergency_status_history`
- `emergency_tracking_points`
- `notifications`
- `quotation_offers`
- `quotation_request_history`
- `quotation_request_workshops`
- `quotation_requests`
- `technicians`
- `tenants`
- `vehicles`
- `workshop_registrations`

### Base `saas_master`

- `auditoria_saas`
- `planes`
- `saas_tenants`
- `suscripciones`

### Base tenant de muestra `tenant_auxilio_norte`

- `clients`
- `device_fcm_tokens`
- `emergency_assignments`
- `emergency_reports`
- `emergency_status_history`
- `emergency_tracking_points`
- `notifications`
- `quotation_offers`
- `quotation_request_workshops`
- `quotation_requests`
- `sucursales`
- `technicians`
- `usuarios_tenant`
- `vehicles`
- `workshop_registrations`

## Conteos reales relevantes

### Base `diagramador`

- `workshop_registrations`: 6
- `technicians`: 3
- `clients`: 1
- `emergency_reports`: 39
- `quotation_requests`: 24
- `quotation_offers`: 17
- `notifications`: 106

### Base `saas_master`

- `saas_tenants`: 4
- `planes`: 3
- `suscripciones`: 0
- `auditoria_saas`: 3

## Inventario rapido de endpoints backend

- `auth.py`: 3
- `clients.py`: 7
- `dashboard.py`: 1
- `devices.py`: 1
- `emergencies.py`: 11
- `health.py`: 2
- `public.py`: 2
- `quotations.py`: 12
- `saas.py`: 7
- `sucursales.py`: 5
- `technicians.py`: 4
- `tenants.py`: 8
- `usuarios_tenant.py`: 6
- `vehicles.py`: 4
- `workshops.py`: 7

## Hallazgos criticos de linea base

1. Coexisten dos modelos de tenancy:
   - modelo legacy con tabla `tenants` dentro de `diagramador`
   - modelo SaaS con `saas_master` y BD por tenant

2. `diagramador` sigue siendo la fuente principal de operacion real.

3. Ya existen tenants reales creados, pero la capa SaaS no esta cerrada:
   - hay `saas_tenants`
   - hay BDs tenant
   - no hay `suscripciones` operativas aun

4. El schema tenant y el schema operativo no estan completamente alineados.

5. No existe framework formal de migraciones.

6. No existe codigo Flutter en este repositorio, por lo que la fase movil no puede auditarse ni ejecutarse localmente desde aqui.

## Criterio de pase a Fase 2

Se puede pasar a Fase 2 porque ya existe:

- respaldo SQL del estado actual
- inventario de bases y tablas
- evidencia de tenants reales
- evidencia de mezcla legacy + SaaS

La prioridad de Fase 2 debe ser unificar la base maestra SaaS y definir una sola fuente de verdad para tenants.
