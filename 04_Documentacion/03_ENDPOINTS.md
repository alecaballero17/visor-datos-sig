# Endpoints alfa

| Método | Ruta | Acceso | Uso |
|---|---|---|---|
| POST | `/api/autenticacion/iniciar` | Público | Iniciar sesión |
| POST | `/api/autenticacion/cerrar` | Autenticado | Cerrar sesión |
| GET | `/api/autenticacion/sesion` | Autenticado | Sesión actual |
| GET | `/api/capas` | Administrador | Catálogo, estilos, campos y extensión |
| GET | `/api/capas/{capa}/geojson?bbox=minX,minY,maxX,maxY` | Administrador | FeatureCollection visible |
| GET | `/api/capas/{capa}/{id}` | Administrador | Feature individual |
| GET | `/api/busqueda?texto=...&capa=...` | Administrador | Búsqueda parcial paginada |
| GET | `/api/administracion/empleados?rol=Cortador%7CConector` | Administrador | Empleados operativos activos por rol |
| POST | `/api/administracion/empleados` | Administrador | Crear usuario Cortador o Conector |
| GET | `/api/administracion/asignaciones` | Administrador | Listar las 100 asignaciones recientes |
| POST | `/api/administracion/asignaciones` | Administrador | Asignar un código fijo para corte o reconexión |
| POST | `/api/administracion/asignaciones/{idOrden}/cancelar` | Administrador | Cancelar una asignación pendiente |
| GET | `/api/migraciones` | Administrador | Historial de migración |
| GET | `/health` | Público | Salud del backend |

Capas válidas: `manzanas`, `lotes`, `codigosfijos`, `vias`.

La web solo permite el ingreso al rol `Administrador`. Una asignación de corte requiere que el campo `Estado` del servicio sea `Normal` y lo cambia a `Para Corte`; una reconexión requiere que sea `Cortado`. El punto debe tener geometría. El campo `EstadoVerificado` puede seguir en falso si el estado proviene de los datos iniciales; el panel lo identifica como no verificado, pero la asignación se basa en el valor de `Estado`. La aplicación móvil y la ejecución/cierre de órdenes no forman parte de esta versión.
# Registro por email

`POST /api/autenticacion/registrar`: nombre, email y password; crea una cuenta Consultor.
`POST /api/autenticacion/iniciar`: acepta el email en `usuario`, ademas de los usuarios existentes.
Detalles en `06_REGISTRO_USUARIOS.md`.
