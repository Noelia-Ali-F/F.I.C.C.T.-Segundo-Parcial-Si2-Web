# Fase 14 - Reset controlado y seed SaaS limpio

Fecha de auditoria: 2026-06-07 UTC

## 1. Resumen actual

### saas_master

- Bases detectadas: `diagramador`, `saas_master`, `tenant_auxilio_norte`, `tenant_mecanicos_express`, `tenant_qa_integral_1780805933`, `tenant_smoke_demo_a_1780794036`, `tenant_smoke_demo_b_1780794036`, `tenant_smoke_tenant_1780768874`, `tenant_taller_sur_premium`, `tenant_taller_verificacion_test`, `tenant_tenant_bootstrap_qa`.
- `planes`: 3
- `saas_tenants`: 9
- `suscripciones`: 5
- `auditoria_saas`: 8
- `device_fcm_tokens`: 8

Tenants registrados en `saas_master`:

| id | slug | nombre | estado | plan | DB |
| --- | --- | --- | --- | --- | --- |
| 1 | `mecanicos_express` | Mecánicos Express | activo | Estándar | `tenant_mecanicos_express` |
| 2 | `auxilio_norte` | Auxilio Norte | activo | Básico | `tenant_auxilio_norte` |
| 3 | `taller_sur_premium` | Taller Sur Premium | activo | Premium | `tenant_taller_sur_premium` |
| 4 | `taller_verificacion_test` | Taller Verificación Test | activo | Básico | `tenant_taller_verificacion_test` |
| 5 | `tenant_bootstrap_qa` | Tenant Bootstrap QA | activo | Básico | `tenant_tenant_bootstrap_qa` |
| 8 | `smoke_tenant_1780768874` | Smoke Tenant 1780768874 | activo | sin plan | `tenant_smoke_tenant_1780768874` |
| 9 | `smoke_demo_a_1780794036` | Smoke Demo A 1780794036 | activo | Básico | `tenant_smoke_demo_a_1780794036` |
| 10 | `smoke_demo_b_1780794036` | Smoke Demo B 1780794036 | activo | Básico | `tenant_smoke_demo_b_1780794036` |
| 11 | `qa_integral_1780805933` | QA Integral 1780805933 | activo | Básico | `tenant_qa_integral_1780805933` |

Tokens FCM globales:

- 3 activos sin `tenant_slug` asociado.
- `smoke_demo_a_1780794036`: 3 tokens, todos inactivos.
- `smoke_demo_b_1780794036`: 2 tokens activos.

### Tenant final A actual: `tenant_auxilio_norte`

- `sucursales`: 1
- `usuarios_tenant`: 1
- `workshop_registrations`: 2
- `technicians`: 2
- `clients`: 2
- `vehicles`: 0
- `emergency_reports`: 0
- `quotation_requests`: 0
- Estado actual:
  - Solo existe `Carlos Mamani` como `SUPERADMIN_TENANT`.
  - Hay dos talleres y dos tecnicos, pero ambos colgados de una sola sucursal.
  - No hay datos utiles para KPIs, WebSocket ni cotizaciones.
  - El plan actual es `Basico`, pero el objetivo final exige 2 sucursales; eso es inconsistente con el limite configurado del plan.

### Tenant final B actual: `tenant_mecanicos_express`

- `sucursales`: 2
- `usuarios_tenant`: 1
- `workshop_registrations`: 4
- `technicians`: 4
- `clients`: 4
- `vehicles`: 0
- `emergency_reports`: 8
- `emergency_assignments`: 4
- `emergency_status_history`: 14
- `emergency_tracking_points`: 6
- `notifications`: 7
- `quotation_*`: 0
- Estado actual:
  - Mezcla datos utiles recientes con registros heredados de prueba.
  - Tiene actividad apta para WebSocket y tracking.
  - No tiene seed limpio ni roles finales completos.
  - Tiene 2 sucursales, cuando el objetivo final pide solo `Sucursal Central`.

### Tenants smoke / QA / test

Resumen operativo:

| slug | tipo | sucursales | usuarios_tenant | clientes | emergencias | cotizaciones |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `smoke_demo_a_1780794036` | smoke | 2 | 7 | 2 | 2 | 1 request / 1 offer |
| `smoke_demo_b_1780794036` | smoke | 1 | 3 | 1 | 1 | 0 |
| `smoke_tenant_1780768874` | smoke | 2 | 3 | 0 | 0 | 0 |
| `tenant_bootstrap_qa` | qa | 2 | 3 | 0 | 2 | 0 |
| `qa_integral_1780805933` | qa | 2 | 4 | 0 | 0 | 0 |
| `taller_verificacion_test` | test | 1 | 2 | 0 | 0 | 0 |
| `taller_sur_premium` | demo | 1 | 1 | 0 | 0 | 0 |

Observacion:

- `smoke_demo_a_1780794036` es un buen referente funcional porque ya demuestra ramas, roles, emergencias y cotizacion aceptada.
- El resto es mayormente ruido operativo para pruebas finales.

### BD legacy `diagramador`

- `tenants`: 3
- `workshop_registrations`: 6
- `technicians`: 3
- `clients`: 5
- `vehicles`: 2
- `emergency_reports`: 40
- `emergency_assignments`: 5
- `emergency_status_history`: 109
- `device_fcm_tokens`: 21
- `notifications`: 108
- `quotation_requests`: 24
- `quotation_request_workshops`: 101
- `quotation_offers`: 17
- `quotation_request_history`: 37

Riesgos detectados en `diagramador`:

- Sigue conteniendo datos single-tenant legacy y ruido de smoke.
- Los estados de emergencia usan el set historico del sistema: `pendiente`, `activo`, `en_revision`, `auxilio_asignado`, `auxilio_en_camino`, `servicio_en_proceso`, `servicio_finalizado`, `solicitud_cancelada`.
- No es una buena base para pruebas finales SaaS multi-tenant; debe dejarse fuera del reset SaaS para no romper compatibilidad retro.

## 2. Que se recomienda conservar

- Tabla `planes` completa en `saas_master`.
- Estructura de todas las tablas existentes.
- Credenciales de `SUPERADMIN_GLOBAL` definidas por configuracion:
  - correo: `administrador@acb.com`
  - password actual: `123ppp+++`
- Metadata y esquema de los tenants finales:
  - `auxilio_norte`
  - `mecanicos_express`
- BD legacy `diagramador` como referencia y respaldo historico, sin usarla para seed final SaaS.

## 3. Que se recomienda limpiar o archivar

- Tokens FCM globales y tenant-aware de pruebas.
- Datos operativos completos dentro de:
  - `tenant_auxilio_norte`
  - `tenant_mecanicos_express`
- Tenants smoke / QA / test en `saas_master`:
  - recomendacion: archivarlos con `estado = inactivo` y cerrar sus suscripciones activas.
- Tenants smoke / QA / test a revisar para posible purge posterior:
  - `smoke_tenant_1780768874`
  - `smoke_demo_a_1780794036`
  - `smoke_demo_b_1780794036`
  - `tenant_bootstrap_qa`
  - `qa_integral_1780805933`
  - `taller_verificacion_test`
  - `taller_sur_premium`

## 4. Que NO se debe borrar

- `planes`
- Estructura de tablas
- `saas_master` como catalogo global
- Configuracion de conexion de los tenants finales
- Credenciales protegidas del admin global
- Backups existentes en `backups/phase1`
- BD `diagramador` y sus tablas, al menos en esta fase

## 5. Estrategia recomendada

### Opcion recomendada: A, con archivo seguro

Recomendacion final:

1. Hacer backup completo de `saas_master`, `diagramador` y todas las BD tenant.
2. Archivar tenants smoke / QA / test en `saas_master` en lugar de hacer `DROP DATABASE`.
3. Limpiar solo datos operativos de `auxilio_norte` y `mecanicos_express`.
4. Re-sembrar esos dos tenants con seed final limpio y coherente.
5. No tocar `diagramador` en esta fase.

Por que esta opcion es la mas segura:

- Evita `DROP` de bases o tablas.
- Mantiene trazabilidad en `saas_master`.
- Reduce el riesgo de romper codigo legacy.
- Deja solo 2 tenants activos, exactamente los que se necesitan para pruebas finales.
- Permite rollback sencillo restaurando backups y reactivando tenants archivados.

### Opcion B

- Crear tenants nuevos finales y dejar el ruido actual.
- No recomendable porque ya existen `auxilio_norte` y `mecanicos_express`, y duplicarlos complica slugs, pruebas y UI.

### Opcion C

- Reset operativo completo con seed controlado.
- No recomendable aun porque elevaria mucho el riesgo sobre `diagramador` y sobre tenants no auditados manualmente.

## 6. Riesgos

- `Auxilio Norte` hoy esta en plan `Basico`; con 2 sucursales finales debe migrarse a `Estandar`.
- Hay mezcla entre usuarios de login tenant (`usuarios_tenant`) y usuarios operativos (`clients`, `technicians`, `workshop_registrations`). El seed final debe poblar ambas capas.
- Los estados de negocio solicitados por QA deben mapearse a los estados reales del backend actual:
  - `pendiente` -> `pendiente`
  - `buscando taller` -> `activo`
  - `taller asignado` -> `auxilio_asignado`
  - `en camino` -> `auxilio_en_camino`
  - `en atencion` -> `servicio_en_proceso`
  - `finalizado` -> `servicio_finalizado`
  - `cancelado` -> `solicitud_cancelada`
- Si despues se decide purgar fisicamente tenants smoke, eso debe hacerse solo luego del backup y con confirmacion aparte.

## 7. Scripts preparados

- Auditoria: [scripts/phase14_audit.py](/home/alexanderaav03/F.I.C.C.T.-Primer-Parcial-Si2-Web/scripts/phase14_audit.py)
- Utilidades comunes: [scripts/phase14_common.py](/home/alexanderaav03/F.I.C.C.T.-Primer-Parcial-Si2-Web/scripts/phase14_common.py)
- Reset controlado: [scripts/phase14_reset_controlled.py](/home/alexanderaav03/F.I.C.C.T.-Primer-Parcial-Si2-Web/scripts/phase14_reset_controlled.py)
- Seed final: [scripts/phase14_seed_final.py](/home/alexanderaav03/F.I.C.C.T.-Primer-Parcial-Si2-Web/scripts/phase14_seed_final.py)
- Backup: [scripts/phase14_backup.sh](/home/alexanderaav03/F.I.C.C.T.-Primer-Parcial-Si2-Web/scripts/phase14_backup.sh)

Comportamiento de seguridad:

- `phase14_reset_controlled.py` y `phase14_seed_final.py` no hacen cambios sin `--apply`.
- El reset:
  - limpia FCM tokens globales
  - archiva tenants no finales en `saas_master`
  - limpia solo datos operativos de los tenants finales
  - no toca `diagramador`
- El seed:
  - puebla `auxilio_norte` y `mecanicos_express`
  - crea sucursales, usuarios, clientes, vehiculos, talleres, tecnicos, emergencias, tracking, notificaciones y cotizaciones
  - deja datos suficientes para KPIs y WebSocket

## 8. Comandos de backup

### Comando unico

```bash
bash scripts/phase14_backup.sh
```

### Prerrequisito para reset y seed

Los scripts Python de Fase 14 usan `psycopg`.

Ejecucion soportada actualmente:

```bash
python3 -m pip install -r backend/requirements.txt
```

Nota:

- El contenedor `backend` actual no monta el directorio `scripts/`, por lo que `docker compose exec -T backend python scripts/...` no funciona sin ajustar antes la configuracion de montaje.

### Comandos individuales

```bash
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d saas_master -f backups/phase14/saas_master_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d diagramador -f backups/phase14/diagramador_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_auxilio_norte -f backups/phase14/tenant_auxilio_norte_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_mecanicos_express -f backups/phase14/tenant_mecanicos_express_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_qa_integral_1780805933 -f backups/phase14/tenant_qa_integral_1780805933_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_smoke_demo_a_1780794036 -f backups/phase14/tenant_smoke_demo_a_1780794036_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_smoke_demo_b_1780794036 -f backups/phase14/tenant_smoke_demo_b_1780794036_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_smoke_tenant_1780768874 -f backups/phase14/tenant_smoke_tenant_1780768874_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_taller_sur_premium -f backups/phase14/tenant_taller_sur_premium_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_taller_verificacion_test -f backups/phase14/tenant_taller_verificacion_test_$(date -u +%Y%m%dT%H%M%SZ).sql
PGPASSWORD=diagramador pg_dump -h 127.0.0.1 -p 5432 -U diagramador -d tenant_tenant_bootstrap_qa -f backups/phase14/tenant_tenant_bootstrap_qa_$(date -u +%Y%m%dT%H%M%SZ).sql
```

## 9. Credenciales que dejara el seed final

### SUPERADMIN_GLOBAL

- correo: `administrador@acb.com`
- password actual: `123ppp+++`
- alcance: vision global de la plataforma SaaS
- origen: configuracion protegida del backend, no registro sembrado por `phase14_seed_final.py`

### Auxilio Norte

Password comun para usuarios tenant: `AuxilioNorte#2026`
Password comun para clientes: `ClienteAuxilio#2026`

| rol | tenant | sucursal | correo | password | visibilidad esperada |
| --- | --- | --- | --- | --- | --- |
| `SUPERADMIN_TENANT` | Auxilio Norte | todas | `superadmin@auxilionorte.com` | `AuxilioNorte#2026` | todo el tenant |
| `ADMIN_SUCURSAL` | Auxilio Norte | Norte | `admin.norte@auxilionorte.com` | `AuxilioNorte#2026` | solo Norte |
| `ADMIN_SUCURSAL` | Auxilio Norte | Sur | `admin.sur@auxilionorte.com` | `AuxilioNorte#2026` | solo Sur |
| `TECNICO` | Auxilio Norte | Norte | `tecnico.norte@auxilionorte.com` | `AuxilioNorte#2026` | solo casos asignados a Norte |
| `TECNICO` | Auxilio Norte | Sur | `tecnico.sur@auxilionorte.com` | `AuxilioNorte#2026` | solo casos asignados a Sur |
| `CLIENTE` | Auxilio Norte | n/a | `cliente.a@auxilionorte.com` | `ClienteAuxilio#2026` | solo sus emergencias y cotizaciones |
| `CLIENTE` | Auxilio Norte | n/a | `cliente.b@auxilionorte.com` | `ClienteAuxilio#2026` | solo sus emergencias y cotizaciones |

### Mecanicos Express

Password comun para usuarios tenant: `MecanicosExpress#2026`
Password comun para clientes: `ClienteExpress#2026`

| rol | tenant | sucursal | correo | password | visibilidad esperada |
| --- | --- | --- | --- | --- | --- |
| `SUPERADMIN_TENANT` | Mecanicos Express | todas | `superadmin@mecanicosexpress.com` | `MecanicosExpress#2026` | todo el tenant |
| `ADMIN_SUCURSAL` | Mecanicos Express | Central | `admin.central@mecanicosexpress.com` | `MecanicosExpress#2026` | solo Central |
| `TECNICO` | Mecanicos Express | Central | `tecnico.central@mecanicosexpress.com` | `MecanicosExpress#2026` | solo asignadas |
| `CLIENTE` | Mecanicos Express | n/a | `cliente@mecanicosexpress.com` | `ClienteExpress#2026` | solo sus datos |

## 10. Validacion prevista despues del seed

Checklist propuesta:

1. Login `SUPERADMIN_GLOBAL`
2. Login `SUPERADMIN_TENANT`
3. Login `ADMIN_SUCURSAL`
4. Login `TECNICO`
5. Login `CLIENTE`
6. `Tenant A` no ve `Tenant B`
7. Norte no ve Sur
8. Cliente A no ve Cliente B
9. Tecnico solo ve asignadas
10. Cotizaciones funcionan
11. KPIs muestran datos reales
12. WebSocket emite `emergency_status_updated`, `technician_assigned` y `tracking_location_updated`
13. `python3 -m compileall backend/app`
14. `docker compose exec -T frontend npm run build`
15. `curl http://127.0.0.1:8787/api/health`

## 11. Confirmacion requerida antes de ejecutar

No se ejecutara ningun reset ni seed hasta recibir confirmacion explicita.

Secuencia recomendada cuando se autorice:

```bash
bash scripts/phase14_backup.sh
python3 scripts/phase14_reset_controlled.py --apply
python3 scripts/phase14_seed_final.py --apply
```
