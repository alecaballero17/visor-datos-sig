using System;
namespace Arquis.Backend.Models.Entities {
    public class BitacoraMigracion {
        public long IdMigracion { get; set; }
        public DateTime FechaInicio { get; set; } = DateTime.UtcNow;
        public DateTime? FechaFin { get; set; }
        public string Usuario { get; set; } = null!;
        public string Capa { get; set; } = null!;
        public string Archivo { get; set; } = null!;
        public string TablaDestino { get; set; } = null!;
        public string Modalidad { get; set; } = null!;
        public int Procesados { get; set; } = 0;
        public int Exitosos { get; set; } = 0;
        public int Omitidos { get; set; } = 0;
        public int Fallidos { get; set; } = 0;
        public string Estado { get; set; } = "Iniciada";
        public string? Detalle { get; set; }
    }
}
