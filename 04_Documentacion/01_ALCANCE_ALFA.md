# Alcance de Arquis Alfa

## Requisitos abordados

- RF-SEG-01/02/04/05/06: autenticación, roles leídos desde SQL, rutas API protegidas, cierre/expiración y bitácora de acceso.
- RF-VIS-01 a RF-VIS-10: mapa OSM, cuatro capas, encendido/apagado, leyenda, zoom/escala/coordenadas, estilos, zoom a resultados, carga controlada por `bbox`, diseño responsive y selección resaltada.
- RF-CON-01/03/04/06/07/08/09: identificación por clic, búsqueda parcial, resultados, acercamiento y sincronización básica.
- RT-01/02/03/04/05/07/08/10: solución C# .NET 10, MVC/Razor, SQL Server, Leaflet, acceso parametrizado, GeoJSON y Kestrel.

## Pendiente para siguientes iteraciones

- Migrador de escritorio completo RF-MIG-01 a RF-MIG-14.
- RF-SEG-03 administración de usuarios/restablecimiento de contraseña.
- RF-CON-02 selección explícita cuando hay coincidencia de varias capas en un punto.
- RF-CON-05 filtros combinados avanzados y RF-CON-10 exportación CSV.
- Pruebas unitarias/integración completas, medición de rendimiento y publicación IIS.
