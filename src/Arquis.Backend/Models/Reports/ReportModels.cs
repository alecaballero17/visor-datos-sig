using System;
using System.Collections.Generic;

namespace Arquis.Backend.Models.Reports
{
    public class ReportePredialDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "INFORME TÉCNICO Y DIAGNÓSTICO PREDIAL";
        public string Subtitulo { get; set; } = "Auditoría Catastral y Estado del Servicio de Agua Potable";

        // Datos Catastrales
        public int IdLote { get; set; }
        public string NumeroLote { get; set; } = string.Empty;
        public string UnidadVecinal { get; set; } = string.Empty;
        public string Manzana { get; set; } = string.Empty;
        public string Sector { get; set; } = string.Empty;
        public string? ClaveOrigen { get; set; }
        public double? Latitud { get; set; }
        public double? Longitud { get; set; }
        public string CoordenadasDisplay => Latitud.HasValue && Longitud.HasValue
            ? $"Lat: {Latitud.Value:F6}, Long: {Longitud.Value:F6}"
            : "Georreferenciado en Catastro SIG";

        // Diagnóstico del Servicio de Agua Potable
        public bool TieneAgua { get; set; }
        public string EstadoTexto => TieneAgua ? "SERVICIO ACTIVO Y REGULARIZADO" : "SIN CONEXIÓN DE AGUA REGISTRADA";
        public string? Titular { get; set; }
        public string? CodigoSuministro { get; set; }
        public string? CodigoSig { get; set; }
        public string CondicionOperativa { get; set; } = "Normal";
        public string UbicacionToma { get; set; } = "En el frente del predio";

        // Análisis Territorial y Contexto del Sector
        public int TotalLotesManzana { get; set; }
        public int LotesConAguaManzana { get; set; }
        public double PorcentajeCoberturaManzana { get; set; }
        public string ClasificacionUrbana { get; set; } = "Lote Residencial Consolidado";
        public string FactibilidadHidraulica { get; set; } = "Factible dentro de la Red Matriz Principal";

        // Conclusiones Ejecutivas para Exposición / Informe
        public string ResumenEjecutivo { get; set; } = string.Empty;
        public List<string> Recomendaciones { get; set; } = new();
    }

    public class ReporteSectorDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "DIAGNÓSTICO TERRITORIAL Y COBERTURA DEL SECTOR";
        public string UnidadVecinal { get; set; } = string.Empty;
        public string Manzana { get; set; } = string.Empty;

        // Métricas de Cobertura
        public int TotalPredios { get; set; }
        public int PrediosConServicio { get; set; }
        public int PrediosSinServicio { get; set; }
        public double PorcentajeCobertura { get; set; }
        public int PrediosEnMoraOCorte { get; set; }
        public string IndiceConsolidacion { get; set; } = "Consolidado";

        // Diagnóstico Redactado para Exposición
        public string DiagnosticoSituacional { get; set; } = string.Empty;
        public List<string> RecomendacionesTecnicas { get; set; } = new();

        // Lista de Predios Censados
        public List<PredioItemDto> Predios { get; set; } = new();
    }

    public class PredioItemDto
    {
        public int IdLote { get; set; }
        public string NumeroLote { get; set; } = string.Empty;
        public bool TieneAgua { get; set; }
        public string EstadoServicio => TieneAgua ? "Con Agua" : "Sin Servicio";
        public string? Titular { get; set; }
        public string? CodigoSuministro { get; set; }
        public string Condicion { get; set; } = "Regular";
    }

    public class BitacoraReporteDto
    {
        public long IdBitacora { get; set; }
        public DateTime Fecha { get; set; }
        public string Usuario { get; set; } = string.Empty;
        public string TipoReporte { get; set; } = string.Empty;
        public string Referencia { get; set; } = string.Empty;
        public string Accion { get; set; } = string.Empty;
        public string? Detalle { get; set; }
    }
}
