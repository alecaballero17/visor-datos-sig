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

    public class ReporteOperacionesRutasDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "INFORME OPERATIVO DE RUTAS Y ÓRDENES EN CAMPO";
        public string Subtitulo { get; set; } = "Seguimiento de Cortes, Reconexiones y Trazabilidad GPS";
        public string FiltroAplicado { get; set; } = "Todos los registros";

        public int TotalRutas { get; set; }
        public int RutasCompletadas { get; set; }
        public int RutasEnProgreso { get; set; }
        public int RutasPendientes { get; set; }
        public int TotalParadas { get; set; }
        public int ParadasCompletadas { get; set; }
        public int ParadasObservadas { get; set; }
        public int ParadasPendientes { get; set; }
        public double PorcentajeAvance { get; set; }
        public double DistanciaTotalKm { get; set; }
        public decimal MontoTotalDeudaBs { get; set; }
        public int ValidacionesGpsTotales { get; set; }
        public int ValidacionesAntifraudeOk { get; set; }

        public string ResumenEjecutivo { get; set; } = string.Empty;
        public List<string> Recomendaciones { get; set; } = new();
        public List<RutaReporteItemDto> Rutas { get; set; } = new();
        public List<ParadaAuditoriaItemDto> DetalleParadas { get; set; } = new();
    }

    public class RutaReporteItemDto
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Titulo { get; set; } = string.Empty;
        public string Tipo { get; set; } = string.Empty;
        public string Estado { get; set; } = string.Empty;
        public string Prioridad { get; set; } = string.Empty;
        public string OperarioAsignado { get; set; } = string.Empty;
        public DateTime FechaCreacion { get; set; }
        public double DistanciaKm { get; set; }
        public int TiempoEstimadoMinutos { get; set; }
        public int TotalPuntos { get; set; }
        public int PuntosCompletados { get; set; }
        public int PuntosObservados { get; set; }
        public decimal MontoDeudaTotalBs { get; set; }
    }

    public class ParadaAuditoriaItemDto
    {
        public string CodigoRuta { get; set; } = string.Empty;
        public string Operario { get; set; } = string.Empty;
        public string TipoRuta { get; set; } = string.Empty;
        public int Orden { get; set; }
        public string CodigoSuministro { get; set; } = string.Empty;
        public string Titular { get; set; } = string.Empty;
        public string Direccion { get; set; } = string.Empty;
        public string Estado { get; set; } = string.Empty;
        public string? EstadoFinal { get; set; }
        public double? DistanciaAntifraudeMetros { get; set; }
        public decimal? MontoDeuda { get; set; }
        public DateTime? FechaEjecucion { get; set; }
    }

    public class ReporteDesempenoCuadrillasDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "INFORME DE DESEMPEÑO Y PRODUCTIVIDAD DE CUADRILLAS";
        public string Subtitulo { get; set; } = "Evaluación Operativa por Cortador y Reponedor / Reconector";
        public string FiltroAplicado { get; set; } = "Todas las cuadrillas";

        public int TotalOperarios { get; set; }
        public int TotalCortadores { get; set; }
        public int TotalReconectores { get; set; }
        public int TotalRutasAsignadas { get; set; }
        public int TotalParadasAsignadas { get; set; }
        public int TotalEjecutadas { get; set; }
        public int TotalObservadas { get; set; }
        public int TotalPendientes { get; set; }
        public double CumplimientoPromedioPct { get; set; }
        public double DistanciaTotalKm { get; set; }

        public string ResumenEjecutivo { get; set; } = string.Empty;
        public List<string> Recomendaciones { get; set; } = new();
        public List<CuadrillaDesempenoItemDto> Cuadrillas { get; set; } = new();
    }

    public class CuadrillaDesempenoItemDto
    {
        public string OperarioId { get; set; } = string.Empty;
        public string NombreOperario { get; set; } = string.Empty;
        public string Rol { get; set; } = string.Empty;
        public int RutasAsignadas { get; set; }
        public int RutasCompletadas { get; set; }
        public int ParadasTotales { get; set; }
        public int Ejecutadas { get; set; }
        public int Observadas { get; set; }
        public int Pendientes { get; set; }
        public double PorcentajeCumplimiento { get; set; }
        public double DistanciaTotalKm { get; set; }
        public double? PrecisionGpsPromedioMetros { get; set; }
        public decimal MontoGestionadoBs { get; set; }
        public DateTime? UltimaActividad { get; set; }
    }

    public class ReporteEstadoSuministrosDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "AUDITORÍA DE CARTERA Y ESTADO DE SUMINISTROS DE AGUA";
        public string Subtitulo { get; set; } = "Clasificación Comercial por Estado Operativo, Mora y Reconexión";
        public string FiltroAplicado { get; set; } = "Todos los estados";

        public int TotalSuministros { get; set; }
        public int Normal { get; set; }
        public int ParaCorte { get; set; }
        public int ParaReconexion { get; set; }
        public int Cortado { get; set; }
        public int BajaParcial { get; set; }
        public int BajaTotal { get; set; }
        public int Verificados { get; set; }
        public int SinVerificar { get; set; }

        public string ResumenEjecutivo { get; set; } = string.Empty;
        public List<string> Recomendaciones { get; set; } = new();
        public List<SuministroEstadoItemDto> Suministros { get; set; } = new();
    }

    public class SuministroEstadoItemDto
    {
        public int IdCodigo { get; set; }
        public string CodigoFijo { get; set; } = string.Empty;
        public string CodigoSig { get; set; } = string.Empty;
        public string Titular { get; set; } = string.Empty;
        public int EstadoCodigo { get; set; }
        public string EstadoTexto { get; set; } = string.Empty;
        public bool EstadoVerificado { get; set; }
        public string UnidadVecinal { get; set; } = string.Empty;
        public string Manzana { get; set; } = string.Empty;
        public string NumeroLote { get; set; } = string.Empty;
        public DateTime FechaCambioEstado { get; set; }
    }

    public class ReporteEjecutivoGlobalDto
    {
        public string CodigoReporte { get; set; } = string.Empty;
        public DateTime FechaEmision { get; set; } = DateTime.UtcNow;
        public string UsuarioEmisor { get; set; } = "Usuario SIG";
        public string Titulo { get; set; } = "INFORME EJECUTIVO CONSOLIDADO DEL SISTEMA SIG MUNICIPAL";
        public string Subtitulo { get; set; } = "Inventario Territorial, Cobertura de Red Hídrica y Operaciones de Campo";

        public int TotalManzanas { get; set; }
        public int TotalLotes { get; set; }
        public int TotalVias { get; set; }
        public double LongitudRedVialKm { get; set; }
        public int TotalCodigosFijos { get; set; }
        public int LotesConServicio { get; set; }
        public int LotesSinServicio { get; set; }
        public double CoberturaGlobalPct { get; set; }

        public int Normal { get; set; }
        public int ParaCorte { get; set; }
        public int ParaReconexion { get; set; }
        public int Cortado { get; set; }
        public int BajaParcial { get; set; }
        public int BajaTotal { get; set; }

        public int TotalRutasHistoricas { get; set; }
        public int TotalIntervencionesCampo { get; set; }
        public int IntervencionesCompletadas { get; set; }
        public double TasaEfectividadCampoPct { get; set; }

        public string ResumenEjecutivo { get; set; } = string.Empty;
        public List<string> Recomendaciones { get; set; } = new();
        public List<ResumenUvItemDto> ResumenPorUv { get; set; } = new();
    }

    public class ResumenUvItemDto
    {
        public string UnidadVecinal { get; set; } = string.Empty;
        public int TotalManzanas { get; set; }
        public int TotalLotes { get; set; }
        public int LotesConAgua { get; set; }
        public double CoberturaPct { get; set; }
        public int CuentasParaCorte { get; set; }
        public int CuentasCortadas { get; set; }
        public int CuentasParaReconexion { get; set; }
    }
}
