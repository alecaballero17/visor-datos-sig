using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using Arquis.Backend.Data;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Services
{
    public class DijkstraRoutingService
    {
        private readonly ArquisDbContext _context;
        private static RoadNetworkGraph? _cachedGraph;
        private static readonly SemaphoreSlim _lock = new(1, 1);
        private static DateTime _lastLoaded = DateTime.MinValue;

        public DijkstraRoutingService(ArquisDbContext context)
        {
            _context = context;
        }

        public class PuntoPartidaDto
        {
            public double Latitud { get; set; }
            public double Longitud { get; set; }
            public string Nombre { get; set; } = "Punto de Partida (Base)";
        }

        public class PuntoIntervencionDto
        {
            public int? IdCodigoFijo { get; set; }
            public int? IdLote { get; set; }
            public string? CodigoSuministro { get; set; }
            public string? Lote { get; set; }
            public string? Titular { get; set; }
            public string? Direccion { get; set; }
            public double Latitud { get; set; }
            public double Longitud { get; set; }
            public decimal? MontoDeuda { get; set; }
            public string? Observaciones { get; set; }
            public int Orden { get; set; }
            public double? DistanciaDesdeAnteriorMetros { get; set; }
        }

        public class ResultadoOptimizacionRuta
        {
            public PuntoPartidaDto Partida { get; set; } = new();
            public List<PuntoIntervencionDto> PuntosOrdenados { get; set; } = new();
            public double DistanciaTotalMetros { get; set; }
            public double DistanciaTotalKm => Math.Round(DistanciaTotalMetros / 1000.0, 2);
            public int TiempoEstimadoMinutos { get; set; }
            public string GeometriaGeoJson { get; set; } = string.Empty;
            public List<List<double>> CoordenadasRuta { get; set; } = new(); // [[lng, lat], ...]
            public string AlgoritmoUtilizado { get; set; } = "Vecino más cercano por distancia Dijkstra sobre dbo.Vias (bidireccional)";
        }

        /// <summary>
        /// Obtiene o construye en memoria el grafo topológico vial de San Ignacio de Velasco.
        /// </summary>
        public async Task<RoadNetworkGraph> ObtenerGrafoAsync(bool forzarRecarga = false)
        {
            if (_cachedGraph != null && !forzarRecarga && (DateTime.UtcNow - _lastLoaded).TotalMinutes < 60)
            {
                return _cachedGraph;
            }

            await _lock.WaitAsync();
            try
            {
                if (_cachedGraph != null && !forzarRecarga && (DateTime.UtcNow - _lastLoaded).TotalMinutes < 60)
                {
                    return _cachedGraph;
                }

                var graph = new RoadNetworkGraph();

                // 1. Consultar geometrías de calles reales
                var vias = await _context.Vias
                    .Where(v => v.Geom != null)
                    .Select(v => new { v.IdVia, v.Nombre, v.Geom })
                    .ToListAsync();

                // Node intersections before building edges: crossings need not be source vertices.
                var lines = vias.SelectMany(v => Enumerable.Range(0, v.Geom!.NumGeometries)
                    .Select(i => v.Geom.GetGeometryN(i))).OfType<LineString>()
                    .Where(l => !l.IsEmpty && l.NumPoints >= 2).ToArray();
                if (lines.Length > 0)
                {
                    var noded = NetTopologySuite.Operation.Union.UnaryUnionOp.Union(
                        (Geometry)lines[0].Factory.CreateMultiLineString(lines));
                    for (int i = 0; i < noded.NumGeometries; i++)
                        if (noded.GetGeometryN(i) is LineString line)
                            graph.AgregarLinea(line.Coordinates, "Red vial");
                }

                _cachedGraph = graph;
                _lastLoaded = DateTime.UtcNow;
                return graph;
            }
            finally
            {
                _lock.Release();
            }
        }

        /// <summary>
        /// Optimiza la ruta utilizando el algoritmo de Dijkstra sobre la red vial dbo.Vias.
        /// Ordena estrictamente los puntos 1, 2, 3... N garantizando circulación sobre ejes viales.
        /// </summary>
        public async Task<ResultadoOptimizacionRuta> OptimizarRutaAsync(
            PuntoPartidaDto partida,
            List<PuntoIntervencionDto> puntos)
        {
            if (puntos == null || puntos.Count == 0)
            {
                return new ResultadoOptimizacionRuta
                {
                    Partida = partida,
                    PuntosOrdenados = new List<PuntoIntervencionDto>(),
                    DistanciaTotalMetros = 0,
                    TiempoEstimadoMinutos = 0,
                    GeometriaGeoJson = "{}"
                };
            }

            var graph = await ObtenerGrafoAsync();
            if (!graph.TieneVias)
                throw new RutaNoDisponibleException("No hay vías cargadas en dbo.Vias. Prepare la base de datos antes de calcular recorridos.");
            var resultado = new ResultadoOptimizacionRuta
            {
                Partida = partida
            };

            // Lista para almacenar la secuencia completa de coordenadas de la ruta [lng, lat]
            var rutaCoordinates = new List<List<double>>();

            // Punto de partida inicial
            var currentLat = partida.Latitud;
            var currentLng = partida.Longitud;


            var restantes = new List<PuntoIntervencionDto>(puntos);
            var ordenados = new List<PuntoIntervencionDto>();
            double distanciaTotalMetros = 0;
            int ordenNum = 1;

            // Algoritmo Greedy con optimización Dijkstra punto a punto:
            // En cada parada, selecciona el punto no visitado con menor distancia de trayectoria por calles
            while (restantes.Count > 0)
            {
                PuntoIntervencionDto? mejorPunto = null;
                double mejorDistancia = double.MaxValue;
                List<Coordinate>? mejorTrayectoria = null;

                foreach (var candidato in restantes)
                {
                    var pathResult = graph.CalcularRutaDijkstra(
                        currentLat, currentLng,
                        candidato.Latitud, candidato.Longitud);

                    if (pathResult.DistanciaMetros < mejorDistancia)
                    {
                        mejorDistancia = pathResult.DistanciaMetros;
                        mejorPunto = candidato;
                        mejorTrayectoria = pathResult.Coordenadas;
                    }
                }

                if (mejorPunto == null)
                {
                    throw new RutaNoDisponibleException("No existe un recorrido conectado por las vías disponibles para todos los puntos seleccionados. Seleccione puntos de la misma red vial y a menos de 200 m de una calle.");
                }

                mejorPunto.Orden = ordenNum++;
                mejorPunto.DistanciaDesdeAnteriorMetros = Math.Round(mejorDistancia, 1);
                distanciaTotalMetros += mejorDistancia;
                ordenados.Add(mejorPunto);
                restantes.Remove(mejorPunto);

                // Agregar los vértices reales de la calle a la trayectoria de la ruta
                if (mejorTrayectoria != null && mejorTrayectoria.Count > 0)
                {
                    foreach (var c in mejorTrayectoria)
                    {
                        rutaCoordinates.Add(new List<double> { c.X, c.Y });
                    }
                }
                else
                {
                    rutaCoordinates.Add(new List<double> { mejorPunto.Longitud, mejorPunto.Latitud });
                }

                currentLat = mejorPunto.Latitud;
                currentLng = mejorPunto.Longitud;
            }

            resultado.PuntosOrdenados = ordenados;
            resultado.DistanciaTotalMetros = Math.Round(distanciaTotalMetros, 1);
            resultado.CoordenadasRuta = rutaCoordinates;

            // Tiempo estimado: Velocidad media vehicular en calles urbanas (25 km/h = 416 m/min) + 5 min por atención
            var minutosViaje = (int)Math.Ceiling(distanciaTotalMetros / 416.0);
            var minutosAtencion = ordenados.Count * 5;
            resultado.TiempoEstimadoMinutos = minutosViaje + minutosAtencion;

            // Generar GeoJSON FeatureLineString estándar
            var geoJsonObj = new
            {
                type = "Feature",
                geometry = new
                {
                    type = "LineString",
                    coordinates = rutaCoordinates
                },
                properties = new
                {
                    distanciaMetros = resultado.DistanciaTotalMetros,
                    distanciaKm = resultado.DistanciaTotalKm,
                    tiempoEstimadoMinutos = resultado.TiempoEstimadoMinutos,
                    totalPuntos = ordenados.Count,
                    puntoPartida = partida.Nombre,
                    algoritmo = resultado.AlgoritmoUtilizado
                }
            };

            resultado.GeometriaGeoJson = JsonSerializer.Serialize(geoJsonObj);
            return resultado;
        }

        public static double CalcularHaversine(double lat1, double lon1, double lat2, double lon2)
        {
            const double R = 6371000.0; // Radio de la Tierra en metros
            var dLat = (lat2 - lat1) * Math.PI / 180.0;
            var dLon = (lon2 - lon1) * Math.PI / 180.0;
            var a = Math.Sin(dLat / 2) * Math.Sin(dLat / 2) +
                    Math.Cos(lat1 * Math.PI / 180.0) * Math.Cos(lat2 * Math.PI / 180.0) *
                    Math.Sin(dLon / 2) * Math.Sin(dLon / 2);
            var c = 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1 - a));
            return R * c;
        }
    }

    public sealed class RutaNoDisponibleException(string message) : Exception(message);

    /// <summary>Bidirectional street graph. Routes end at the street access, not inside parcels.</summary>
    public class RoadNetworkGraph
    {
        private readonly List<Coordinate> nodes = new();
        private readonly Dictionary<(double, double), int> nodeIds = new();
        private readonly List<List<(int Target, double Distance)>> edges = new();
        private readonly List<(int A, int B)> segments = new();
        public bool TieneVias => segments.Count > 0;

        public class PathResult
        {
            public double DistanciaMetros { get; set; } = double.PositiveInfinity;
            public List<Coordinate> Coordenadas { get; set; } = new();
        }

        private int Node(Coordinate c)
        {
            // Only merge numerical noise; do not connect nearby parallel streets.
            var key = (Math.Round(c.X, 9), Math.Round(c.Y, 9));
            if (nodeIds.TryGetValue(key, out int id)) return id;
            id = nodes.Count;
            nodes.Add(new Coordinate(c));
            edges.Add(new());
            nodeIds[key] = id;
            return id;
        }

        public void AgregarLinea(Coordinate[] coords, string streetName)
        {
            for (int i = 1; i < coords.Length; i++)
            {
                int a = Node(coords[i - 1]), b = Node(coords[i]);
                if (a == b) continue;
                double distance = Distance(nodes[a], nodes[b]);
                edges[a].Add((b, distance));
                edges[b].Add((a, distance));
                segments.Add((a, b));
            }
        }

        private static double Distance(Coordinate a, Coordinate b) =>
            DijkstraRoutingService.CalcularHaversine(a.Y, a.X, b.Y, b.X);

        private (int Segment, Coordinate Point, double Distance) Snap(double lat, double lng)
        {
            int best = -1;
            double min = double.PositiveInfinity;
            var point = new Coordinate(lng, lat);
            var projected = point;
            // Local metric projection compensates for longitude scale at this latitude.
            double scale = Math.Cos(lat * Math.PI / 180);
            for (int i = 0; i < segments.Count; i++)
            {
                var (a, b) = segments[i];
                var start = nodes[a]; var end = nodes[b];
                double dx = (end.X - start.X) * scale, dy = end.Y - start.Y;
                double t = Math.Clamp(((lng - start.X) * scale * dx + (lat - start.Y) * dy)
                    / (dx * dx + dy * dy), 0, 1);
                var candidate = new Coordinate(start.X + t * (end.X - start.X), start.Y + t * dy);
                double distance = Distance(point, candidate);
                if (distance < min) { best = i; min = distance; projected = candidate; }
            }
            return (best, projected, min);
        }

        public PathResult CalcularRutaDijkstra(double startLat, double startLng, double endLat, double endLng)
        {
            if (!double.IsFinite(startLat) || !double.IsFinite(startLng) ||
                !double.IsFinite(endLat) || !double.IsFinite(endLng) ||
                Math.Abs(startLat) > 90 || Math.Abs(endLat) > 90 ||
                Math.Abs(startLng) > 180 || Math.Abs(endLng) > 180) return new();
            var start = Snap(startLat, startLng); var end = Snap(endLat, endLng);
            // Reject points outside the dataset rather than inventing long access lines.
            if (start.Segment < 0 || end.Segment < 0 || start.Distance > 200 || end.Distance > 200)
                return new();
            if (start.Segment == end.Segment)
                return new() { DistanciaMetros = Distance(start.Point, end.Point),
                    Coordenadas = new() { start.Point, end.Point } };

            var distances = Enumerable.Repeat(double.PositiveInfinity, nodes.Count).ToArray();
            var previous = Enumerable.Repeat(-1, nodes.Count).ToArray();
            var queue = new PriorityQueue<int, double>();
            var source = segments[start.Segment]; var target = segments[end.Segment];
            foreach (int id in new[] { source.A, source.B })
            {
                distances[id] = Distance(start.Point, nodes[id]);
                queue.Enqueue(id, distances[id]);
            }
            while (queue.TryDequeue(out int current, out double cost))
            {
                if (cost > distances[current]) continue;
                foreach (var edge in edges[current])
                {
                    double next = cost + edge.Distance;
                    if (next >= distances[edge.Target]) continue;
                    distances[edge.Target] = next;
                    previous[edge.Target] = current;
                    queue.Enqueue(edge.Target, next);
                }
            }
            int finish = distances[target.A] + Distance(nodes[target.A], end.Point)
                <= distances[target.B] + Distance(nodes[target.B], end.Point) ? target.A : target.B;
            if (!double.IsFinite(distances[finish])) return new();
            var path = new List<Coordinate>();
            for (int id = finish; id >= 0; id = previous[id]) path.Add(nodes[id]);
            path.Reverse();
            path.Insert(0, start.Point);
            path.Add(end.Point);
            return new() { DistanciaMetros = distances[finish] + Distance(nodes[finish], end.Point), Coordenadas = path };
        }
    }
}
