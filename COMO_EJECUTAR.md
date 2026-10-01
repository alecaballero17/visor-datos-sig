# Ejecutar Arquis sin Visual Studio

## Primera instalacion

1. Instale el SDK de .NET 10 para Windows (no solo el runtime): https://dotnet.microsoft.com/download/dotnet/10.0.
2. Instale/abra Docker Desktop, usando contenedores Linux. No necesita instalar SQL Server ni LocalDB.
3. Instale Python 3 con el lanzador `py`: https://www.python.org/downloads/windows/.
4. Abra una terminal nueva de PowerShell en la carpeta del proyecto y ejecute:

```powershell
py -m pip install --no-deps --target .setup/pythonlibs pyshp
.\LEVANTAR_ARQUIS.cmd
```

Mantenga Docker Desktop abierto. La primera ejecucion descarga SQL Server 2022, crea la base, importa las capas disponibles, prepara relaciones espaciales y compila el backend y el frontend. Necesita Internet; espere el mensaje `Listo`.

Las cuatro capas `Exp_*_4326` deben conservar sus archivos SHP, SHX, DBF y PRJ juntos. Se aceptan en `03_DatosPrueba` o `03_DatosPrueba/DatosSIG_Reproj` (esta ultima tiene prioridad).

## Abrir el visor

- Visor: http://localhost:5180
- API: http://localhost:5080/health
- Swagger: http://localhost:5080/swagger
- Administrador inicial de una base nueva: `admin` / `Admin123!`.

## Siguientes ejecuciones

```powershell
.\LEVANTAR_ARQUIS.cmd
```

Se conservan los usuarios y los datos. Si copia las capas despues del primer arranque:

```powershell
.\LEVANTAR_ARQUIS.cmd -ImportarCapas
```

La importacion del lanzador solo carga tablas vacias. Para aplicar nuevamente los scripts de indices y relaciones: ` .\LEVANTAR_ARQUIS.cmd -PrepararBase`.

## Docker y datos

Solo SQL Server corre en Docker; .NET y Python se ejecutan en Windows. SQL escucha en `127.0.0.1:14330`; el lanzador configura la conexion del backend automaticamente. Las credenciales locales se generan en `.setup/sql.env`, excluido de Git. Conserve ese archivo junto con el volumen Docker `arquis_sql-data`.

Para detener solo SQL Server:

```powershell
docker compose --env-file .setup/sql.env stop sql
```

No use `down -v` si desea conservar la base. Cerrar la ventana del lanzador no detiene los servidores web. Reiniciar Windows los detiene.

## Problemas frecuentes

- Docker no responde: abra Docker Desktop y espere a que el motor Linux este listo.
- Puerto ocupado: libere 14330 (SQL), 5080 (API) o 5180 (visor).
- SDK incorrecto: `dotnet --list-sdks` debe mostrar una version 10.x.
- Falta pyshp: ejecute el comando pip de la primera instalacion.
- SQL no inicia: `docker compose --env-file .setup/sql.env logs sql`.
- Error del visor: revise `.setup/Backend.log`, `.setup/Backend.error.log`, `.setup/Frontend.log` y `.setup/Frontend.error.log`.

Para conservar el arranque antiguo con SQL Server 2022 LocalDB instalado: `.\LEVANTAR_ARQUIS.cmd -LocalDB`. Las bases de Docker y LocalDB son independientes; reinicie los procesos web al cambiar entre ellas.
