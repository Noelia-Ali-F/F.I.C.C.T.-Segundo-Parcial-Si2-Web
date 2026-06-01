# F.I.C.C.T.-Primer-Parcial-Si2-Diagramador-Web

Estructura base del proyecto web para el primer parcial de SI2.

## Flujo Soportado

Este proyecto se ejecuta usando Docker Compose.

- Backend, frontend y PostgreSQL estan pensados para correr dentro de contenedores.
- No se requiere crear entornos virtuales locales ni instalar dependencias manualmente en la maquina host.
- Si existen carpetas locales como `.venv`, `node_modules` o `dist`, se consideran artefactos temporales y no forman parte del flujo oficial.

## Estructura

- `frontend`: aplicacion Angular para desarrollo web
- `backend`: API FastAPI y configuracion de acceso a PostgreSQL
- `docker-compose.yml`: entorno de desarrollo con frontend, backend y base de datos
- `backend/API.md`: documentacion de endpoints del backend
- `FLUJO_PROYECTO.md`: comentario general del flujo del sistema y sus modulos principales

## Desarrollo con Docker

1. Copiar `.env.example` a `.env`
2. Copiar `backend/.env.example` a `backend/.env`
3. Ejecutar `docker compose up --build`

## Puertos

- Frontend: `http://localhost:5656`
- Backend: `http://localhost:8787`
- API healthcheck: `http://localhost:8787/api/health`
- PostgreSQL: `localhost:5454`

## Administrador Del Sistema

- Login web: `http://localhost:5656/login`
- Correo: `administrador@acb.com`
- Contrasena: `123ppp+++`

Notas:
- Este administrador es un usuario virtual del sistema.
- No se guarda en la tabla `clients` de PostgreSQL.
- Su autenticacion se resuelve directamente en `POST /api/auth/login`.
- El correo `administrador@acb.com` queda reservado y no debe usarse para registros normales de clientes.
