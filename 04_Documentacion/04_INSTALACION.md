# Instalación local

## Requisitos

- SDK .NET 10. Visual Studio es opcional.
- Docker Desktop abierto con contenedores Linux; SQL Server 2022 se descarga automaticamente.
- Navegador Chrome/Edge actual.
- Acceso a Internet para restaurar NuGet y cargar CDN/OSM durante desarrollo.

## Base de datos

Siga [COMO_EJECUTAR.md](../COMO_EJECUTAR.md): instale pyshp y ejecute `LEVANTAR_ARQUIS.cmd`. El lanzador inicia SQL Server en Docker, crea el esquema, importa las capas disponibles y aplica los scripts 10 a 13. Acepta las capas directamente en `03_DatosPrueba` o en `03_DatosPrueba/DatosSIG_Reproj`.

El lanzador aplica automáticamente las migraciones `13_Registro_Email.sql` y `14_Asignacion_Empleados.sql`. La última crea el rol `Conector` y la tabla de asignaciones. Los usuarios existentes conservan sus contraseñas y roles.

## Backend

El lanzador configura `ConnectionStrings__DefaultConnection` con las credenciales generadas en `.setup/sql.env`. Use `LEVANTAR_ARQUIS.cmd` o `iniciar.ps1` para heredar esa conexion. Swagger queda disponible en desarrollo.

## Frontend

Verifique `BackendBaseUrl` en `src/Arquis.Frontend/appsettings.json`, inicie `Arquis.Frontend` y abra `http://localhost:5180`.

Para HTTPS de desarrollo, actualice los orígenes CORS en el backend con el origen exacto del frontend.
