# Acceso de administradores y empleados operativos

La versión web es de uso exclusivo del rol `Administrador`. El formulario de login no ofrece registro público. Las cuentas operativas se crean desde el panel web con rol `Cortador` o `Conector`; cada cuenta recibe login y contraseña inicial y puede usarse posteriormente desde la aplicación móvil.

`POST /api/administracion/empleados` recibe `nombre`, `login`, `password` y `rol`. Solo permite los roles `Cortador` y `Conector`; la contraseña debe tener entre 8 y 128 caracteres. `GET /api/administracion/empleados?rol=Cortador` y `?rol=Conector` devuelve las cuentas activas para asignarlas.

El endpoint legado `POST /api/autenticacion/registrar` ya no es público: requiere sesión de administrador. Las cuentas existentes que no tienen rol Administrador pueden iniciar sesión, pero no accederán a la interfaz ni a los endpoints de la web.

La migración `14_Asignacion_Empleados.sql` instala el rol `Conector` y `dbo.OrdenesTrabajo`. Para detalles de asignación, condiciones de estado y rutas, consulte [03_ENDPOINTS.md](03_ENDPOINTS.md).
