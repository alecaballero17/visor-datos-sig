using System.Collections.Generic;
using NetTopologySuite.Geometries;
namespace Arquis.Backend.Models.Entities {
    public class Manzana {
        public int IdManzana { get; set; }
        public int? IdOrigen { get; set; }
        public string? UV_MZA { get; set; }
        public string? UV { get; set; }
        public string? MZA { get; set; }
        public Geometry? Geom { get; set; }
        public ICollection<Lote> Lotes { get; set; } = new List<Lote>();
    }
}
