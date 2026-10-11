# Ejecutar Arquis en Zorin OS / Linux

Requisitos: SDK .NET 10, Docker Desktop iniciado (o Docker Engine con Compose), Python 3, Bash y curl. No se requiere Visual Studio ni SQL Server instalado en el sistema. Los scripts utilizan `/proc` para reconocer sus propios procesos.

## Arrancar con un comando

Desde la carpeta del proyecto:

```bash
./levantar-proyecto.sh
```

Si el sistema de archivos no permite ejecutar archivos, use `bash levantar-proyecto.sh`. El script también puede invocarse desde otra carpeta mediante su ruta completa.

La primera ejecución descarga SQL Server, crea `.setup/sql.env`, prepara la base, importa las cuatro capas disponibles y compila únicamente el backend y el frontend. Instala pyshp localmente en `.setup/pythonlibs`; si Python no tiene pip, usa un contenedor temporal `python:3.12-slim`. No instala paquetes en el Python del sistema ni requiere compartir la carpeta del proyecto con Docker Desktop.

Las capas deben estar completas en `03_DatosPrueba` o `03_DatosPrueba/DatosSIG_Reproj` (esta última tiene prioridad). Cada capa necesita SHP, SHX, DBF y PRJ. La importación usa bloques de 100 registros para limitar la memoria de SQL Server y una transacción por capa. Conserva las tablas que ya contienen registros. Si faltan archivos de alguna capa, el arranque muestra el error.

- Visor: http://localhost:5180
- API: http://localhost:5080/health
- Swagger: http://localhost:5080/swagger
- Cuenta inicial de una base nueva: `admin` / `Admin123!`

En ejecuciones posteriores se conservan datos y usuarios. Si hay tablas vacías y capas disponibles, se intenta completar la importación. Para solicitar la importación después de copiar capas:

```bash
./levantar-proyecto.sh --importar-capas
```

Para volver a aplicar los scripts de preparación y relaciones espaciales:

```bash
./levantar-proyecto.sh --preparar-base
```

## Apagar

```bash
./detener-proyecto.sh
```

Detiene los procesos web iniciados por el lanzador Linux y el servicio SQL del proyecto. Conserva el volumen Docker y `.setup/sql.env`. Puede ejecutarse más de una vez.

Para detener únicamente el visor y la API:

```bash
./detener-proyecto.sh --solo-web
```

No utilice `docker compose down -v` si quiere conservar la base.

## Logs y problemas frecuentes

Los logs están en `.setup/Backend.log`, `.setup/Frontend.log` y `.setup/*.build.log`. Los identificadores de los procesos se guardan en `.setup/*.linux.pid`. El lanzador comprueba su identidad antes de detenerlos y rechaza puertos ocupados por otros procesos. Los servicios siguen funcionando al cerrar la terminal.

Si Docker no responde, abra Docker Desktop y compruebe `docker info`. Para revisar SQL:

```bash
docker compose --env-file .setup/sql.env logs sql
```

Puertos utilizados: 14330 (SQL), 5080 (API) y 5180 (visor). Conserve las credenciales junto con el volumen Docker. Si elimina `.setup/sql.env` pero conserva una base existente, la contraseña nueva no coincidirá con la del volumen.

Si falla el arranque después de iniciar algún servicio, consulte los logs y ejecute el script de apagado antes de reintentar. La primera ejecución necesita Internet para Docker y NuGet; el mapa base y las bibliotecas del navegador también necesitan conexión.

El migrador WPF es exclusivo de Windows. En Linux, el lanzador realiza la importación mediante Python y sqlcmd dentro del contenedor SQL Server. Los scripts originales de Windows se conservan.
