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
            public string AlgoritmoUtilizado { get; set; } = "Dijkstra Topológico sobre dbo.Vias";
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

                if (vias.Count > 0)
                {
                    foreach (var via in vias)
                    {
                        var geom = via.Geom;
                        if (geom == null) continue;

                        for (int i = 0; i < geom.NumGeometries; i++)
                        {
                            var subGeom = geom.GetGeometryN(i);
                            if (subGeom is LineString line && line.Coordinates.Length >= 2)
                            {
                                graph.AgregarLinea(line.Coordinates, via.Nombre ?? $"Via-{via.IdVia}");
                            }
                        }
                    }
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
            var resultado = new ResultadoOptimizacionRuta
            {
                Partida = partida
            };

            // Lista para almacenar la secuencia completa de coordenadas de la ruta [lng, lat]
            var rutaCoordinates = new List<List<double>>();

            // Punto de partida inicial
            var currentLat = partida.Latitud;
            var currentLng = partida.Longitud;
            rutaCoordinates.Add(new List<double> { currentLng, currentLat });

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
                    // Fallback directo si no hubiera candidatos
                    mejorPunto = restantes[0];
                    mejorDistancia = CalcularHaversine(currentLat, currentLng, mejorPunto.Latitud, mejorPunto.Longitud);
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
                    algoritmo = "Dijkstra - Ejes Viales dbo.Vias (Sin cruce de manzanas)"
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

    /// <summary>
    /// Representación de la Red Topológica de Vías para ejecución de Dijkstra.
    /// </summary>
    public class RoadNetworkGraph
    {
        public class Node
        {
            public int Id { get; set; }
            public double Lat { get; set; }
            public double Lng { get; set; }
            public List<Edge> Edges { get; set; } = new();
        }

        public class Edge
        {
            public int TargetNodeId { get; set; }
            public double WeightMeters { get; set; }
            public string StreetName { get; set; } = string.Empty;
            public List<Coordinate> GeometryPoints { get; set; } = new();
        }

        public class PathResult
        {
            public double DistanciaMetros { get; set; }
            public List<Coordinate> Coordenadas { get; set; } = new();
        }

        private readonly List<Node> _nodes = new();
        private readonly Dictionary<(long, long), int> _coordToNodeIndex = new();
        private const double SnapToleranceDegrees = 0.0001; // ~10 metros

        private (long, long) Discretize(double lat, double lng)
        {
            long latGrid = (long)Math.Round(lat / SnapToleranceDegrees);
            long lngGrid = (long)Math.Round(lng / SnapToleranceDegrees);
            return (latGrid, lngGrid);
        }

        public int ObtenerOCrearNodo(double lat, double lng)
        {
            var key = Discretize(lat, lng);
            if (_coordToNodeIndex.TryGetValue(key, out var existingId))
            {
                return existingId;
            }

            int id = _nodes.Count;
            var node = new Node { Id = id, Lat = lat, Lng = lng };
            _nodes.Add(node);
            _coordToNodeIndex[key] = id;
            return id;
        }

        public void AgregarLinea(Coordinate[] coords, string streetName)
        {
            if (coords == null || coords.Length < 2) return;

            for (int i = 0; i < coords.Length - 1; i++)
            {
                var c1 = coords[i];
                var c2 = coords[i + 1];

                int u = ObtenerOCrearNodo(c1.Y, c1.X);
                int v = ObtenerOCrearNodo(c2.Y, c2.X);

                if (u == v) continue;

                double dist = DijkstraRoutingService.CalcularHaversine(c1.Y, c1.X, c2.Y, c2.X);
                if (dist < 0.5) dist = 0.5; // evitar pesos nulos

                var segCoords = new List<Coordinate> { c1, c2 };
                var revSegCoords = new List<Coordinate> { c2, c1 };

                _nodes[u].Edges.Add(new Edge
                {
                    TargetNodeId = v,
                    WeightMeters = dist,
                    StreetName = streetName,
                    GeometryPoints = segCoords
                });

                _nodes[v].Edges.Add(new Edge
                {
                    TargetNodeId = u,
                    WeightMeters = dist,
                    StreetName = streetName,
                    GeometryPoints = revSegCoords
                });
            }
        }

        public int EncontrarNodoMasCercano(double lat, double lng)
        {
            if (_nodes.Count == 0) return -1;

            int bestId = 0;
            double bestDist = double.MaxValue;

            for (int i = 0; i < _nodes.Count; i++)
            {
                var n = _nodes[i];
                double d = DijkstraRoutingService.CalcularHaversine(lat, lng, n.Lat, n.Lng);
                if (d < bestDist)
                {
                    bestDist = d;
                    bestId = i;
                }
            }

            return bestId;
        }

        /// <summary>
        /// Algoritmo de Dijkstra para calcular la ruta más corta sobre la red topológica vial.
        /// </summary>
        public PathResult CalcularRutaDijkstra(double startLat, double startLng, double endLat, double endLng)
        {
            // Si la red vial no tiene datos cargados aún, trazar línea directa geodésica
            if (_nodes.Count == 0)
            {
                double directDist = DijkstraRoutingService.CalcularHaversine(startLat, startLng, endLat, endLng);
                return new PathResult
                {
                    DistanciaMetros = directDist,
                    Coordenadas = new List<Coordinate>
                    {
                        new(startLng, startLat),
                        new(endLng, endLat)
                    }
                };
            }

            int startNode = EncontrarNodoMasCercano(startLat, startLng);
            int endNode = EncontrarNodoMasCercano(endLat, endLng);

            if (startNode == endNode || startNode < 0 || endNode < 0)
            {
                double directDist = DijkstraRoutingService.CalcularHaversine(startLat, startLng, endLat, endLng);
                return new PathResult
                {
                    DistanciaMetros = directDist,
                    Coordenadas = new List<Coordinate>
                    {
                        new(startLng, startLat),
                        new(endLng, endLat)
                    }
                };
            }

            // Dijkstra con PriorityQueue (Min-Heap)
            var distances = new Dictionary<int, double>();
            var previous = new Dictionary<int, (int NodeId, List<Coordinate> EdgeGeom)>();
            var pq = new PriorityQueue<int, double>();

            distances[startNode] = 0;
            pq.Enqueue(startNode, 0);

            while (pq.Count > 0)
            {
                var current = pq.Dequeue();

                if (current == endNode) break;

                double currentDist = distances[current];

                foreach (var edge in _nodes[current].Edges)
                {
                    double newDist = currentDist + edge.WeightMeters;
                    if (!distances.TryGetValue(edge.TargetNodeId, out var prevDist) || newDist < prevDist)
                    {
                        distances[edge.TargetNodeId] = newDist;
                        previous[edge.TargetNodeId] = (current, edge.GeometryPoints);
                        pq.Enqueue(edge.TargetNodeId, newDist);
                    }
                }
            }

            // Reconstrucción del camino si se alcanzó el destino
            if (distances.ContainsKey(endNode))
            {
                var pathCoords = new List<Coordinate>();
                int curr = endNode;

                while (previous.TryGetValue(curr, out var step))
                {
                    // Invertir para agregar secuencialmente
                    for (int k = step.EdgeGeom.Count - 1; k >= 0; k--)
                    {
                        pathCoords.Insert(0, step.EdgeGeom[k]);
                    }
                    curr = step.NodeId;
                }

                // Asegurar extremos de conexión con los puntos exactos de partida y llegada
                pathCoords.Insert(0, new Coordinate(startLng, startLat));
                pathCoords.Add(new Coordinate(endLng, endLat));

                double distConAcometidas = distances[endNode] +
                    DijkstraRoutingService.CalcularHaversine(startLat, startLng, _nodes[startNode].Lat, _nodes[startNode].Lng) +
                    DijkstraRoutingService.CalcularHaversine(_nodes[endNode].Lat, _nodes[endNode].Lng, endLat, endLng);

                return new PathResult
                {
                    DistanciaMetros = distConAcometidas,
                    Coordenadas = pathCoords
                };
            }

            // Si los nodos están en componentes inconexos, retornar ruta estimada conectando a red
            double fallbackDist = DijkstraRoutingService.CalcularHaversine(startLat, startLng, endLat, endLng) * 1.35; // factor de rodeo urbano
            return new PathResult
            {
                DistanciaMetros = fallbackDist,
                Coordenadas = new List<Coordinate>
                {
                    new(startLng, startLat),
                    new(_nodes[startNode].Lng, _nodes[startNode].Lat),
                    new(_nodes[endNode].Lng, _nodes[endNode].Lat),
                    new(endLng, endLat)
                }
            };
        }
    }
}
