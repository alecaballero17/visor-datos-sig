# Arquis · VisorDatosSIG

Sistema web SIG para importar, consultar y visualizar información cartográfica de **San Ignacio de Velasco**. Combina un visor web responsivo, una API protegida, SQL Server y un migrador de escritorio para manzanas, lotes, códigos fijos y vías.

> Versión alfa funcional: autenticación, mapa, capas, búsqueda, fichas de información y validación inicial de Shapefiles.

## Qué ofrece

- Inicio de sesión y registro de cuentas de consulta.
- Mapa base con cuatro capas temáticas, estilos, leyenda y coordenadas.
- Búsqueda de lotes, manzanas, códigos fijos y vías; zoom y selección de resultados.
- Fichas de entidades y disponibilidad de agua potable.
- Migrador WPF que valida archivos obligatorios, WGS 84, geometría, extensión y registros.

## Arquitectura

```text
Archivos SHP → Migrador → SQL Server 2022 → API ASP.NET Core → Visor Leaflet
```

| Componente | Ubicación | Tecnología |
|---|---|---|
| Visor web | `src/Arquis.Frontend` | MVC/Razor, JavaScript, Bootstrap 5, Leaflet |
| API | `src/Arquis.Backend` | ASP.NET Core, C#, GeoJSON, cookies |
| Migrador | `src/Arquis.Migrador` | .NET 10, WPF |
| Base de datos | `02_BaseDatos` | SQL Server 2022, T-SQL, índices espaciales |

## Inicio rápido

### Requisitos

- Windows 10/11.
- [SDK de .NET 10](https://dotnet.microsoft.com/download/dotnet/10.0).
- SQL Server 2022 o LocalDB.
- Python 3 para convertir las capas SHP.
- Internet para NuGet y el mapa base.

```powershell
dotnet --version
git clone https://github.com/alecaballero17/visor-datos-sig.git
cd visor-datos-sig
```

### Preparar datos

Las capas reales no se suben al repositorio. Copia los archivos autorizados en `03_DatosPrueba/DatosSIG_Reproj/`, conservando por capa los archivos `.shp`, `.shx`, `.dbf` y `.prj`:

- `Exp_MapaBase_MZA_4326`
- `Exp_MapaBase_LOTES_4326`
- `Exp_CodigoFijo_4326`
- `Exp_MapaBase_VIAS_4326`

Consulta [las instrucciones de datos](03_DatosPrueba/README.md) antes de usar información real.

### Crear la base y cargar capas

Con LocalDB, usa el lanzador:

```powershell
.\LEVANTAR_ARQUIS.cmd
```

Con una instancia local de SQL Server, crea la base con los scripts de `02_BaseDatos`. Luego:

```powershell
py -m pip install --no-deps --target .setup/pythonlibs pyshp
py convertir-capas.py
powershell -ExecutionPolicy Bypass -File .\cargar-capas-completas.ps1
```

La carga se realiza por lotes y reemplaza las entidades cartográficas existentes; úsala solo en una base de desarrollo.

### Ejecutar el visor

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
```

- Visor: [http://localhost:5180](http://localhost:5180)
- API: [http://localhost:5080/health](http://localhost:5080/health)
- Swagger: [http://localhost:5080/swagger](http://localhost:5080/swagger)

Cuenta inicial: `admin` / `Admin123!`.

## Demostración sugerida

1. Iniciar sesión.
2. Activar/desactivar capas desde el panel lateral.
3. Buscar una entidad y acercar el mapa al resultado.
4. Seleccionar una geometría para consultar sus atributos.

## Documentación

- [Guía de ejecución](COMO_EJECUTAR.md)
- [Alcance alfa](04_Documentacion/01_ALCANCE_ALFA.md)
- [Mapeo SHP a SQL](04_Documentacion/02_MAPEO_SHP_SQL.md)
- [Endpoints](04_Documentacion/03_ENDPOINTS.md)
- [Instalación](04_Documentacion/04_INSTALACION.md)
- [Agua potable](04_Documentacion/05_AGUA_POTABLE.md)

## Seguridad y datos

Las capas reales, bases locales, archivos temporales y registros están excluidos mediante `.gitignore`. Las contraseñas se almacenan con PBKDF2-SHA256 y los endpoints de consulta requieren sesión autenticada.

## Próximos pasos

La siguiente iteración completa el migrador con mapeo configurable, cancelación, bitácora y resumen de importación; además de filtros avanzados, administración de usuarios, pruebas automatizadas y despliegue.

Proyecto académico de Sistemas de Información Geográfica. Utiliza los datos cartográficos únicamente con autorización y no los publiques en repositorios públicos.
