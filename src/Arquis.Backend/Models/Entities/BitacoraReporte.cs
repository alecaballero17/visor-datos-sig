using System;

namespace Arquis.Backend.Models.Entities
{
    public class BitacoraReporte
    {
        public long IdBitacora { get; set; }
        public DateTime Fecha { get; set; } = DateTime.UtcNow;
        public string Usuario { get; set; } = "Usuario SIG";
        public string TipoReporte { get; set; } = "Predial";
        public string Referencia { get; set; } = string.Empty;
        public string Accion { get; set; } = "Emisión de Informe";
        public string? Detalle { get; set; }
        public string? Ip { get; set; }
    }
}
