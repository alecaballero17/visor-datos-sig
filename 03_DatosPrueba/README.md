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

Luego ejecute `convertir-capas.py` y `preparar-base.ps1` segun el README
principal. Sin estas capas, el sistema permite registrarse e iniciar sesion,
pero la base cartografica del proyecto no contiene entidades locales.
