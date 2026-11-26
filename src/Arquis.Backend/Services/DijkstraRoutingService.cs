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
        /// Optimiza la ruta utilizando Dijkstra sobre la red vial dbo.Vias.
        /// Cuando no hay punto de partida fijo, elige automáticamente el punto inicial y el orden óptimo (NN multi-inicio + 2-opt) para minimizar distancia y tiempo.
        /// </summary>
        public async Task<ResultadoOptimizacionRuta> OptimizarRutaAsync(
            PuntoPartidaDto? partida,
            List<PuntoIntervencionDto> puntos,
            bool partidaAutomatica = false)
        {
            var usarPartidaAutomatica = partidaAutomatica ||
                partida == null ||
                (Math.Abs(partida.Latitud) < 0.0001 && Math.Abs(partida.Longitud) < 0.0001);

            if (puntos == null || puntos.Count == 0)
            {
                return new ResultadoOptimizacionRuta
                {
                    Partida = partida ?? new PuntoPartidaDto { Nombre = "Inicio óptimo de ruta" },
                    PuntosOrdenados = new List<PuntoIntervencionDto>(),
                    DistanciaTotalMetros = 0,
                    TiempoEstimadoMinutos = 0,
                    GeometriaGeoJson = "{}"
                };
            }

            var graph = await ObtenerGrafoAsync();
            if (!graph.TieneVias)
                throw new RutaNoDisponibleException("No hay vías cargadas en dbo.Vias. Prepare la base de datos antes de calcular recorridos.");

            var targets = puntos.Select(p => (p.Latitud, p.Longitud)).ToList();
            var matriz = new double[puntos.Count][];
            for (int i = 0; i < puntos.Count; i++)
            {
                var row = graph.CalcularDistanciasDesde(puntos[i].Latitud, puntos[i].Longitud, targets);
                if (row == null)
                {
                    throw new RutaNoDisponibleException("No existe un recorrido conectado por las vías disponibles para todos los puntos seleccionados. Seleccione puntos de la misma red vial y a menos de 200 m de una calle.");
                }
                matriz[i] = row;
            }

            double[]? distDesdePartidaFija = null;
            if (!usarPartidaAutomatica && partida != null)
            {
                distDesdePartidaFija = graph.CalcularDistanciasDesde(partida.Latitud, partida.Longitud, targets);
                if (distDesdePartidaFija == null)
                {
                    throw new RutaNoDisponibleException("No existe un recorrido conectado por las vías disponibles desde el punto de partida. Seleccione puntos de la misma red vial y a menos de 200 m de una calle.");
                }
            }

            var ordenIndices = usarPartidaAutomatica
                ? CalcularMejorOrdenAbierto(matriz, puntos)
                : CalcularOrdenDesdePartida(distDesdePartidaFija!, matriz);

            var partidaEfectiva = usarPartidaAutomatica
                ? new PuntoPartidaDto
                {
                    Latitud = puntos[ordenIndices[0]].Latitud,
                    Longitud = puntos[ordenIndices[0]].Longitud,
                    Nombre = $"Inicio óptimo: {puntos[ordenIndices[0]].CodigoSuministro ?? puntos[ordenIndices[0]].Titular ?? "Parada 1"}"
                }
                : partida!;

            var resultado = new ResultadoOptimizacionRuta
            {
                Partida = partidaEfectiva
            };

            var rutaCoordinates = new List<List<double>>();
            var ordenados = new List<PuntoIntervencionDto>();
            double distanciaTotalMetros = 0;

            var prevLat = partidaEfectiva.Latitud;
            var prevLng = partidaEfectiva.Longitud;

            for (int step = 0; step < ordenIndices.Count; step++)
            {
                var candidato = puntos[ordenIndices[step]];
                double distSegmento = 0;
                List<Coordinate>? trayectoria = null;

                if (step > 0 || !usarPartidaAutomatica)
                {
                    var pathResult = graph.CalcularRutaDijkstra(prevLat, prevLng, candidato.Latitud, candidato.Longitud);
                    if (!double.IsFinite(pathResult.DistanciaMetros))
                    {
                        throw new RutaNoDisponibleException("No existe un recorrido conectado por las vías disponibles para todos los puntos seleccionados. Seleccione puntos de la misma red vial y a menos de 200 m de una calle.");
                    }
                    distSegmento = pathResult.DistanciaMetros;
                    trayectoria = pathResult.Coordenadas;
                }

                candidato.Orden = step + 1;
                candidato.DistanciaDesdeAnteriorMetros = Math.Round(distSegmento, 1);
                distanciaTotalMetros += distSegmento;
                ordenados.Add(candidato);

                if (trayectoria != null && trayectoria.Count > 0)
                {
                    foreach (var c in trayectoria)
                    {
                        rutaCoordinates.Add(new List<double> { c.X, c.Y });
                    }
                }
                else
                {
                    rutaCoordinates.Add(new List<double> { candidato.Longitud, candidato.Latitud });
                }

                prevLat = candidato.Latitud;
                prevLng = candidato.Longitud;
            }

            resultado.PuntosOrdenados = ordenados;
            resultado.DistanciaTotalMetros = Math.Round(distanciaTotalMetros, 1);
            resultado.CoordenadasRuta = rutaCoordinates;

            // Tiempo estimado: Velocidad media vehicular en calles urbanas (25 km/h = 416 m/min) + 5 min por atención
            var minutosViaje = (int)Math.Ceiling(distanciaTotalMetros / 416.0);
            var minutosAtencion = ordenados.Count * 5;
            resultado.TiempoEstimadoMinutos = minutosViaje + minutosAtencion;

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
                    puntoPartida = partidaEfectiva.Nombre,
                    algoritmo = usarPartidaAutomatica
                        ? "Ruta óptima automática Dijkstra + 2-Opt sobre dbo.Vias"
                        : resultado.AlgoritmoUtilizado
                }
            };

            resultado.GeometriaGeoJson = JsonSerializer.Serialize(geoJsonObj);
            return resultado;
        }

        private static List<int> CalcularOrdenDesdePartida(double[] distDesdePartida, double[][] matriz)
        {
            int n = matriz.Length;
            var restantes = new HashSet<int>(Enumerable.Range(0, n));
            var orden = new List<int>(n);

            int actual = restantes.OrderBy(i => distDesdePartida[i]).First();
            orden.Add(actual);
            restantes.Remove(actual);

            while (restantes.Count > 0)
            {
                int siguiente = -1;
                double mejor = double.MaxValue;
                foreach (var idx in restantes)
                {
                    if (matriz[actual][idx] < mejor)
                    {
                        mejor = matriz[actual][idx];
                        siguiente = idx;
                    }
                }
                orden.Add(siguiente);
                restantes.Remove(siguiente);
                actual = siguiente;
            }

            Aplicar2Opt(orden, matriz, fixedStartCost: i => distDesdePartida[i]);
            return orden;
        }

        private static List<int> CalcularMejorOrdenAbierto(double[][] matriz, List<PuntoIntervencionDto> puntos)
        {
            int n = matriz.Length;
            if (n <= 1) return Enumerable.Range(0, n).ToList();

            IEnumerable<int> candidatosInicio;
            if (n <= 60)
            {
                candidatosInicio = Enumerable.Range(0, n);
            }
            else
            {
                var set = new HashSet<int>
                {
                    Enumerable.Range(0, n).OrderBy(i => puntos[i].Latitud).First(),
                    Enumerable.Range(0, n).OrderByDescending(i => puntos[i].Latitud).First(),
                    Enumerable.Range(0, n).OrderBy(i => puntos[i].Longitud).First(),
                    Enumerable.Range(0, n).OrderByDescending(i => puntos[i].Longitud).First()
                };
                int step = Math.Max(1, n / 20);
                for (int i = 0; i < n && set.Count < 24; i += step) set.Add(i);
                candidatosInicio = set;
            }

            List<int>? mejorOrden = null;
            double mejorCosto = double.MaxValue;

            foreach (var inicio in candidatosInicio)
            {
                var orden = new List<int>(n) { inicio };
                var usados = new bool[n];
                usados[inicio] = true;
                int actual = inicio;
                double costo = 0;

                for (int k = 1; k < n; k++)
                {
                    int sig = -1;
                    double minD = double.MaxValue;
                    for (int j = 0; j < n; j++)
                    {
                        if (!usados[j] && matriz[actual][j] < minD)
                        {
                            minD = matriz[actual][j];
                            sig = j;
                        }
                    }
                    orden.Add(sig);
                    usados[sig] = true;
                    costo += minD;
                    actual = sig;
                }

                Aplicar2Opt(orden, matriz, fixedStartCost: null);
                costo = CalcularCostoAbierto(orden, matriz);

                if (costo < mejorCosto)
                {
                    mejorCosto = costo;
                    mejorOrden = orden;
                }
            }

            return mejorOrden!;
        }

        private static double CalcularCostoAbierto(List<int> orden, double[][] matriz, Func<int, double>? fixedStartCost = null)
        {
            double total = fixedStartCost != null && orden.Count > 0 ? fixedStartCost(orden[0]) : 0;
            for (int i = 0; i < orden.Count - 1; i++)
            {
                total += matriz[orden[i]][orden[i + 1]];
            }
            return total;
        }

        private static void Aplicar2Opt(List<int> orden, double[][] matriz, Func<int, double>? fixedStartCost)
        {
            int n = orden.Count;
            if (n < 3) return;

            bool mejorado = true;
            int guard = 0;
            int maxPasses = n * 2;
            while (mejorado && guard++ < maxPasses)
            {
                mejorado = false;
                double actualTotal = CalcularCostoAbierto(orden, matriz, fixedStartCost);

                for (int i = 0; i < n - 1; i++)
                {
                    for (int j = i + 1; j < n; j++)
                    {
                        orden.Reverse(i, j - i + 1);
                        double nuevoTotal = CalcularCostoAbierto(orden, matriz, fixedStartCost);
                        if (nuevoTotal < actualTotal - 0.01)
                        {
                            actualTotal = nuevoTotal;
                            mejorado = true;
                        }
                        else
                        {
                            orden.Reverse(i, j - i + 1);
                        }
                    }
                }
            }
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

        public double[]? CalcularDistanciasDesde(
            double startLat,
            double startLng,
            IReadOnlyList<(double Lat, double Lng)> targets)
        {
            if (!double.IsFinite(startLat) || !double.IsFinite(startLng) ||
                Math.Abs(startLat) > 90 || Math.Abs(startLng) > 180)
                return null;

            var start = Snap(startLat, startLng);
            if (start.Segment < 0 || start.Distance > 200)
                return null;

            var snappedTargets = new (int Segment, Coordinate Point, double Distance)[targets.Count];
            var neededVertices = new HashSet<int>();

            for (int k = 0; k < targets.Count; k++)
            {
                var (tLat, tLng) = targets[k];
                if (!double.IsFinite(tLat) || !double.IsFinite(tLng) ||
                    Math.Abs(tLat) > 90 || Math.Abs(tLng) > 180)
                    return null;

                var end = Snap(tLat, tLng);
                if (end.Segment < 0 || end.Distance > 200)
                    return null;

                snappedTargets[k] = end;
                if (end.Segment != start.Segment)
                {
                    var tSeg = segments[end.Segment];
                    neededVertices.Add(tSeg.A);
                    neededVertices.Add(tSeg.B);
                }
            }

            var distances = Enumerable.Repeat(double.PositiveInfinity, nodes.Count).ToArray();
            if (neededVertices.Count > 0)
            {
                var queue = new PriorityQueue<int, double>();
                var source = segments[start.Segment];
                foreach (int id in new[] { source.A, source.B })
                {
                    distances[id] = Distance(start.Point, nodes[id]);
                    queue.Enqueue(id, distances[id]);
                }

                int remainingNeeded = neededVertices.Count;
                while (queue.TryDequeue(out int current, out double cost))
                {
                    if (cost > distances[current]) continue;
                    if (neededVertices.Remove(current))
                    {
                        remainingNeeded--;
                        if (remainingNeeded == 0) break;
                    }
                    foreach (var edge in edges[current])
                    {
                        double next = cost + edge.Distance;
                        if (next >= distances[edge.Target]) continue;
                        distances[edge.Target] = next;
                        queue.Enqueue(edge.Target, next);
                    }
                }
            }

            var result = new double[targets.Count];
            for (int k = 0; k < targets.Count; k++)
            {
                var end = snappedTargets[k];
                if (start.Segment == end.Segment)
                {
                    result[k] = Distance(start.Point, end.Point);
                }
                else
                {
                    var tSeg = segments[end.Segment];
                    double dA = distances[tSeg.A] + Distance(nodes[tSeg.A], end.Point);
                    double dB = distances[tSeg.B] + Distance(nodes[tSeg.B], end.Point);
                    double d = Math.Min(dA, dB);
                    if (!double.IsFinite(d)) return null;
                    result[k] = d;
                }
            }
            return result;
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
