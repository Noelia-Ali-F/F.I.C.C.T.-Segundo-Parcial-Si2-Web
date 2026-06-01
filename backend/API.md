# Backend API

Documentacion breve de los endpoints disponibles en el backend FastAPI.

## Base URL

- Desarrollo con Docker Compose: `http://localhost:8000`
- En red local: `http://192.168.0.50:8000` o `http://192.168.26.4:8000`

Nota:

- El backend de este proyecto corre dentro de Docker.
- El host `db` de PostgreSQL esta pensado para resolverse desde la red interna de Docker Compose.

## Endpoints

### `GET /`

Endpoint basico para comprobar que el backend esta levantado.

Respuesta esperada:

```json
{
  "message": "Backend running"
}
```

Ejemplo:

```bash
curl http://localhost:8000/
```

### `GET /api/health`

Verifica el estado general del backend y la conexion con PostgreSQL.

Respuesta esperada:

```json
{
  "status": "ok",
  "environment": "development",
  "database": "connected"
}
```

Campo `database`:

- `connected`: la base de datos responde correctamente
- `unavailable`: el backend esta arriba, pero PostgreSQL no responde

Ejemplo:

```bash
curl http://localhost:8000/api/health
```

### `POST /api/devices/fcm-token`

Registra o actualiza el token FCM de un dispositivo movil.

#### Body JSON

```json
{
  "user_id": 3,
  "fcm_token": "token_del_dispositivo",
  "platform": "android"
}
```

Valores permitidos para `platform`:

- `android`
- `ios`
- `web`

#### Comportamiento

- Crea el token si no existe.
- Si el mismo token ya existe, actualiza `user_id`, `platform`, `updated_at` y lo marca como activo.
- Permite mas de un dispositivo por usuario porque la unicidad esta en `fcm_token`.
- Requiere que `user_id` exista en clientes.

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "user_id": 3,
  "fcm_token": "token_del_dispositivo",
  "platform": "android",
  "is_active": true,
  "created_at": "2026-04-25T01:25:00.000000Z",
  "updated_at": "2026-04-25T01:25:00.000000Z"
}
```

#### Push enviados por backend

El backend envia notificaciones FCM si `FCM_ENABLED=true` y `FIREBASE_CREDENTIALS_PATH` apunta al JSON de service account de Firebase.

Eventos implementados:

- `emergency_accepted`: cuando un taller acepta una emergencia.
- `technician_assigned`: cuando un taller asigna o cambia el tecnico de una emergencia.

Payload para emergencia aceptada:

```json
{
  "notification": {
    "title": "Emergencia aceptada",
    "body": "DiegoRepair acepto tu emergencia: Bateria descargada"
  },
  "data": {
    "type": "emergency_accepted",
    "emergency_id": "45",
    "workshop_id": "11",
    "workshop_name": "DiegoRepair",
    "incident_description": "Bateria descargada"
  }
}
```

Payload para tecnico asignado:

```json
{
  "notification": {
    "title": "Tecnico asignado",
    "body": "Lucia Cuellar de DiegoRepair atendera: Bateria descargada"
  },
  "data": {
    "type": "technician_assigned",
    "emergency_id": "45",
    "workshop_id": "11",
    "technician_id": "40",
    "workshop_name": "DiegoRepair",
    "technician_name": "Lucia Cuellar",
    "incident_description": "Bateria descargada",
    "technician_latitude": "-17.7700",
    "technician_longitude": "-63.1700"
  }
}

```

Nota: mientras no exista tracking real del tecnico, `technician_latitude` y `technician_longitude` usan la ubicacion registrada del taller.

### `POST /api/clientes`

Registra un cliente desde la app movil despues de la validacion OTP.

#### Body JSON

```json
{
  "identityCard": "12345678",
  "fullName": "Juan Perez Gomez",
  "email": "juan@example.com",
  "phone": "71234567",
  "password": "ClaveSegura123",
  "confirmPassword": "ClaveSegura123",
  "acceptedTerms": true,
  "role": "client"
}
```

#### Claves aceptadas

El backend acepta tanto nombres en camelCase como en snake_case para facilitar compatibilidad con el telefono:

- `identityCard`, `identity_card`, `ci`
- `fullName`, `full_name`, `name`
- `phone`, `telefono`
- `confirmPassword`, `confirm_password`
- `acceptedTerms`, `accepted_terms`, `termsAccepted`

#### Validaciones

- `identity_card`: entre 5 y 40 caracteres
- `full_name`: entre 3 y 160 caracteres
- `email`: debe ser un correo valido
- `phone`: entre 7 y 40 caracteres
- `password`: minimo 6 caracteres
- `confirm_password`: si se envia, debe coincidir con `password`
- `accepted_terms`: debe ser `true`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "identity_card": "12345678",
  "full_name": "Juan Perez Gomez",
  "email": "juan@example.com",
  "phone": "71234567",
  "role": "client",
  "accepted_terms": true,
  "created_at": "2026-04-11T20:45:00.000000Z",
  "updated_at": "2026-04-11T20:45:00.000000Z"
}
```

#### Errores posibles

- `409 Conflict`: ya existe un cliente con ese carnet o correo
- `422 Unprocessable Entity`: datos invalidos o terminos no aceptados

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "identityCard": "12345678",
    "fullName": "Juan Perez Gomez",
    "email": "juan@example.com",
    "phone": "71234567",
    "password": "ClaveSegura123",
    "confirmPassword": "ClaveSegura123",
    "acceptedTerms": true,
    "role": "client"
  }'
```

### `GET /api/clientes`

Lista los clientes registrados.

Ejemplo:

```bash
curl http://localhost:8000/api/clientes
```

### `PUT /api/clientes/{client_id}/status`

Actualiza el estado de un cliente desde el panel administrativo.

#### Body JSON

```json
{
  "status": "suspended"
}
```

Valores permitidos:

- `active`
- `suspended`

Ejemplo:

```bash
curl -X PUT http://localhost:8000/api/clientes/4/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }'
```

### `PUT /api/clientes/{client_id}`

Actualiza los datos administrativos de un cliente.

#### Body JSON

```json
{
  "identity_card": "7700476",
  "full_name": "Jhasmany Fernandez",
  "email": "jhasmany@gmail.com",
  "phone": "72992000",
  "password": "NuevaClave123",
  "role": "client",
  "status": "active",
  "accepted_terms": true
}
```

El campo `password` es opcional en esta edición. Si se envía, el backend actualiza la contraseña del cliente; si se omite o va vacío, conserva la actual.

### `DELETE /api/clientes/{client_id}`

Elimina un cliente por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8000/api/clientes/4
```

### `POST /api/auth/login`

Autentica un cliente registrado desde la app movil.

Tambien autentica al administrador web del sistema con estas credenciales:

- `email`: `administrador@acb.com`
- `password`: `123ppp+++`

Importante:

- El administrador es un usuario virtual del sistema.
- No se guarda en la tabla `clients`.
- Si el correo es `administrador@acb.com`, el backend valida ese acceso fuera del CRUD normal de clientes.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "password": "claveSegura123"
}
```

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "id": 4,
  "email": "jhasmany@gmail.com",
  "full_name": "Jhasmany Fernandez",
  "phone": "72992000",
  "role": "client",
  "status": "active",
  "access_token": "token_generado_por_el_backend",
  "token_type": "bearer"
}
```

#### Errores posibles

- `401 Unauthorized`: `{"detail":"Correo o contraseña incorrectos"}`
- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "password": "claveSegura123"
  }'
```

### `POST /api/auth/account-type`

Permite consultar si un correo pertenece a una cuenta registrada y de qué tipo es.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com"
}
```

#### Respuesta cuando existe

```json
{
  "exists": true,
  "role": "workshop"
}
```

o

```json
{
  "exists": true,
  "role": "client"
}
```

#### Respuesta cuando no existe

```json
{
  "exists": false,
  "role": null
}
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/auth/account-type \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com"
  }'
```

### `POST /api/auth/forgot-password`

Permite restablecer la contraseña con una sola ruta para clientes y talleres.

El backend decide internamente si el correo pertenece a un cliente o a un taller.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Respuesta exitosa

Cliente:

```json
{
  "message": "La contraseña del cliente fue restablecida correctamente"
}
```

Taller:

```json
{
  "message": "La contraseña del taller fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: cuenta suspendida o taller no habilitado
- `404 Not Found`: `{"detail":"No existe una cuenta con ese correo"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/clientes/change-password`

Permite que un cliente cambie su propia contraseña usando su correo y su contraseña actual.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "currentPassword": "claveActual123",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `currentPassword`, `current_password`
- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un cliente registrado
- `current_password`: debe coincidir con la contraseña actual del cliente
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- La nueva contraseña debe ser distinta a la actual
- La cuenta del cliente debe estar en estado `active`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del cliente fue actualizada correctamente"
}
```

#### Errores posibles

- `401 Unauthorized`: `{"detail":"La contraseña actual es incorrecta"}`
- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`
- `404 Not Found`: `{"detail":"Cliente no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/clientes/change-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "currentPassword": "claveActual123",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/clientes/forgot-password`

Permite restablecer la contraseña de un cliente usando solamente su correo y una nueva contraseña.

Importante:

- Este es un flujo simple de recuperacion.
- No pide la contraseña actual.
- No usa token de recuperacion ni envio de correo.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un cliente registrado
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- La cuenta del cliente debe estar en estado `active`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del cliente fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`
- `404 Not Found`: `{"detail":"Cliente no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/clientes/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/workshops/forgot-password`

Permite restablecer la contraseña de un taller usando solamente su correo y una nueva contraseña.

Importante:

- Este es un flujo simple de recuperacion.
- No pide la contraseña actual.
- No usa token de recuperacion ni envio de correo.

#### Body JSON

```json
{
  "email": "taller@correo.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un taller registrado
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- El taller debe estar en estado `activo`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del taller fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: `{"detail":"El taller todavía no fue habilitado por el administrador"}`
- `404 Not Found`: `{"detail":"Taller no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/workshops/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "taller@correo.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/workshops`

### `POST /api/emergencias`

Registra una solicitud de emergencia enviada desde la app movil usando `multipart/form-data`.

#### Campos `form-data`

- `client_id`: opcional, entero mayor a 0
- `vehicle_name`: nombre mostrado del vehiculo
- `vehicle_plate`: placa del vehiculo
- `problem_type`: tipo de problema o emergencia
- `price`: opcional, precio estimado del servicio. Si no llega y el backend puede clasificar el problema, se completa con el precio base
- `problem_type_standardized`: calculado por backend a partir de `problem_type` y `description`; no es necesario enviarlo
- `photo_problem_type_standardized`: calculado por backend desde las fotos cuando la clasificacion visual esta activada
- `photo_classification_confidence`: confianza numerica de la clasificacion visual, entre `0.0` y `1.0`
- `photo_classification_error`: detalle del error si la clasificacion visual falla o no esta configurada
- `description`: opcional, descripcion detallada
- `latitude`: opcional
- `longitude`: opcional
- `address`: opcional
- `zone`: opcional
- `nearest_workshop_id`: opcional, entero mayor a 0
- `nearest_workshop_name`: opcional
- `nearest_workshop_specialty`: opcional
- `nearest_workshop_zone`: opcional
- `nearest_workshop_distance_meters`: opcional
- `audio_duration_seconds`: opcional
- `photos`: opcional, archivo repetido 0..n veces
- `audio`: opcional, archivo unico

#### Valores permitidos para `problem_type`

- `Batería`
- `Neumático`
- `Combustible`
- `Motor`
- `Sistema eléctrico`
- `Accidente`
- `Cerrajería / llaves`
- `Otro`

Si `problem_type` es `Otro`, el cliente movil puede complementar el detalle en `description`.
En ese caso, el backend intenta clasificarlo automaticamente a una de las 7 categorias estandarizadas y la guarda en `problem_type_standardized`.
Si hay fotos y la clasificacion visual esta activada, el backend tambien intenta inferir `photo_problem_type_standardized` y usa esa sugerencia como apoyo cuando el texto no alcanza para decidir.

#### Precios estimados enviados por movil

- `Batería`: `50`
- `Neumático`: `50`
- `Combustible`: `60`
- `Motor`: `100`
- `Sistema eléctrico`: `90`
- `Accidente`: `150`
- `Cerrajería / llaves`: `80`

Para `Otro`, `price` puede no enviarse. Si el backend logra clasificarlo en `problem_type_standardized`, guardara el precio base de esa categoria; si no logra clasificarlo, devolvera `price: null` y queda como servicio a cotizar.

#### Nombres de campos aceptados para archivos

- Fotos: `photos`
- Audio: `audio`

#### Tipos de archivo aceptados

- Fotos: `jpg`, `jpeg`, `png`, `webp`
- Audio: `aac`, `m4a`, `mp3`, `wav`, `ogg`, `webm`

#### Limites actuales

- Fotos: maximo `6` archivos por solicitud
- Tamano maximo por foto: `20 MB`
- Audio: maximo `1` archivo
- Tamano maximo del audio: `40 MB`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "client_id": 4,
  "vehicle_name": "Toyota Corolla",
  "vehicle_plate": "1234ABC",
  "problem_type": "Neumático",
  "price": 50,
  "problem_type_standardized": "Neumático",
  "photo_problem_type_standardized": "Neumático",
  "photo_classification_confidence": 0.93,
  "photo_classification_error": null,
  "description": "La llanta delantera se vacio en plena avenida",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "address": "Av. Banzer y 4to anillo",
  "zone": "Norte",
  "nearest_workshop_id": 14,
  "nearest_workshop_name": "MecaApp",
  "nearest_workshop_specialty": "Electricidad automotriz",
  "nearest_workshop_zone": "Centro",
  "nearest_workshop_distance_meters": 482.37,
  "audio_duration_seconds": 12.4,
  "audio_transcript": "se me pinchó la llanta en el camino",
  "audio_transcript_status": "completed",
  "audio_transcript_error": null,
  "photo_paths": [
    "emergencias/photos/archivo1.jpg"
  ],
  "photo_urls": [
    "/uploads/emergencias/photos/archivo1.jpg"
  ],
  "audio_path": "emergencias/audio/audio1.m4a",
  "audio_url": "/uploads/emergencias/audio/audio1.m4a",
  "created_at": "2026-04-12T12:00:00.000000Z"
}
```

#### Errores posibles

- `400 Bad Request`: archivo de foto o audio invalido
- `404 Not Found`: `client_id` no existe
- `422 Unprocessable Entity`: `problem_type` invalido
- `503 Service Unavailable`: base de datos no disponible

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/emergencias \
  -F "client_id=4" \
  -F "vehicle_name=Toyota Corolla" \
  -F "vehicle_plate=1234ABC" \
  -F "problem_type=Sistema eléctrico" \
  -F "price=90" \
  -F "description=El auto no enciende y las luces del tablero parpadean" \
  -F "latitude=-17.7833" \
  -F "longitude=-63.1821" \
  -F "address=Av. Banzer y 4to anillo" \
  -F "zone=Norte" \
  -F "nearest_workshop_id=14" \
  -F "nearest_workshop_name=MecaApp" \
  -F "nearest_workshop_specialty=Electricidad automotriz" \
  -F "nearest_workshop_zone=Centro" \
  -F "nearest_workshop_distance_meters=482.37" \
  -F "audio_duration_seconds=12.4" \
  -F "photos=@foto1.jpg" \
  -F "photos=@foto2.jpg" \
  -F "audio=@nota.m4a"
```

Ejemplo con clasificacion automatica desde `Otro`:

```bash
curl -X POST http://localhost:8000/api/emergencias \
  -F "client_id=4" \
  -F "vehicle_name=Suzuki Swift" \
  -F "vehicle_plate=5678XYZ" \
  -F "problem_type=Otro" \
  -F "description=Las llaves quedaron dentro del vehiculo" \
  -F "address=Av. Banzer" \
  -F "zone=Norte"
```

En ese caso, el backend conserva `problem_type=Otro` y normalmente guarda `problem_type_standardized=Cerrajería / llaves`.

Activacion de clasificacion visual:

- `PHOTO_CLASSIFICATION_ENABLED=true`
- `PHOTO_CLASSIFICATION_MODEL=gpt-5-mini`
- `OPENAI_API_KEY=<tu_api_key>`

Si `PHOTO_CLASSIFICATION_ENABLED=false` o no existe `OPENAI_API_KEY`, la emergencia igual se registra y `photo_problem_type_standardized` queda vacio.

Registra un taller mecanico desde el formulario principal del frontend.

#### Body JSON

```json
{
  "workshop_name": "Taller Demo",
  "contact_name": "Noelia Demo",
  "phone": "77712345",
  "email": "demo@example.com",
  "zone": "Centro",
  "specialty": "Auxilio mecánico",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "timezone": "America/La_Paz",
  "utc_offset_minutes": -240
}
```

#### Campos

- `workshop_name`: nombre del taller
- `contact_name`: nombre del responsable
- `phone`: telefono de contacto
- `email`: correo valido
- `zone`: zona o direccion referencial del taller
- `specialty`: especialidad principal
- `latitude`: latitud del punto en el mapa, opcional
- `longitude`: longitud del punto en el mapa, opcional
- `timezone`: zona horaria IANA, opcional
- `utc_offset_minutes`: diferencia respecto a UTC en minutos, opcional

#### Validaciones

- `workshop_name`: entre 3 y 160 caracteres
- `contact_name`: entre 3 y 160 caracteres
- `phone`: entre 7 y 40 caracteres
- `email`: debe ser un correo valido
- `zone`: entre 2 y 120 caracteres
- `specialty`: entre 2 y 120 caracteres
- `latitude`: entre `-90` y `90`
- `longitude`: entre `-180` y `180`
- `timezone`: entre 2 y 120 caracteres
- `utc_offset_minutes`: entre `-840` y `840`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "workshop_name": "Taller Demo",
  "contact_name": "Noelia Demo",
  "phone": "77712345",
  "email": "demo@example.com",
  "zone": "Centro",
  "specialty": "Auxilio mecánico",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "timezone": "America/La_Paz",
  "utc_offset_minutes": -240,
  "created_at": "2026-04-09T05:35:45.417342Z"
}
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "workshop_name": "Taller Demo",
    "contact_name": "Noelia Demo",
    "phone": "77712345",
    "email": "demo@example.com",
    "zone": "Centro",
    "specialty": "Auxilio mecánico",
    "latitude": -17.7833,
    "longitude": -63.1821,
    "timezone": "America/La_Paz",
    "utc_offset_minutes": -240
  }'
```

### `GET /api/workshops`

Lista todos los talleres registrados en orden descendente de creacion.

Ejemplo:

```bash
curl http://localhost:8000/api/workshops
```

### `PUT /api/workshops/{workshop_id}`

Actualiza el registro de un taller existente usando la misma estructura JSON de creacion.

Opcionalmente tambien puede recibir `password` para reemplazar la contraseña actual del taller.

Ejemplo:

```bash
curl -X PUT http://localhost:8000/api/workshops/1 \
  -H "Content-Type: application/json" \
  -d '{
    "workshop_name": "Taller Demo Actualizado",
    "contact_name": "Noelia Demo",
    "phone": "77712345",
    "email": "demo@example.com",
    "zone": "Centro",
    "specialty": "Auxilio mecánico",
    "password": "NuevaClave123",
    "latitude": -17.7833,
    "longitude": -63.1821,
    "timezone": "America/La_Paz",
    "utc_offset_minutes": -240
  }'
```

### `DELETE /api/workshops/{workshop_id}`

Elimina un taller por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8000/api/workshops/1
```

### `POST /api/vehiculos`

Registra un vehiculo desde la app movil usando `multipart/form-data`.

#### Campos enviados

- `client_id`: identificador del cliente propietario del vehiculo
- `brand`: marca del vehiculo
- `model`: modelo del vehiculo
- `year`: anio del vehiculo
- `plate`: placa
- `color`: color
- `is_primary`: `true` o `false`
- `photo`: archivo opcional en formato `jpg`, `jpeg`, `png` o `webp`

#### Ejemplo con curl

```bash
curl -X POST http://localhost:8000/api/vehiculos \
  -F "client_id=15" \
  -F "brand=Toyota" \
  -F "model=Corolla" \
  -F "year=2018" \
  -F "plate=1023HHNNI" \
  -F "color=gris" \
  -F "is_primary=true" \
  -F "photo=@/ruta/opcional/vehiculo.jpg"
```

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "client_id": 15,
  "brand": "Toyota",
  "model": "Corolla",
  "year": 2018,
  "plate": "1023HHNNI",
  "color": "gris",
  "is_primary": true,
  "photo_path": "vehicles/archivo_generado.jpg",
  "photo_url": "/uploads/vehicles/archivo_generado.jpg",
  "created_at": "2026-04-11T21:10:00.000000Z"
}
```

#### Errores posibles

- `400 Bad Request`: foto con formato no permitido
- `404 Not Found`: cliente no encontrado
- `409 Conflict`: ya existe un vehiculo con esa placa
- `422 Unprocessable Entity`: datos faltantes o invalidos

### `GET /api/vehiculos`

Lista los vehiculos registrados de un cliente en orden descendente de creacion.

#### Ejemplo

```bash
curl "http://localhost:8000/api/vehiculos?client_id=15"
```

#### Respuesta exitosa

Codigo: `200 OK`

```json
[
  {
    "id": 2,
    "client_id": 15,
    "brand": "Suzuki",
    "model": "Vitara",
    "year": 2021,
    "plate": "REMOTE20260411",
    "color": "negro",
    "is_primary": false,
    "photo_path": null,
    "photo_url": null,
    "created_at": "2026-04-11T06:12:01.102533Z"
  },
  {
    "id": 1,
    "client_id": 15,
    "brand": "Suzuki",
    "model": "Vitara",
    "year": 2021,
    "plate": "PRUEBA20260411",
    "color": "negro",
    "is_primary": false,
    "photo_path": null,
    "photo_url": null,
    "created_at": "2026-04-11T06:07:52.203747Z"
  }
]
```

#### Reglas

- `client_id` es obligatorio como query param
- el backend filtra por `client_id`
- si el cliente no existe, responde `404 Not Found`

### `DELETE /api/vehiculos/{vehicle_id}`

Elimina un vehiculo por su identificador. Si el vehiculo tenia foto guardada, tambien elimina el archivo asociado.
La eliminacion valida pertenencia usando `client_id`.

#### Ejemplo

```bash
curl -X DELETE "http://localhost:8000/api/vehiculos/1?client_id=15"
```

#### Respuestas

- `204 No Content`: vehiculo eliminado
- `404 Not Found`: vehiculo no encontrado
- `503 Service Unavailable`: base de datos no disponible

### `PUT /api/vehiculos/{vehicle_id}`

Actualiza un vehiculo existente usando `multipart/form-data`. La foto es opcional; si no se envia una nueva, se conserva la actual.

#### Campos enviados

- `client_id`
- `brand`
- `model`
- `year`
- `plate`
- `color`
- `is_primary`
- `photo` opcional

#### Ejemplo

```bash
curl -X PUT http://localhost:8000/api/vehiculos/3 \
  -F "client_id=15" \
  -F "brand=Suzuki" \
  -F "model=Vitara GLX" \
  -F "year=2022" \
  -F "plate=REMOTE20260411B" \
  -F "color=gris grafito" \
  -F "is_primary=true"
```

#### Respuestas

- `200 OK`: vehiculo actualizado
- `404 Not Found`: vehiculo no encontrado
- `409 Conflict`: placa duplicada
- `503 Service Unavailable`: base de datos no disponible

#### Reglas

- `client_id` es obligatorio
- el backend valida que el vehiculo pertenezca a ese `client_id`
- si el vehiculo no pertenece al cliente indicado, responde `404 Not Found`

### `POST /api/technicians`

Registra un tecnico asociado al sistema.

#### Body JSON

```json
{
  "full_name": "Carlos Perez",
  "phone": "77799911",
  "email": "carlos@example.com",
  "specialty": "Electricidad automotriz",
  "status": "disponible"
}
```

#### Validaciones

- `full_name`: entre 3 y 160 caracteres
- `phone`: entre 7 y 40 caracteres
- `email`: debe ser un correo valido
- `specialty`: entre 2 y 120 caracteres
- `status`: uno de `disponible`, `ocupado` o `fuera_de_servicio`

### `GET /api/technicians`

Lista todos los tecnicos registrados.

Ejemplo:

```bash
curl http://localhost:8000/api/technicians
```

### `PUT /api/technicians/{technician_id}`

Actualiza un tecnico existente usando la misma estructura JSON de creacion.

Ejemplo:

```bash
curl -X PUT http://localhost:8000/api/technicians/1 \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Carlos Perez",
    "phone": "77799911",
    "email": "carlos@example.com",
    "specialty": "Electricidad automotriz",
    "status": "ocupado"
  }'
```

### `DELETE /api/technicians/{technician_id}`

Elimina un tecnico por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8000/api/technicians/1
```

## Persistencia

Los registros de talleres se guardan en PostgreSQL en la tabla:

- `workshop_registrations`

Columnas principales:

- `id`
- `workshop_name`
- `contact_name`
- `phone`
- `email`
- `zone`
- `specialty`
- `latitude`
- `longitude`
- `timezone`
- `utc_offset_minutes`
- `created_at`

Los registros de clientes se guardan en PostgreSQL en la tabla:

- `clients`

El administrador `administrador@acb.com` no forma parte de esta tabla porque su acceso es virtual y exclusivo del sistema.

Los registros de tecnicos se guardan en PostgreSQL en la tabla:

- `technicians`

## CORS

El backend acepta solicitudes desde estos origenes de desarrollo:

- `localhost`
- `127.0.0.1`
- rangos privados `10.x.x.x`, `172.16.x.x` a `172.31.x.x` y `192.168.x.x`
- otras direcciones IPv4 cuando se accede por IP en desarrollo local

## Nota

La tabla `workshop_registrations` se crea automaticamente al iniciar el backend.
