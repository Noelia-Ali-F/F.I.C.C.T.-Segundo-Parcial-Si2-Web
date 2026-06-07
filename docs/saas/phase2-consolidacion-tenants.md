# Fase 2 - Consolidacion de tenants en saas_master

Fecha de ejecucion: 2026-06-06

## Objetivo

Convertir `/api/tenants` en una capa de compatibilidad que lea desde `saas_master`
en lugar de la tabla legacy `tenants` de `diagramador`.

## Cambio aplicado

Se reemplazo la implementacion de:

- `backend/app/routes/tenants.py`

Nuevo comportamiento:

- `GET /api/tenants` lista tenants desde `saas_master`
- `GET /api/tenants/{id}` obtiene tenant desde `saas_master`
- `GET /api/tenants/{id}/kpis` consulta la BD propia del tenant
- `GET /api/tenants/{id}/workshops` consulta la BD propia del tenant
- `PUT /api/tenants/{id}` actualiza metadata en `saas_master`
- `PATCH /api/tenants/{id}/estado` cambia estado en `saas_master`
- `DELETE /api/tenants/{id}` ahora actua como baja logica y marca `inactivo`

## Compatibilidad preservada

Se mantuvo la ruta `/api/tenants` porque el dashboard Angular actual todavia la consume.

## Pruebas ejecutadas

### Compilacion backend

- `python3 -m compileall backend/app`
- Resultado: OK

### Endpoints validados

- `GET /api/tenants` -> 200
- `GET /api/tenants/1` -> 200
- `GET /api/tenants/2/kpis` -> 200
- `GET /api/tenants/2/workshops` -> 200
- `PATCH /api/tenants/4/estado?estado=inactivo` -> 200
- `PATCH /api/tenants/4/estado?estado=activo` -> 200

## Evidencia funcional

`GET /api/tenants` ahora devolvio 4 tenants reales de `saas_master`,
mientras que la tabla legacy `diagramador.public.tenants` tenia solo 3 registros.

Eso confirma que la fuente de verdad de la ruta dejo de ser el modelo legacy.

## Riesgos que siguen abiertos

1. La tabla legacy `diagramador.public.tenants` sigue existiendo.
2. `db.py` todavia conserva funciones multi-tenant antiguas mezcladas con el modelo nuevo.
3. El dashboard Angular aun usa `/api/tenants` en vez de `/api/saas/tenants`.
4. La creacion manual desde `/api/tenants` sigue siendo basica y no reemplaza el flujo completo de registro publico.

## Criterio de pase a Fase 3

Se puede pasar a Fase 3 porque:

- `saas_master` ya gobierna la lectura y estado de tenants en runtime
- `/api/tenants` ya no depende de la tabla legacy para listar u obtener tenants
- los KPIs y talleres por tenant ya se resuelven sobre la BD propia del tenant
