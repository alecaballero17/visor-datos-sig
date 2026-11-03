# Estados para la exposición

Se utilizan los suministros existentes. No se generan ni redistribuyen registros.

| Estado | Significado | Asignación |
|---|---|---|
| 0 | Para reconexión | Reconexión |
| 1 | Normal | Ninguna |
| 2 | Para corte | Corte |
| 3 | Cortado | Puede pasar manualmente a 0 |
| 4, 5 | Baja parcial / total | Ninguna |

`EstadoVerificado` se informa por separado; no habilita una reconexión.
Las estadísticas cuentan suministros, no cuentas de acceso. Al entrar a
`/dashboard` se abre el resumen. El estado 0 forma parte del total y del gráfico,
y no se contabiliza como sin clasificar. No hay cifras mínimas ni datos inventados:
si el conjunto cargado no tiene candidatos, su contador muestra cero.

## Cambio manual

En Panel de Operaciones → Reconexiones, desplegar “Pasar un suministro cortado
a candidato a reconexión”, buscar con los filtros actuales y pulsar “Marcar
candidato”. Confirmar para cambiar 3 → 0. Después puede seleccionarse para un
ticket. Esta acción todavía no restituye el servicio: la ejecución de la orden
de reconexión lo cambia a Normal mediante el flujo existente.

Contrato de API:

- `GET /api/dashboard/kpis`: añade `tarjetasResumen.conexionesParaReconexion`,
  `graficoDona.cantidades.paraReconexion` y `graficoDona.porcentajes.paraReconexion`.
- `GET /api/rutas-trabajo/entidades-disponibles?tipo=Corte|Reconexion|Cortado`:
  devuelve únicamente estados 2, 0 y 3 respectivamente, con coordenadas disponibles.
  La asignación masiva por cantidad utiliza el mismo criterio. Los tickets rechazan
  con 409 una selección por identificadores cuyo estado cambió antes de guardarse.
- `PUT /api/rutas-trabajo/codigos/{id}/candidato-reconexion`: sin cuerpo,
  requiere sesión con rol `Administrador`. Actualiza atómicamente solo un registro
  en estado 3 a estado 0, marca el estado verificado y actualiza la fecha.
  Devuelve 200 con `{ idCodigo, estado: 0 }`, 404 si no existe y 409 si no está
  cortado (incluidos reintentos). Sin sesión/rol devuelve 401/403.
- SignalR emite `ReceiveEstadoServicioActualizado` después de guardar. El mapa
  y los KPIs abiertos se actualizan con los datos actuales.

## Base SQL Server en Docker

La restricción anterior `Estado BETWEEN 1 AND 5` impedía guardar candidatos.
Ejecutar `02_BaseDatos/14_Candidatos_Reconexion.sql` sobre la base existente,
o iniciar la API actualizada para aplicar la migración EF equivalente.
Ambas opciones conservan registros y permiten estados del 0 al 5.
El script puede repetirse. Revertir la migración se bloquea si quedan estados 0.

Validación local sin SQL: `dotnet run --project tests/Arquis.RoutingChecks --configuration Release`
y `node tests/realtime-checks.cjs`. Estas pruebas verifican las reglas de selección,
la transición elegible y la distribución de eventos; no sustituyen una prueba
integrada del cambio en SQL con una sesión de administrador.

`tests/service-state-checks.sql` verifica la restricción en SQL y, si existe
algún suministro cortado, ensaya la transición dentro de una transacción que
se revierte. Si no existen cortados, informa `SKIP` sin crear datos de prueba.
