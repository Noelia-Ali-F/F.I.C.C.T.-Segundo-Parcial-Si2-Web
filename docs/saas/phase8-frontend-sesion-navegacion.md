# Fase 8 — Frontend Angular: sesión y navegación SaaS

Fecha: 2026-06-06

## Objetivo de este corte

Dar el primer paso útil de la adaptación Angular al modelo SaaS ya consolidado
en backend, enfocando en:

- sesión frontend con roles tenant centralizados
- navegación del dashboard por rol
- consumo autenticado de endpoints operativos desde el panel web

## Archivos modificados

- `frontend/src/app/auth/session.ts`
- `frontend/src/app/dashboard/dashboard-page.component.ts`

## Cambios aplicados

### 1. Sesión frontend alineada con SaaS

Se centralizaron los roles de empresa en `session.ts`:

- `SUPERADMIN_TENANT`
- `ADMIN_SUCURSAL`
- `TECNICO`
- `CLIENTE`

Además se agregaron helpers reutilizables para identificar:

- sesión tenant
- superadmin tenant
- admin de sucursal
- técnico

### 2. Navegación por rol en dashboard

El dashboard ahora usa reglas explícitas por tipo de sesión:

- `SUPERADMIN_TENANT`
  - ve operación del tenant y administración de empresa
- `ADMIN_SUCURSAL`
  - ve operación de su sucursal y vistas de solo lectura donde backend no le permite mutar
- `TECNICO`
  - ve solo panel operativo necesario

También se ocultaron acciones de frontend que backend rechaza por diseño:

- creación/edición/eliminación de sucursales para roles no superadmin
- creación/edición/eliminación de usuarios de empresa para roles no superadmin

### 3. Endpoints protegidos ahora salen con JWT

Se corrigió el principal riesgo del frontend SaaS:

- varias llamadas del dashboard usaban endpoints con autenticación opcional
- el frontend estaba consumiendo esas rutas sin `Authorization`
- eso podía degradar el alcance real de tenant/sucursal en la experiencia web

Se unificó el armado de requests autenticados para:

- dashboard overview
- talleres
- técnicos
- clientes
- emergencias y tracking
- cotizaciones
- servicios contratados
- resolución del contexto workshop legacy

## Validación ejecutada

Compilación real del frontend:

- `docker compose exec -T frontend npm run build` -> `OK`

## Resultado de este corte

- Fase 8: iniciada y validada en su primer bloque
- sesión y navegación base del dashboard: alineadas con SaaS
- consumo operativo protegido con JWT: corregido

## Siguiente subfase recomendada

Continuar con adaptación de pantallas legacy fuera del dashboard compartido,
priorizando:

1. servicios/componentes reutilizables que aún dependen solo de `workshop_id`
2. guards o redirecciones por rol si se agregan rutas separadas
3. pruebas funcionales reales con:
   - `SUPERADMIN_TENANT`
   - `ADMIN_SUCURSAL`
   - `TECNICO`
