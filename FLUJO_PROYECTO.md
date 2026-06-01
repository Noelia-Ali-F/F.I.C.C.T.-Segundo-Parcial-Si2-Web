# Flujo Del Proyecto

Este documento resume el flujo principal del sistema web y su relacion con la app movil. Sirve como guia rapida para entender que hace cada parte importante del proyecto.

## 1. Ejecucion General

El proyecto se ejecuta con Docker Compose y tiene tres servicios:

- `frontend`: aplicacion Angular disponible en `http://localhost:5656`.
- `backend`: API FastAPI disponible en `http://localhost:8787`.
- `db`: PostgreSQL usado por el backend.

El archivo principal de orquestacion es `docker-compose.yml`.

Flujo de arranque:

1. PostgreSQL inicia y espera estar saludable.
2. Backend inicia despues de la base de datos.
3. Backend ejecuta la inicializacion de tablas y columnas necesarias.
4. Frontend inicia y consume la API del backend.

## 2. Roles Del Sistema

El sistema maneja tres tipos principales de usuario:

- Administrador: usuario protegido del sistema.
- Socio de taller: taller aprobado por el administrador.
- Cliente movil: usuario registrado desde la app movil.

### Administrador

El administrador es una cuenta virtual configurada por variables de entorno:

- `PROTECTED_ADMIN_EMAIL`
- `PROTECTED_ADMIN_PASSWORD`
- `PROTECTED_ADMIN_FULL_NAME`
- `PROTECTED_ADMIN_PHONE`

No se guarda en la tabla `clients`. Su autenticacion se resuelve directamente en `POST /api/auth/login`.

### Socio De Taller

El socio de taller nace desde el registro de talleres. El administrador puede aprobarlo. Cuando queda activo, puede iniciar sesion en el panel web.

En el dashboard, el socio solo puede ver:

- Tecnicos
- Emergencias
- Reportes

El administrador puede ver todas las secciones.

### Cliente Movil

El cliente movil se registra en PostgreSQL y puede enviar emergencias desde la app movil. Sus datos se usan para relacionar vehiculos, emergencias y notificaciones.

## 3. Login Y Seguridad De Intentos

El login web usa `POST /api/auth/login`.

El frontend envia:

- `email`
- `password`
- `account_type`

Valores de `account_type`:

- `admin`
- `workshop`

El backend maneja 3 intentos fallidos por separado para administrador y socio de taller. Esto evita que los intentos fallidos de un perfil afecten al otro.

Regla actual:

- Maximo: 3 intentos.
- Bloqueo temporal: 10 minutos.
- Un login correcto reinicia el contador de ese tipo de cuenta.

## 4. Flujo De Talleres

El flujo de talleres empieza cuando un taller se registra desde el formulario web.

1. Se crea un registro con estado `pendiente`.
2. El administrador revisa la solicitud.
3. El administrador puede aprobar o rechazar.
4. Al aprobar, el taller queda como `activo`.
5. El taller puede iniciar sesion como socio.

Los talleres activos pueden gestionar tecnicos y atender emergencias asignadas a su taller.

## 5. Flujo De Tecnicos

Los tecnicos pertenecen a un taller.

Estados principales:

- `disponible`
- `ocupado`
- `fuera_de_servicio`

Cuando un tecnico es asignado a una emergencia, el backend lo marca como `ocupado`.

## 6. Flujo De Emergencias Desde La App Movil

La app movil envia emergencias al backend con:

`POST /api/emergencias`

El envio usa `multipart/form-data` porque puede incluir:

- Datos del cliente y vehiculo.
- Tipo de problema.
- Ubicacion.
- Fotos.
- Audio.
- Precio estimado.

Campos importantes:

- `client_id`
- `vehicle_name`
- `vehicle_plate`
- `problem_type`
- `price`
- `description`
- `latitude`
- `longitude`
- `nearest_workshop_id`
- `photos`
- `audio`

Cuando llega una emergencia:

1. El backend valida datos basicos.
2. Guarda fotos y audio en `backend/uploads/emergencias`.
3. Normaliza placa y tipo de problema.
4. Determina `problem_type_standardized` si corresponde.
5. Calcula o conserva `price`.
6. Guarda la emergencia en PostgreSQL.
7. Devuelve la emergencia creada.

## 7. Clasificacion De Problemas

Los tipos permitidos son:

- `Bateria`
- `Neumatico`
- `Combustible`
- `Motor`
- `Sistema electrico`
- `Accidente`
- `Cerrajeria / llaves`
- `Otro`

Si el movil envia `problem_type=Otro`, el backend intenta clasificar el problema usando:

- `description`
- transcripcion del audio, si Whisper esta activo
- clasificacion visual de fotos, si esta activada

Ejemplo:

Si llega:

```text
problem_type=Otro
description=no quiere encender el auto
```

El backend puede guardar:

```json
{
  "problem_type": "Otro",
  "problem_type_standardized": "Bateria",
  "price": 50
}
```

Si la descripcion no tiene pistas reales, por ejemplo `Segunda prueba tipo Otro`, el backend no puede saber el problema y deja:

```json
{
  "problem_type_standardized": null,
  "price": null
}
```

## 8. Precios Base De Emergencias

El backend usa precios base cuando el movil no envia `price` y se puede determinar el problema.

Precios actuales:

- `Bateria`: 50
- `Neumatico`: 50
- `Combustible`: 60
- `Motor`: 100
- `Sistema electrico`: 90
- `Accidente`: 150
- `Cerrajeria / llaves`: 80

Si el movil envia `price`, ese valor se respeta.

En las vistas del sistema, el precio se divide de forma operativa:

- `Servicio`: 10% del precio.
- `Monto`: 90% del precio para el trabajo del taller.

Ejemplo: si el precio base es 100, el sistema muestra `Servicio=10` y `Monto=90`.

## 9. Estados De Emergencias

Las emergencias usan estos estados:

- `pendiente`: creada, todavia no aceptada.
- `activo`: aceptada por un taller.
- `rechazado`: rechazada.

Flujo normal:

1. La app movil crea la emergencia como `pendiente`.
2. El taller ve las emergencias asignadas a su `nearest_workshop_id`.
3. El taller acepta la emergencia.
4. La emergencia pasa a `activo`.
5. El taller puede asignar un tecnico.
6. El cliente puede recibir notificacion push si FCM esta activo.

## 10. Notificaciones Push

El backend puede enviar push con Firebase Cloud Messaging si:

- `FCM_ENABLED=true`
- `FIREBASE_CREDENTIALS_PATH` apunta al JSON correcto.

Eventos implementados:

- `emergency_accepted`
- `technician_assigned`

Mientras no exista rastreo real del tecnico, la ubicacion enviada en la notificacion usa las coordenadas registradas del taller.

## 11. Dashboard Web

El dashboard esta implementado principalmente en:

`frontend/src/app/pages/dashboard-page.component.ts`

Secciones principales:

- Dashboard general.
- Talleres.
- Tecnicos.
- Clientes.
- Emergencias.
- Reportes.
- Bitacora.

Restricciones por rol:

- Administrador: puede ver todas las secciones.
- Socio de taller: solo ve Tecnicos, Emergencias y Reportes.

## 12. Emergencias En Dashboard

La seccion de emergencias permite:

- Listar solicitudes.
- Filtrar por estado.
- Ver mapa, fotos y audio.
- Aceptar o rechazar emergencias.
- Asignar tecnico disponible.
- Ver historial de emergencias no pendientes.

Filtros disponibles:

- Todas
- Pendiente
- Activa
- Rechazado
- Historial

Para socios de taller, el frontend carga emergencias filtradas por `nearest_workshop_id`.

## 13. Reportes

La seccion Reportes muestra trabajos realizados por el socio/taller.

Datos mostrados:

- Taller.
- Cantidad de trabajos.
- Total por servicio.
- Total por monto neto.
- Fecha de generacion.
- Cliente.
- Vehiculo.
- Problema.
- Tecnico.
- Estado.
- Servicio.
- Monto.

La exportacion PDF se realiza desde el navegador usando impresion. Durante la impresion se oculta el encabezado del dashboard y solo se imprime el reporte.

## 14. Bitacora

La bitacora muestra una linea de tiempo con eventos recientes.

Incluye:

- Emergencias registradas.
- Emergencias aceptadas.
- Emergencias rechazadas.
- Tecnicos disponibles, ocupados o fuera de servicio.
- Para administrador tambien incluye talleres y clientes.

La bitacora se arma desde datos ya disponibles del dashboard, sin crear una tabla adicional por ahora.

## 15. Base De Datos Principal

Tablas importantes:

- `clients`: clientes moviles.
- `workshop_registrations`: talleres/socios.
- `technicians`: tecnicos por taller.
- `vehicles`: vehiculos de clientes.
- `emergency_reports`: emergencias creadas por la app movil.
- `emergency_assignments`: asignacion de tecnico a emergencia.
- `device_fcm_tokens`: tokens de dispositivos moviles.

La inicializacion y migraciones simples estan en:

`backend/app/db.py`

## 16. Archivos Clave

- `docker-compose.yml`: servicios del proyecto.
- `backend/app/main.py`: endpoints FastAPI y logica principal.
- `backend/app/db.py`: SQL, tablas y consultas.
- `backend/app/config.py`: configuracion por entorno.
- `backend/API.md`: documentacion de endpoints.
- `frontend/src/app/pages/login-page.component.ts`: login web.
- `frontend/src/app/pages/dashboard-page.component.ts`: dashboard principal.
- `frontend/src/app/pages/shared-pages.css`: estilos principales.
- `frontend/src/app/session.ts`: sesion local del frontend.

## 17. Consideraciones Importantes

- El proyecto esta pensado para ejecutarse en Docker.
- Los uploads se guardan localmente en `backend/uploads`.
- Los registros antiguos pueden tener `price=null` si no existia precio al momento de creacion o si no se pudo clasificar el problema.
- El calculo automatico de precio para `Otro` depende de que exista una pista real en la descripcion, audio o imagen.
- El rol del usuario define que menus ve en el dashboard.
- El administrador protegido no vive en base de datos.
