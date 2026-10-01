using System;
using NetTopologySuite.Geometries;
namespace Arquis.Backend.Models.Entities {
    public class CodigoFijo {
        public int IdCodigo { get; set; }
        public int? CodF_SQL { get; set; }
        public string? CodF_SIG { get; set; }
        public int? CodFijo { get; set; }
        public string? Nombre { get; set; }
        public byte Estado { get; set; } = 1;
        public bool EstadoVerificado { get; set; } = false;
        public DateTime FechaCambioEstado { get; set; } = DateTime.UtcNow;
        public int? IdLote { get; set; }
        public double? Longitud { get; set; }
        public double? Latitud { get; set; }
        public Geometry? Geom { get; set; }
        public Lote? Lote { get; set; }
    }
}
