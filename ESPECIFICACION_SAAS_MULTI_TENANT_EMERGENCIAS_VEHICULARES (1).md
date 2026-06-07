# ESPECIFICACIÓN ARQUITECTÓNICA SAAS MULTI-TENANT
# Sistema de Emergencias Vehiculares

## 1. Objetivo general

Convertir el sistema actual de Emergencias Vehiculares en una plataforma **SaaS Multi-Tenant real**, permitiendo que múltiples talleres, empresas o redes de talleres utilicen la misma plataforma sin mezclar información.

La solución debe incluir:

- Arquitectura SaaS real.
- Base de datos independiente por tenant.
- Registro público de empresas/talleres.
- Creación automática de tenants.
- Creación automática de bases de datos.
- Gestión de sucursales.
- Gestión de administradores por sucursal.
- Gestión de técnicos.
- Tiempo real.
- Offline real.
- KPIs reales.
- Seguridad.
- Auditoría.
- Aislamiento completo entre tenants.

---

## 2. Regla principal de la ingeniera

No se aceptará funcionalidad decorativa.

Cada módulo debe afectar realmente al sistema:

### Tiempo real

- Debe actualizar estados reales.
- No debe simular cambios.
- Debe reflejar eventos reales del backend y base de datos.

### Offline

- Debe guardar datos reales.
- Debe sincronizar datos reales.
- Debe evitar duplicados.

### KPIs

- Deben calcularse desde PostgreSQL.
- No deben usar datos falsos, mock o números fijos.

### Multi-Tenant

- Debe aislar información real.
- Un tenant no debe ver datos de otro tenant.
- Una sucursal no debe ver datos de otra sucursal si el rol no tiene permiso.

---

## 3. Arquitectura general SaaS

El sistema funcionará como una plataforma SaaS.

Ejemplo:

- Tenant A: Auxilio Norte.
- Tenant B: Mecánicos Express.
- Tenant C: Red Sur.

Todos utilizan la misma plataforma, pero cada tenant posee:

- su propia base de datos;
- sus usuarios;
- sus técnicos;
- sus emergencias;
- sus pagos;
- sus cotizaciones;
- sus reportes;
- sus KPIs.

Los datos no deben mezclarse.

---

## 4. Arquitectura Database Per Tenant

Implementar arquitectura **Database Per Tenant**.

Debe existir una base maestra y una base independiente por cada tenant.

### Base maestra

```text
saas_master
```

### Bases de datos tenant

```text
tenant_auxilio_norte
tenant_mecanicos_express
tenant_red_sur
```

Ejemplo:

```text
Auxilio Norte
↓
tenant_auxilio_norte

Mecánicos Express
↓
tenant_mecanicos_express

Red Sur
↓
tenant_red_sur
```

No se debe crear una base de datos por cada usuario.

La base de datos se crea únicamente cuando una empresa, red o taller principal se registra.

Los usuarios internos, como administradores secundarios, técnicos o encargados de sucursal, pertenecen al tenant y trabajan dentro de la misma base de datos del tenant.

---

## 5. Base maestra SaaS

Base:

```text
saas_master
```

La base maestra administra únicamente la información global SaaS.

### Tabla: tenants

Campos sugeridos:

- id
- nombre
- slug
- razon_social
- nit
- correo
- telefono
- direccion_principal
- zona
- ciudad
- latitud
- longitud
- estado
- database_name
- database_host
- database_port
- database_user
- database_password
- plan_id
- fecha_creacion
- fecha_expiracion
- created_at
- updated_at

### Tabla: planes

Campos sugeridos:

- id
- nombre
- descripcion
- precio_mensual
- limite_sucursales
- limite_tecnicos
- limite_administradores
- estado
- created_at
- updated_at

### Tabla: suscripciones

Campos sugeridos:

- id
- tenant_id
- plan_id
- fecha_inicio
- fecha_fin
- estado
- monto
- metodo_pago
- created_at
- updated_at

### Tabla: auditoria_saas

Campos sugeridos:

- id
- tenant_id
- usuario_id
- accion
- descripcion
- ip
- fecha

La base maestra no debe almacenar datos operativos como emergencias, cotizaciones, técnicos, pagos o evidencias. Esos datos deben vivir dentro de la base de datos del tenant correspondiente.

---

## 6. Superadministrador global

Crear rol:

```text
SUPERADMIN_GLOBAL
```

Este rol representa a la persona o empresa dueña de toda la plataforma SaaS.

Puede ver y administrar todo el ecosistema.

### Permisos del SUPERADMIN_GLOBAL

Puede:

- Ver todos los tenants registrados.
- Ver todas las empresas o redes de talleres.
- Ver todas las sucursales de todos los tenants.
- Ver todos los usuarios.
- Ver todos los administradores.
- Ver todos los técnicos.
- Ver todas las emergencias.
- Ver todas las cotizaciones.
- Ver todos los pagos.
- Ver todas las comisiones.
- Ver todos los reportes.
- Ver todos los KPIs globales.
- Ver métricas agregadas de toda la plataforma.
- Crear tenants manualmente.
- Activar tenants.
- Suspender tenants.
- Desactivar tenants.
- Administrar planes SaaS.
- Administrar suscripciones.
- Administrar límites de uso.
- Acceder a panel de auditoría.
- Acceder a logs globales.
- Acceder a soporte técnico.

### Dashboard del SUPERADMIN_GLOBAL

Debe mostrar:

- Total de tenants.
- Tenants activos.
- Tenants suspendidos.
- Total de sucursales.
- Total de usuarios.
- Total de técnicos.
- Total de emergencias.
- Total de servicios completados.
- Total de pagos procesados.
- Total de ingresos de la plataforma.
- Total de comisiones generadas.
- Tenants más activos.
- Tenants con más emergencias.
- Tenants con más ingresos.

### Modo soporte: Entrar como Tenant

Debe existir un modo opcional:

```text
Entrar como Tenant
```

Este modo permite al SUPERADMIN_GLOBAL ingresar temporalmente a un tenant específico para soporte o diagnóstico.

Toda acción realizada en modo soporte debe quedar registrada en auditoría global.

El SUPERADMIN_GLOBAL puede visualizar información de todos los tenants, pero no debe participar directamente en la operación diaria de emergencias como operador común, salvo en modo soporte auditado.

---

## 7. Registro público de empresa o taller principal

Agregar desde la pantalla de login o desde una ruta pública:

```text
/registro-taller
/registrar-empresa
```

Este flujo permite que un dueño registre su empresa, red de talleres o taller principal.

### Datos de la empresa o red

Campos del formulario:

- nombre_empresa
- razon_social
- nit
- telefono
- correo
- direccion_principal
- zona
- ciudad
- latitud
- longitud
- descripcion
- servicios_ofrecidos

### Datos del dueño o superadministrador tenant

Campos del formulario:

- nombres
- apellidos
- correo
- telefono
- usuario
- contraseña
- confirmacion_contraseña

### Datos de sucursal principal

Campos del formulario:

- nombre_sucursal
- direccion_sucursal
- zona_sucursal
- ciudad_sucursal
- latitud_sucursal
- longitud_sucursal
- telefono_sucursal

### Flujo backend

Cuando se registra una empresa/taller principal, el backend debe:

1. Validar datos obligatorios.
2. Validar NIT único en `saas_master`.
3. Validar correo único del dueño.
4. Crear tenant en `saas_master`.
5. Generar slug único.
6. Crear base de datos PostgreSQL vacía para ese tenant.
7. Ejecutar migraciones en la nueva base de datos.
8. Crear taller/empresa principal dentro de la base de datos tenant.
9. Crear sucursal principal.
10. Crear usuario dueño con rol `SUPERADMIN_TENANT`.
11. Asociar dueño al tenant.
12. Asociar dueño a todas las sucursales del tenant.
13. Crear configuración inicial.
14. Redirigir al login o iniciar sesión.
15. Permitir ingreso al panel del dueño.

### Reglas de rollback

Si falla cualquier paso:

- Hacer rollback.
- No dejar tenant incompleto.
- No dejar base de datos huérfana.
- Registrar error en auditoría.

---

## 8. Jerarquía de roles

La jerarquía final debe ser:

```text
SUPERADMIN_GLOBAL
↓
SUPERADMIN_TENANT
↓
ADMIN_SUCURSAL
↓
TECNICO
↓
CLIENTE
```

---

## 9. SUPERADMIN_TENANT

Representa al dueño principal del taller, empresa o red de talleres.

Ejemplo:

```text
Tenant: Talleres Pérez
```

Sucursales:

```text
Sucursal Norte
Sucursal Sur
Sucursal Central
```

El `SUPERADMIN_TENANT` tiene acceso completo a todos los talleres y sucursales que pertenecen a su tenant.

### Puede ver

- Todas las sucursales.
- Todos los técnicos.
- Todas las emergencias.
- Todas las cotizaciones.
- Todos los pagos.
- Todas las comisiones.
- Todos los reportes.
- Todos los KPIs globales del tenant.

### Puede administrar

- Crear sucursales.
- Editar sucursales.
- Activar sucursales.
- Desactivar sucursales.
- Crear administradores de sucursal.
- Asignar administradores a sucursales.
- Crear técnicos.
- Asignar técnicos a sucursales.

El `SUPERADMIN_TENANT` sí puede ver toda la información de sus sucursales porque es el propietario del tenant.

---

## 10. Sucursales dentro del tenant

Cada tenant puede tener varias sucursales.

Ejemplo:

```text
Tenant: Auxilio Norte

Sucursales:
- Sucursal Norte
- Sucursal Sur
- Sucursal Central
```

### Tabla: sucursales

Esta tabla debe vivir dentro de cada base de datos tenant.

Campos sugeridos:

- id
- nombre
- direccion
- zona
- ciudad
- latitud
- longitud
- telefono
- estado
- created_at
- updated_at

### Reglas

- Un tenant puede tener varias sucursales.
- El `SUPERADMIN_TENANT` ve todas las sucursales.
- El `ADMIN_SUCURSAL` solo ve su sucursal asignada.
- Un técnico pertenece a una sucursal.
- Una emergencia atendida debe quedar asociada a una sucursal cuando corresponda.
- Una cotización debe quedar asociada a la sucursal que la emite.
- Un pago debe quedar asociado a la sucursal que atiende.
- Los KPIs pueden calcularse por tenant y por sucursal.

---

## 11. Administradores de sucursal

El dueño o `SUPERADMIN_TENANT` puede asignar administradores a diferentes sucursales.

Ejemplo:

```text
Juan Pérez → Administrador de Sucursal Norte
Adriana Lima → Administradora de Sucursal Sur
```

### Regla de acceso por sucursal

El administrador de Sucursal Norte solo puede ver información de Sucursal Norte.

El administrador de Sucursal Sur solo puede ver información de Sucursal Sur.

### ADMIN_SUCURSAL puede ver

- Su sucursal asignada.
- Técnicos de su sucursal.
- Emergencias de su sucursal.
- Cotizaciones de su sucursal.
- Pagos de su sucursal.
- Reportes de su sucursal.
- KPIs de su sucursal.

### ADMIN_SUCURSAL no puede ver

- Otras sucursales.
- Técnicos de otras sucursales.
- Emergencias de otras sucursales.
- Cotizaciones de otras sucursales.
- Pagos de otras sucursales.
- Reportes de otras sucursales.
- KPIs de otras sucursales.

Todo debe validarse obligatoriamente en backend mediante rol, tenant y sucursal.

No confiar únicamente en frontend.

---

## 12. Técnicos

Cada técnico pertenece a una sucursal.

### Técnico puede

- Ver emergencias asignadas.
- Cambiar estado a `EN_CAMINO`.
- Registrar llegada.
- Iniciar atención.
- Finalizar servicio.
- Subir evidencias.

### Técnico no puede

- Ver emergencias de otro tenant.
- Ver emergencias de otra sucursal si no están asignadas.
- Modificar datos administrativos.
- Ver KPIs globales.

---

## 13. Cliente

El cliente utiliza principalmente la aplicación móvil.

### Cliente puede

- Registrar emergencia.
- Registrar emergencia offline.
- Solicitar cotización.
- Ver cotizaciones recibidas.
- Seleccionar taller por cotización.
- Ver seguimiento del servicio.
- Realizar pagos.
- Calificar servicio.
- Recibir notificaciones.

El cliente no debe poder ver información de otros tenants.

---

## 14. Tenant Resolver

Implementar `Tenant Resolver` en backend.

### Proceso

```text
JWT
↓
Obtener tenant_id / tenant_slug
↓
Consultar saas_master
↓
Obtener connection string
↓
Conectar a base de datos tenant
↓
Ejecutar consulta
```

Nunca confiar en `tenant_id` enviado desde frontend.

El tenant debe resolverse desde JWT y `saas_master`.

---

## 15. JWT Multi-Tenant

El JWT debe incluir:

- user_id
- tenant_id
- tenant_slug
- rol
- sucursal_id
- exp

Ejemplo:

```json
{
  "user_id": 15,
  "tenant_id": 3,
  "tenant_slug": "auxilio_norte",
  "rol": "ADMIN_SUCURSAL",
  "sucursal_id": 2,
  "exp": 123456789
}
```

---

## 16. Login Multi-Tenant

El login debe soportar usuarios de tenants.

Puede resolver tenant por una de estas opciones según la arquitectura actual:

- subdominio;
- slug;
- correo del usuario;
- selector de empresa si es necesario.

### Flujo login

1. Identificar tenant.
2. Verificar que el tenant esté activo.
3. Conectar a la base de datos tenant.
4. Buscar usuario.
5. Validar contraseña.
6. Validar usuario activo.
7. Generar JWT con tenant, rol y sucursal.
8. Devolver perfil y permisos.

Si el tenant está inactivo:

- Bloquear login.
- Mostrar mensaje.

---

## 17. Connection Manager

Implementar `Connection Manager` por tenant.

Debe manejar:

- Cache de conexiones por tenant.
- Conexión a `saas_master`.
- Conexión a base tenant.
- Tenant inactivo.
- Base tenant no disponible.
- Cierre correcto de sesiones.
- Errores claros.

---

## 18. Aislamiento obligatorio

No permitir:

- Tenant A vea Tenant B.
- Tenant B modifique Tenant A.
- Admin Sucursal Norte vea Sucursal Sur.
- Admin Sucursal Sur vea Sucursal Norte.
- Técnico Norte vea emergencias Sur.
- Cliente vea cotizaciones de otro tenant.
- Taller cotice emergencia de otro tenant.

Validar siempre en backend:

- tenant correcto;
- sucursal correcta;
- rol correcto;
- permisos correctos.

No confiar en frontend.

---

## 19. Módulos afectados

Aplicar esta arquitectura a todos los módulos, no solo a los últimos casos de uso.

Módulos afectados:

- usuarios;
- roles;
- empresas/talleres;
- sucursales;
- técnicos;
- clientes;
- vehículos;
- emergencias;
- evidencias;
- solicitudes de cotización;
- cotizaciones;
- selección de taller;
- asignación técnico;
- seguimiento;
- llegada técnico;
- atención;
- pagos;
- comisiones;
- calificaciones;
- notificaciones;
- reportes;
- KPIs;
- dashboard;
- offline;
- tiempo real.

---

## 20. Flujo operativo con tenant y sucursal

### Registro de emergencia

- Cliente registra emergencia desde móvil.
- Backend resuelve tenant.
- Guarda emergencia en la base tenant correcta.
- Asocia sucursal/taller compatible si corresponde.

### Solicitar cotización

- Buscar solo talleres/sucursales del mismo tenant.
- No enviar a otros tenants.

### Registrar cotización

- Taller/sucursal registra cotización.
- Guardar en BD tenant correcta.
- Asociar a sucursal.

### Seleccionar taller por cotización

- Cliente selecciona cotización.
- Cotización seleccionada queda `ACEPTADA`.
- Demás cotizaciones quedan `RECHAZADAS`.
- Emergencia cambia a `TALLER_SELECCIONADO`.
- Taller/sucursal queda asociado.
- Se habilita asignación de técnico.

### Asignar técnico

- Técnico debe pertenecer al mismo tenant.
- Si el usuario es `ADMIN_SUCURSAL`, el técnico debe pertenecer a su sucursal.

### Registrar llegada

- Técnico debe estar asignado.
- Validar GPS.
- Actualizar estado.
- Registrar historial.

---

## 21. Tiempo real real

Implementar WebSocket real o corregirlo si existe.

### Eventos a emitir

- emergencia registrada;
- solicitud recibida;
- solicitud aceptada;
- solicitud rechazada;
- cotización enviada;
- cotización aceptada;
- taller seleccionado;
- técnico asignado;
- técnico en camino;
- técnico en sitio;
- servicio iniciado;
- servicio finalizado;
- pago registrado;
- notificación enviada.

### Reglas

Debe respetar:

- tenant;
- sucursal;
- rol.

No enviar eventos de Tenant A a Tenant B.

No enviar eventos de Sucursal Sur a Admin Norte.

---

## 22. Offline real en Flutter

Implementar o corregir modo offline real.

Debe permitir:

- registrar emergencia sin internet;
- guardar datos localmente;
- guardar ubicación GPS;
- guardar fotos;
- guardar audios;
- marcar estado `PENDIENTE_SINCRONIZACION`;
- cola de sincronización;
- reintentos automáticos;
- sincronizar al recuperar internet;
- evitar duplicados;
- cambiar estado a `SINCRONIZADO` cuando backend confirme.

### Sincronización

Al sincronizar:

- Backend resuelve tenant desde JWT.
- Guarda en base tenant correcta.
- No confiar en `tenant_id` enviado desde móvil.

---

## 23. KPIs reales

Calcular KPIs desde PostgreSQL real.

No usar mocks.

No usar números fijos.

### KPIs SUPERADMIN_GLOBAL

- total tenants;
- tenants activos;
- tenants suspendidos;
- total sucursales;
- total usuarios;
- total técnicos;
- total emergencias plataforma;
- total pagos plataforma;
- ingresos SaaS;
- tenants con más actividad.

### KPIs SUPERADMIN_TENANT

- total emergencias tenant;
- emergencias pendientes;
- emergencias atendidas;
- emergencias canceladas;
- tiempo promedio respuesta;
- tiempo promedio llegada técnico;
- servicios por sucursal;
- cotizaciones aceptadas;
- cotizaciones rechazadas;
- ingresos por pagos;
- comisiones generadas;
- calificación promedio.

### KPIs ADMIN_SUCURSAL

- emergencias de su sucursal;
- técnicos activos de su sucursal;
- servicios finalizados;
- ingresos por sucursal;
- tiempo promedio de atención.

---

## 24. Backend FastAPI

Implementar:

- conexión `saas_master`;
- modelos SaaS;
- Tenant Resolver;
- Connection Manager;
- creación de BD tenant;
- migraciones tenant;
- JWT multi-tenant;
- guards por rol;
- guards por sucursal;
- WebSocket multi-tenant;
- KPIs multi-tenant;
- offline sync multi-tenant.

### Endpoints públicos

```http
POST /auth/login
POST /public/registro-taller
```

### Endpoints SUPERADMIN_GLOBAL

```http
GET /saas/tenants
POST /saas/tenants
GET /saas/tenants/{id}
PATCH /saas/tenants/{id}/estado
GET /saas/planes
POST /saas/planes
GET /saas/dashboard
GET /saas/auditoria
```

### Endpoints TENANT

```http
GET /sucursales
POST /sucursales
PUT /sucursales/{id}
PATCH /sucursales/{id}/estado
```

### Endpoints USUARIOS

```http
POST /usuarios/admin-sucursal
POST /usuarios/tecnico
GET /usuarios
```

Mantener y adaptar endpoints existentes de:

- emergencias;
- cotizaciones;
- pagos;
- notificaciones;
- reportes;
- dashboard.

---

## 25. Angular Web

### Rutas públicas

- login;
- registrar empresa/taller.

### Módulo SUPERADMIN_GLOBAL

Debe incluir:

- dashboard global SaaS;
- listar tenants;
- ver detalle tenant;
- crear tenant;
- activar/desactivar tenant;
- administrar planes;
- administrar suscripciones;
- auditoría global;
- modo entrar como tenant.

### Módulo SUPERADMIN_TENANT

Debe incluir:

- dashboard tenant;
- gestión sucursales;
- crear sucursal;
- editar sucursal;
- activar/desactivar sucursal;
- gestión administradores;
- asignar administradores a sucursales;
- gestión técnicos;
- asignar técnicos a sucursales;
- reportes tenant;
- KPIs tenant.

### Módulo ADMIN_SUCURSAL

Debe incluir:

- dashboard sucursal;
- emergencias sucursal;
- cotizaciones sucursal;
- técnicos sucursal;
- pagos sucursal;
- KPIs sucursal.

### Reglas Angular

- Usar guards por rol.
- Usar guards por sucursal.
- No mostrar datos no autorizados.
- No enviar tenant_id como filtro confiable.
- Mantener diseño existente.
- No romper funcionalidades actuales.

---

## 26. Flutter móvil

Actualizar:

- login;
- JWT;
- registro emergencia;
- seguimiento;
- cotizaciones;
- selección taller;
- pagos;
- notificaciones;
- offline;
- sincronización.

Todo debe funcionar con tenant resuelto por backend.

El cliente no puede ver datos de otro tenant.

---

## 27. Errores a controlar

Implementar errores claros:

- TENANT_NO_ENCONTRADO
- TENANT_INACTIVO
- BASE_TENANT_NO_DISPONIBLE
- USUARIO_NO_EXISTE
- USUARIO_INACTIVO
- SUCURSAL_NO_AUTORIZADA
- ROL_NO_AUTORIZADO
- ACCESO_DENEGADO
- REGISTRO_NO_PERTENECE_AL_TENANT
- REGISTRO_NO_PERTENECE_A_SUCURSAL
- ERROR_CREANDO_BASE_TENANT
- ERROR_MIGRANDO_TENANT
- ERROR_SINCRONIZACION_OFFLINE

---

## 28. Migración de datos actuales

No perder datos existentes.

Crear:

- Tenant Principal.
- Base de datos `tenant_principal`.
- Superadmin tenant principal.

Migrar o asignar datos actuales al tenant principal.

Mantener compatibilidad con endpoints existentes.

---

## 29. Pruebas obligatorias

Crear o documentar pruebas:

1. Registrar empresa desde login.
2. Verificar creación de tenant.
3. Verificar creación de BD tenant.
4. Verificar creación de superadmin tenant.
5. Superadmin tenant crea sucursal norte.
6. Superadmin tenant crea sucursal sur.
7. Superadmin tenant crea admin norte.
8. Superadmin tenant crea admin sur.
9. Admin norte no ve sucursal sur.
10. Admin sur no ve sucursal norte.
11. Tenant Auxilio Norte no ve Mecánicos Express.
12. Taller Tenant A no cotiza emergencia Tenant B.
13. Técnico Tenant A no atiende emergencia Tenant B.
14. KPIs globales no mezclan tenants.
15. KPIs sucursal no mezclan sucursales.
16. Offline sincroniza a BD correcta.
17. WebSocket no cruza eventos entre tenants.
18. Notificaciones no cruzan tenants.
19. SUPERADMIN_GLOBAL ve todos los tenants.
20. SUPERADMIN_GLOBAL puede entrar en modo soporte y queda auditado.

---

## 30. Resultado esperado

Al finalizar, el sistema debe tener:

- SaaS Multi-Tenant real.
- Database Per Tenant.
- Base maestra SaaS.
- Registro público de empresa/taller.
- Creación automática de tenant.
- Creación automática de BD tenant.
- SUPERADMIN_GLOBAL dueño de plataforma.
- SUPERADMIN_TENANT dueño de empresa/taller.
- Sucursales.
- Administradores por sucursal.
- Técnicos por sucursal.
- Aislamiento entre tenants.
- Aislamiento entre sucursales.
- WebSocket real por tenant/sucursal.
- Offline real.
- KPIs reales.
- Flutter compatible.
- Angular compatible.
- FastAPI compatible.
- PostgreSQL compatible.

No entregar pseudocódigo.

Implementar código real.

No romper funcionalidades existentes.

Al terminar mostrar:

1. Plan aplicado.
2. Archivos creados.
3. Archivos modificados.
4. Migraciones creadas.
5. Endpoints nuevos.
6. Endpoints modificados.
7. Cómo probar.
8. Riesgos técnicos.
9. Comandos para ejecutar.
