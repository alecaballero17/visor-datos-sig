using System;
using System.Text.Json.Serialization;

namespace Arquis.Backend.Models.Entities
{
    public class PuntoRutaTrabajo
    {
        public int Id { get; set; }
        public int RutaTrabajoId { get; set; }
        public int Orden { get; set; }
        public int? IdCodigoFijo { get; set; }
        public int? IdLote { get; set; }
        public string? CodigoSuministro { get; set; }
        public string? Lote { get; set; }
        public string? Titular { get; set; }
        public string? Direccion { get; set; }
        public double Latitud { get; set; }
        public double Longitud { get; set; }
        public decimal? MontoDeuda { get; set; }
        public string Estado { get; set; } = "Pendiente"; // "Pendiente", "Ejecutado", "Omitido"
        public DateTime? FechaEjecucion { get; set; }
        public string? Observaciones { get; set; }

        // Auditoría y Validación Geográfica Antifraude (RN-01 / RF-MOB-05)
        public double? LatitudEjecucion { get; set; }
        public double? LongitudEjecucion { get; set; }
        public double? DistanciaAntifraudeMetros { get; set; }
        public decimal? LecturaMedidor { get; set; }
        public string? EstadoFinal { get; set; } // "Cortado", "Reconectado", "Observado"
        public string? MotivoObservacion { get; set; }
        public string? FotosEvidenciasJson { get; set; }

        [JsonIgnore]
        public RutaTrabajo? RutaTrabajo { get; set; }
    }
}
