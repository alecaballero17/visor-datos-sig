# Datos locales del mapa

Las capas reales incluyen nombres registrados y ubicaciones de usuarios.
La carpeta `DatosSIG_Reproj` permanece en el equipo local y esta excluida
del repositorio Git. No se incluyen bases de datos ni cuentas creadas en
la instalacion local.

Para usar las capas existentes en otra instalacion, copie los archivos del
paquete de datos autorizado a `03_DatosPrueba` o `03_DatosPrueba/DatosSIG_Reproj`
(esta ultima tiene prioridad). Ambas ubicaciones de las capas estan excluidas de Git:

- `Exp_CodigoFijo_4326`: SHP/SHX/DBF/PRJ/CPG, 6.271 registros.
- `Exp_MapaBase_LOTES_4326`: SHP/SHX/DBF/PRJ/CPG, 15.281 registros.
- `Exp_MapaBase_MZA_4326`: SHP/SHX/DBF/PRJ/CPG, 863 registros.
- `Exp_MapaBase_VIAS_4326`: SHP/SHX/DBF/PRJ/CPG, 578 registros.

Luego instale pyshp y ejecute `LEVANTAR_ARQUIS.cmd` segun `COMO_EJECUTAR.md`.
Si la base ya existe, use `LEVANTAR_ARQUIS.cmd -ImportarCapas`.
Sin estas capas, el sistema permite registrarse e iniciar sesion,
pero la base cartografica del proyecto no contiene entidades locales.
