# Datos locales del mapa

Las capas reales incluyen nombres registrados y ubicaciones de usuarios.
La carpeta `DatosSIG_Reproj` permanece en el equipo local y esta excluida
del repositorio Git. No se incluyen bases de datos ni cuentas creadas en
la instalacion local.

Para usar las capas existentes en otra instalacion, copie los archivos del
paquete de datos autorizado a `03_DatosPrueba/DatosSIG_Reproj`:

- `Exp_CodigoFijo_4326`: SHP/SHX/DBF/PRJ/CPG, 6.271 registros.
- `Exp_MapaBase_LOTES_4326`: SHP/SHX/DBF/PRJ/CPG, 15.281 registros.
- `Exp_MapaBase_MZA_4326`: SHP/SHX/DBF/PRJ/CPG, 863 registros.
- `Exp_MapaBase_VIAS_4326`: SHP/SHX/DBF/PRJ/CPG, 578 registros.

Luego, simplemente inicie el backend (por ejemplo ejecutando `dotnet run` en el proyecto Arquis.Backend).
El sistema detectará automáticamente los archivos `.shp` y poblará la base de datos usando el seeder nativo integrado en C# (`GeoDataSeeder.cs`). 

No es necesario ejecutar scripts adicionales de Python o PowerShell. Sin estas capas, el sistema permite registrarse e iniciar sesión, y utilizará datos de prueba mínimos (si están configurados), pero la base cartográfica del proyecto no contendrá sus entidades reales.
