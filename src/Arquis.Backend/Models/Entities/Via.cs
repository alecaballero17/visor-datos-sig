using NetTopologySuite.Geometries;
namespace Arquis.Backend.Models.Entities {
    public class Via {
        public int IdVia { get; set; }
        public int? OBJECTID { get; set; }
        public string? Nombre { get; set; }
        public string? TipoVia { get; set; }
        public string? OSMID { get; set; }
        public Geometry? Geom { get; set; }
    }
}
