# Fase 15 - Routing de emergencias por especialidad y sucursal cercana

Fecha: 2026-06-07

## Regla de negocio

Cuando un cliente crea una emergencia con un problema como `Batería`, el
sistema debe resolver dos cosas al mismo tiempo:

1. difundir la emergencia a todas las sucursales del tenant que sí atienden
   esa especialidad
2. sugerir a la app móvil cuál de esas sucursales compatibles es la más
   cercana a la ubicación del cliente

## Ajuste aplicado sin romper compatibilidad

- Se mantiene `POST /api/emergencias` y sus campos históricos.
- Se agrega `GET /api/emergencias/routing-preview` para uso directo del móvil.
- Si el móvil no envía `nearest_workshop_id`, el backend intenta resolverlo
  automáticamente usando:
  - `problem_type`
  - `problem_type_standardized`
  - coordenadas del cliente
- La notificación `EMERGENCY_REGISTERED` deja de difundirse ciegamente a todo
  el tenant y ahora puede limitarse a las sucursales compatibles mediante
  `matching_sucursal_ids`.

## Contrato recomendado para móvil

### Paso 1

Llamar:

- `GET /api/emergencias/routing-preview`

Entradas:

- `problem_type`
- `latitude`
- `longitude`
- `description` opcional

Salidas clave:

- `nearest_workshop_id`
- `nearest_sucursal_id`
- `nearest_sucursal_nombre`
- `total_matching_sucursales`
- `candidates[]`

### Paso 2

Crear la emergencia con:

- `POST /api/emergencias`

Compatibilidad:

- si la app ya envía `nearest_workshop_id`, el backend lo respeta cuando es
  compatible
- si no lo envía, el backend selecciona el más cercano elegible

## Resultado esperado

- la app móvil puede mostrar una sugerencia clara y explicable
- la emergencia llega solo a sucursales capaces de atender ese problema
- no se rompe el flujo actual de clientes que ya envían `nearest_workshop_id`
