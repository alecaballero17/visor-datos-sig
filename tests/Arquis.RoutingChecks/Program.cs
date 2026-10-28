using Arquis.Backend.Services;
using NetTopologySuite.Geometries;
using NetTopologySuite.Operation.Union;

static void Check(bool condition, string name)
{
    if (!condition) throw new Exception(name);
    Console.WriteLine($"PASS: {name}");
}
var graph = new RoadNetworkGraph();
Check(double.IsPositiveInfinity(graph.CalcularRutaDijkstra(0, 0, 0, .001).DistanciaMetros), "Empty network rejects route");
graph.AgregarLinea([new(0, 0), new(.001, 0), new(.001, .001)], "L-shaped street");
var path = graph.CalcularRutaDijkstra(0, .0002, .0008, .001);
Check(path.Coordenadas.Any(c => c.Equals2D(new Coordinate(.001, 0))), "Route follows street corner instead of diagonal");
Check(path.DistanciaMetros > 170 && path.DistanciaMetros < 185, "Distance measures street geometry");
var reverse = graph.CalcularRutaDijkstra(.0008, .001, 0, .0002);
Check(Math.Abs(path.DistanciaMetros - reverse.DistanciaMetros) < .01, "Dataset streets are bidirectional");
var access = graph.CalcularRutaDijkstra(.0001, .0002, .0001, .0006);
Check(access.Coordenadas.All(c => c.Y == 0), "Parcel access is projected onto street without off-road segments");
graph.AgregarLinea([new(.01, 0), new(.011, 0)], "Disconnected street");
Check(double.IsPositiveInfinity(graph.CalcularRutaDijkstra(0, 0, 0, .01).DistanciaMetros), "Disconnected components reject route");
Check(double.IsPositiveInfinity(graph.CalcularRutaDijkstra(20, 20, 0, 0).DistanciaMetros), "Out-of-area start rejects route");
Check(double.IsPositiveInfinity(graph.CalcularRutaDijkstra(double.NaN, 0, 0, 0).DistanciaMetros), "Nonfinite coordinates reject route");
var factory = new GeometryFactory();
var noded = UnaryUnionOp.Union((Geometry)factory.CreateMultiLineString([
    factory.CreateLineString([new(0, .001), new(.002, .001)]),
    factory.CreateLineString([new(.001, 0), new(.001, .002)])]));
var crossing = new RoadNetworkGraph();
for (int i = 0; i < noded.NumGeometries; i++)
    if (noded.GetGeometryN(i) is LineString line) crossing.AgregarLinea(line.Coordinates, "Crossing");
var turn = crossing.CalcularRutaDijkstra(.001, 0, .002, .001);
Check(turn.Coordenadas.Any(c => c.Equals2D(new Coordinate(.001, .001))) && double.IsFinite(turn.DistanciaMetros),
    "Geometric intersections become traversable junctions");
Check(graph.CalcularRutaDijkstra(0, .0002, 0, .0002).DistanciaMetros == 0, "Repeated stop has zero distance");
