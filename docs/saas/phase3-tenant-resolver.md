# Fase 3 - Endurecimiento del Tenant Resolver

Fecha de ejecucion: 2026-06-06

## Objetivo

Evitar que un JWT de tenant invalido, incompleto o inactivo termine usando la BD legacy
`diagramador` por fallback silencioso.

## Archivos ajustados

- `backend/app/main.py`
- `backend/app/utils.py`
- `backend/app/tenant_context.py`
- `backend/app/saas_master.py`

## Cambios aplicados

### 1. Contexto tenant consistente

`tenant_context.py` ahora conserva:

- engine actual del tenant
- metadata del tenant actual

### 2. Validacion dura de claims tenant

`utils.py` ahora invalida JWT de tenant si falta:

- `tenant_id`
- `tenant_slug`

Si llega un bearer token invalido a un endpoint con auth opcional,
ya no se ignora silenciosamente: responde `401`.

### 3. Middleware endurecido

`main.py` ahora:

- resuelve el tenant desde el JWT solo si el token tenant es valido
- distingue:
  - `TENANT_NO_ENCONTRADO`
  - `TENANT_TOKEN_MISMATCH`
  - `TENANT_INACTIVO`
- evita caer a `diagramador` cuando el JWT de tenant es incorrecto

### 4. Lookup de tenant por slug sin filtrar estado

`saas_master.py` agrega `get_tenant_by_slug_any()` para que el middleware
pueda diferenciar entre tenant inexistente e inactivo.

## Pruebas ejecutadas

### Compilacion backend

- `python3 -m compileall backend/app`
- Resultado: OK

### Casos reales validados

1. Token tenant valido:
   - `GET /api/sucursales`
   - Resultado: `200`

2. Token tenant incompleto, sin `tenant_slug`:
   - `GET /api/sucursales`
   - Resultado: `401`
   - Detalle: `TOKEN_TENANT_INVALIDO`

3. Token tenant con slug inexistente:
   - `GET /api/sucursales`
   - Resultado: `403`
   - Detalle: `TENANT_NO_ENCONTRADO`

4. Token tenant con tenant inactivo:
   - se desactivo temporalmente tenant `4`
   - `GET /api/sucursales`
   - Resultado: `403`
   - Detalle: `TENANT_INACTIVO`
   - luego se reactivo el tenant

## Criterio de pase a Fase 4

Se puede pasar a Fase 4 porque:

- el contexto tenant ya no depende de fallback silencioso
- un token tenant defectuoso ya no puede tocar la BD legacy por accidente
- el middleware diferencia causas reales de fallo de tenancy
