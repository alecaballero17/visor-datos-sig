# Matriz inicial SHP -> SQL

| SHP oficial | Tabla SQL | Campo SHP | Campo SQL |
|---|---|---|---|
| Exp_MapaBase_MZA_4326 | dbo.Manzanas | Id | IdOrigen |
| Exp_MapaBase_MZA_4326 | dbo.Manzanas | UV_MZA | UV_MZA |
| Exp_MapaBase_MZA_4326 | dbo.Manzanas | UV | UV |
| Exp_MapaBase_MZA_4326 | dbo.Manzanas | MZA | MZA |
| Exp_MapaBase_LOTES_4326 | dbo.Lotes | Id | IdOrigen |
| Exp_MapaBase_LOTES_4326 | dbo.Lotes | NroLote | NroLote |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | CodF_SQL | CodF_SQL |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | CodF_SIG | CodF_SIG |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | CodFijo | CodFijo |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | Nombre | Nombre |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | Longi | Longitud |
| Exp_CodigoFijo_4326 | dbo.CodigosFijos | Latid | Latitud |
| Exp_MapaBase_VIAS_4326 | dbo.Vias | OBJECTID | OBJECTID |
| Exp_MapaBase_VIAS_4326 | dbo.Vias | Nombre/name | Nombre (confirmar precedencia) |
| Exp_MapaBase_VIAS_4326 | dbo.Vias | type | TipoVia |
| Exp_MapaBase_VIAS_4326 | dbo.Vias | OSMID/osm_id | OSMID |

Todas las geometrías se almacenan en `Geom geometry` con SRID 4326. Antes de automatizar la migración hay que confirmar con el docente la precedencia de los campos duplicados de Vías y validar la anomalía observada en algunos valores de `Latid` de Códigos Fijos.
