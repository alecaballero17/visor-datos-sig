using System;
using System.Collections.Generic;

namespace Arquis.Backend.Models.Entities
{
    public class RutaTrabajo
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Titulo { get; set; } = string.Empty;
        public string Tipo { get; set; } = "Corte"; // "Corte", "Reconexion", "Inspeccion"
        public string Estado { get; set; } = "Pendiente"; // "Pendiente", "EnProgreso", "Completada", "Cancelada"
        public string Prioridad { get; set; } = "Normal"; // "Baja", "Normal", "Alta", "Urgente"
        public string OperarioAsignado { get; set; } = "Pedro";
        public string? OperarioId { get; set; }
        public string CreadoPor { get; set; } = "Gerente";
        public DateTime FechaCreacion { get; set; } = DateTime.UtcNow;
        public DateTime? FechaAsignacion { get; set; }
        public DateTime? FechaCompletado { get; set; }
        public string? Observaciones { get; set; }

        // Datos del Punto de Partida y Optimización Topológica de Ruta (Dijkstra sobre dbo.Vias)
        public double? PartidaLatitud { get; set; }
        public double? PartidaLongitud { get; set; }
        public string? PartidaNombre { get; set; }
        public double? DistanciaTotalMetros { get; set; }
        public int? TiempoEstimadoMinutos { get; set; }
        public string? GeometriaRutaGeoJson { get; set; }

        public List<PuntoRutaTrabajo> Puntos { get; set; } = new();
    }
}
