# Instalación local

## Requisitos

- SDK .NET 10. Visual Studio es opcional.
- SQL Server 2022 LocalDB para el arranque con `preparar-base.ps1`.
- Navegador Chrome/Edge actual.
- Acceso a Internet para restaurar NuGet y cargar CDN/OSM durante desarrollo.

## Base de datos

Desde la raíz del proyecto ejecute `powershell -ExecutionPolicy Bypass -File .\preparar-base.ps1`. Crea el esquema y aplica las mejoras de asociación, disponibilidad y registro por email (scripts 10 a 13). Para importar datos reales, copie primero las capas autorizadas según `03_DatosPrueba/README.md`, instale pyshp y ejecute `convertir-capas.py`.

Para actualizar una base ya existente al registro por email, aplique `13_Registro_Email.sql` antes de ejecutar la nueva versión. Los usuarios existentes conservan sus contraseñas y pueden seguir entrando con su usuario.

## Backend

Configure `ConnectionStrings:DefaultConnection` en `src/Arquis.Backend/appsettings.json`. Inicie el proyecto `Arquis.Backend`. Swagger queda disponible en desarrollo.

## Frontend

Verifique `BackendBaseUrl` en `src/Arquis.Frontend/appsettings.json`, inicie `Arquis.Frontend` y abra `http://localhost:5180`.

Para HTTPS de desarrollo, actualice los orígenes CORS en el backend con el origen exacto del frontend.
