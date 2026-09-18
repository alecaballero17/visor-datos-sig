# Ejecutar Arquis en Windows

## 1. Requisitos de la primera instalación

Instale el **SDK de .NET 10**, no solamente el runtime, desde
https://dotnet.microsoft.com/download/dotnet/10.0.
Instale **SQL Server 2022 Express LocalDB** siguiendo
https://learn.microsoft.com/es-es/sql/database-engine/configure-windows/sql-server-express-localdb.
El arranque utiliza la instancia `MSSQLLocalDB` del usuario actual de Windows.
No necesita Visual Studio. Abra una terminal nueva después de instalar los requisitos.
La primera compilación necesita Internet para restaurar NuGet; el mapa base y
Bootstrap/Leaflet también necesitan Internet.

## 2. Capas del mapa (primera instalación)

Las capas reales se conservan fuera de GitHub. Para usar los datos del mapa,
copie los archivos autorizados siguiendo [las instrucciones de datos](03_DatosPrueba/README.md).
Mantenga juntos los archivos SHP, SHX, DBF y demás archivos complementarios.
Si no dispone de ellos, puede iniciar el sistema con el mapa sin lotes.

Para importar las capas necesita **Python 3**, con el lanzador `py`, y la biblioteca
`pyshp`. Instale Python desde https://www.python.org/downloads/windows/.
Abra PowerShell en la carpeta del proyecto y ejecute una sola vez:

```powershell
py -m pip install --no-deps --target .setup/pythonlibs pyshp
```

## 3. Levantar el proyecto

Haga doble clic en **LEVANTAR_ARQUIS.cmd**. También puede ejecutarlo desde PowerShell:

```powershell
.\LEVANTAR_ARQUIS.cmd
```

El archivo comprueba los requisitos, inicia LocalDB, crea y prepara la base
si hace falta, importa las capas disponibles en una base nueva, compila e inicia
el backend y el frontend. Conserva los usuarios y datos existentes.
La primera preparación espacial puede tardar varios minutos; espere el mensaje
`Listo`. Las siguientes ejecuciones evitan repetir esa preparación.
Si una aplicación de Arquis ya está ejecutándose, no inicia otra instancia.
La ventana muestra los errores y permanece abierta para que pueda leerlos.

Abra **http://localhost:5180**. Puede elegir **Registrar usuario** para crear
una cuenta con nombre, email y contraseña de al menos ocho caracteres.
En una base nueva, el administrador inicial es `admin` / `Admin123!`.
Los usuarios creados en otra computadora no se copian junto con el código.
La API responde en http://localhost:5080/health.

## 4. Importar capas después o aplicar actualizaciones de la base

Después de copiar las capas e instalar pyshp:

```powershell
.\LEVANTAR_ARQUIS.cmd -ImportarCapas
```

Para volver a aplicar los scripts de preparación sin convertir las capas:

```powershell
.\LEVANTAR_ARQUIS.cmd -PrepararBase
```

La importación omite las tablas que ya contienen registros; no reemplaza sus datos.
La preparación vuelve a construir índices y relaciones espaciales.

## 5. Problemas frecuentes

- **Falta SDK o LocalDB:** complete el paso 1. El script no instala estos programas automáticamente.
- **Falta shapefile/pyshp:** complete el paso 2 y vuelva a ejecutar con `-ImportarCapas`.
- **Puerto ocupado por otra aplicación:** libere los puertos 5080 y 5180 y vuelva a ejecutar.
- **Error de compilación/restauración:** revise la conexión a Internet y el error mostrado en la ventana.
- **Aplicación no responde:** consulte `.setup/Backend.log`, `.setup/Backend.error.log`,
  `.setup/Frontend.log` y `.setup/Frontend.error.log`.

Cerrar la ventana del lanzador no detiene los servidores: se ejecutan en segundo
plano. Reiniciar Windows los detiene; después vuelva a abrir el lanzador.
Este arranque corresponde al desarrollo local; no configura un servidor público.
