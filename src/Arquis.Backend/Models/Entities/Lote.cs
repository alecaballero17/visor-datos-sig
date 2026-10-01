using System.Collections.Generic;
using NetTopologySuite.Geometries;
namespace Arquis.Backend.Models.Entities {
    public class Lote {
        public int IdLote { get; set; }
        public int? IdOrigen { get; set; }
        public string? NroLote { get; set; }
        public int? IdManzana { get; set; }
        public Geometry? Geom { get; set; }
        public Manzana? Manzana { get; set; }
        public ICollection<CodigoFijo> CodigosFijos { get; set; } = new List<CodigoFijo>();
    }
}
