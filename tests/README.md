# Web checks

From the repository root:

```sh
dotnet run --project tests/Arquis.RoutingChecks
node tests/realtime-checks.cjs
```

The console checks exercise routing without SQL Server: street corners, projected
access, disconnected/empty networks, out-of-area points, geometric intersections,
bidirectional travel and repeated stops. They use the backend's actual graph code.
The Node checks verify shared SignalR subscriptions, event filtering, reconnection
notifications and cleanup using a hub double.

For a presentation rehearsal, run the backend/frontend against the database
prepared with `02_BaseDatos/` and check:

1. Dashboard counts match `dbo.CodigosFijos` grouped by `Estado`; unverified states
   are disclosed and no made-up distribution appears. No routes means empty bars.
2. Assign a route from either the first selected stop or a clicked street position.
   Preview and saved route must follow the same street geometry. Disconnected
   selections show a useful error and do not create partial assignments.
3. With the dashboard/monitor open, submit an existing mobile position or complete
   an order. The marker, compliance and connection layers update without reload.
4. Restart the API. The web shows disconnection and refreshes on reconnection.

Only the database's loaded street geometries are used. No directions/turn
restrictions exist in the supplied schema, so streets are treated as bidirectional.
Street access must be within 200 m; inaccessible selections are rejected.
Automatic geographic/demo route seeding is disabled; existing rows are preserved.
The browser loads SignalR from the CDN, like the existing Leaflet/Three.js assets.
