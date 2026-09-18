# Arquis - versión alfa

Base inicial del proyecto SIG solicitada para la **Fase I / versión alfa**. Está construida con **C# / .NET 10**, **ASP.NET Core Web API**, **ASP.NET Core MVC + Razor**, **SQL Server 2022**, **Bootstrap 5** y **Leaflet**.

## Contenido

- `src/Arquis.Backend`: API protegida por cookie, catálogo de capas, GeoJSON acotado por `bbox`, búsqueda e historial de migraciones.
- `src/Arquis.Frontend`: MVC/Razor responsivo con login, mapa base, cuatro capas, leyenda, identificación, búsqueda y sincronización básica de resultados.
- Ficha de agua potable al seleccionar códigos fijos o lotes, con datos disponibles y estado del servicio sin verificar. Consulte `04_Documentacion/05_AGUA_POTABLE.md`.
- Registro con nombre, email y contraseña desde el login. Las nuevas cuentas tienen rol Consultor e ingresan con su email; los usuarios existentes conservan su acceso.
- Colores: manzanas rojo, lotes celeste, códigos fijos ámbar y vías violeta. Los símbolos de agua y las casillas Con agua/Sin agua mantienen la clasificación del servicio.
- `02_BaseDatos`: scripts originales entregados por el docente y `09_Arquis_Alfa.sql` para bitácoras/rol Consultor.
- `03_DatosPrueba`: SHP oficiales incluidos en el ZIP de especificaciones.
- `04_Documentacion`: mapeo, endpoints, alcance alfa e instalación.

## Arranque rápido

Haga doble clic en **LEVANTAR_ARQUIS.cmd** para comprobar los requisitos,
preparar la base cuando corresponda y levantar ambas aplicaciones.
La guía completa, incluidos los requisitos y la importación de capas, está en
[COMO_EJECUTAR.md](COMO_EJECUTAR.md).

Para desarrollo local en Windows se incluyen `preparar-base.ps1` e `iniciar.ps1`.
Requieren el [SDK de .NET 10](https://dotnet.microsoft.com/en-us/download/dotnet/10.0)
y [SQL Server 2022 LocalDB](https://learn.microsoft.com/es-es/sql/database-engine/configure-windows/sql-server-express-localdb).
La configuración de desarrollo utiliza `(localdb)\MSSQLLocalDB`.

```powershell
# Opcional: copiar primero las capas autorizadas según 03_DatosPrueba/README.md.
py -m pip install --no-deps --target .setup/pythonlibs pyshp
py convertir-capas.py

# Crear la base, importar las capas convertidas e iniciar ambas aplicaciones.
powershell -ExecutionPolicy Bypass -File .\preparar-base.ps1
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
```

Abra http://localhost:5180 e ingrese con `admin` / `Admin123!`.
También puede elegir **Registrar usuario** y crear una cuenta con nombre,
email y contraseña de al menos 8 caracteres. Ingrese luego con ese email.
Los logs de ambas aplicaciones quedan en `.setup`.
La preparación conserva las tablas que ya tienen datos y no vuelve a crear una base existente.
El mapa base y las librerías Bootstrap/Leaflet utilizan recursos de Internet.

Para una instalación con SQL Server como servicio:

1. En SQL Server 2022 ejecute `02_BaseDatos/01_CrearBD.sql` y luego los scripts siguientes que correspondan. Ejecute al final `09_Arquis_Alfa.sql`.
2. Importe los SHP siguiendo `02_BaseDatos/02_Importar_SHP.md` o use el migrador que se desarrollará en la siguiente iteración.
3. Revise `src/Arquis.Backend/appsettings.json` y configure `DefaultConnection`.
4. Abra `Arquis.sln` en Visual Studio 2026 y restaure NuGet.
5. Inicie primero `Arquis.Backend` en `http://localhost:5080` y luego `Arquis.Frontend` en `http://localhost:5180`.
6. Ingrese con `admin` y la contraseña inicial indicada por el script oficial (`Admin123!`). Cámbiela antes de publicar.

## Repositorio GitHub

El repositorio contiene código, scripts de esquema y documentación. Las capas
reales con nombres y ubicaciones se mantienen locales según
`03_DatosPrueba/README.md`; tampoco se versionan credenciales locales, logs,
instaladores o archivos de la base de datos. La configuración incluida usa
autenticación integrada de Windows y no contiene contraseñas de conexión.

La rama inicial es `main`. El workflow `.github/workflows/build.yml` restaura
NuGet y compila ambos proyectos en Release en cada push o pull request,
usando las acciones oficiales [setup-dotnet](https://github.com/actions/setup-dotnet).
No realiza publicación ni necesita una base de datos para compilar.
El remoto se configurará cuando se proporcione la URL de GitHub.

> Este paquete es una base **alfa**, no la entrega final de 45 días. Aún falta completar el migrador WinForms/WPF, gestión administrativa de usuarios, filtros combinados avanzados, exportación CSV, pruebas automatizadas, endurecimiento de seguridad y publicación IIS/Kestrel.

## Nota de validación

Validado en Windows con .NET SDK 10.0.401: restauración NuGet y compilación
de ambos proyectos sin errores ni advertencias. La API y el frontend responden
en sus puertos locales, el inicio de sesión de administrador funciona y las
cuatro capas entregan GeoJSON. La preparación local aplica el script
`10_Asociacion_Indices_Espaciales.sql` para utilizar los índices espaciales
durante la asociación de lotes, manzanas y códigos fijos.
