using System;
namespace Arquis.Backend.Models.Entities {
    public class BitacoraAcceso {
        public long IdBitacora { get; set; }
        public DateTime Fecha { get; set; } = DateTime.UtcNow;
        public string Login { get; set; } = null!;
        public bool Exitoso { get; set; }
        public string? Ip { get; set; }
        public string? Detalle { get; set; }
    }
}
