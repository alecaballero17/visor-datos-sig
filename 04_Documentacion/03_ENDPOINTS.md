# Endpoints alfa

| Método | Ruta | Acceso | Uso |
|---|---|---|---|
| POST | `/api/autenticacion/iniciar` | Público | Iniciar sesión |
| POST | `/api/autenticacion/cerrar` | Autenticado | Cerrar sesión |
| GET | `/api/autenticacion/sesion` | Autenticado | Sesión actual |
| GET | `/api/capas` | Autenticado | Catálogo, estilos, campos y extensión |
| GET | `/api/capas/{capa}/geojson?bbox=minX,minY,maxX,maxY` | Autenticado | FeatureCollection visible |
| GET | `/api/capas/{capa}/{id}` | Autenticado | Feature individual |
| GET | `/api/busqueda?texto=...&capa=...` | Autenticado | Búsqueda parcial paginada |
| GET | `/api/migraciones` | Administrador | Historial de migración |
| GET | `/health` | Público | Salud del backend |

Capas válidas: `manzanas`, `lotes`, `codigosfijos`, `vias`.
# Registro por email

`POST /api/autenticacion/registrar`: nombre, email y password; crea una cuenta Consultor.
`POST /api/autenticacion/iniciar`: acepta el email en `usuario`, ademas de los usuarios existentes.
Detalles en `06_REGISTRO_USUARIOS.md`.
