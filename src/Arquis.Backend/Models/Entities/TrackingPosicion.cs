using System;

namespace Arquis.Backend.Models.Entities
{
    public class TrackingPosicion
    {
        public long Id { get; set; }
        public string OperarioId { get; set; } = string.Empty;
        public string NombreOperario { get; set; } = string.Empty;
        public string Rol { get; set; } = "Cortador";
        public double Latitud { get; set; }
        public double Longitud { get; set; }
        public double Rumbo { get; set; }
        public double Velocidad { get; set; }
        public int Bateria { get; set; } = 100;
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
        public bool EnLinea { get; set; } = true;
    }
}
