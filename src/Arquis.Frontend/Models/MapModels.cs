using System.Text.Json.Serialization;

namespace Arquis.Frontend.Models;

public sealed class SearchResultItem
{
    [JsonPropertyName("layer")]
    public string Layer { get; set; } = string.Empty;

    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("label")]
    public string Label { get; set; } = string.Empty;

    [JsonPropertyName("properties")]
    public Dictionary<string, object?>? Properties { get; set; }

    [JsonPropertyName("bbox")]
    public double[]? Bbox { get; set; }

    // Helper semántico para interfaz tipo Google Maps
    public string CategoryName => Layer.ToLowerInvariant() switch
    {
        "lotes" => "Predio / Lote",
        "codigosfijos" => "Conexión de Agua",
        "manzanas" => "Manzana Urbana",
        "vias" => "Calle / Vía",
        _ => "Elemento"
    };

    public string CategoryIcon => Layer.ToLowerInvariant() switch
    {
        "lotes" => "bi-house-door-fill",
        "codigosfijos" => "bi-droplet-fill",
        "manzanas" => "bi-grid-3x3-gap-fill",
        "vias" => "bi-signpost-split-fill",
        _ => "bi-geo-alt-fill"
    };

    public string CategoryBadgeColor => Layer.ToLowerInvariant() switch
    {
        "lotes" => "bg-primary-subtle text-primary border-primary-subtle",
        "codigosfijos" => "bg-warning-subtle text-warning-emphasis border-warning-subtle",
        "manzanas" => "bg-danger-subtle text-danger border-danger-subtle",
        "vias" => "bg-secondary-subtle text-secondary border-secondary-subtle",
        _ => "bg-light text-dark"
    };
}

public sealed class FichaAguaResponse
{
    [JsonPropertyName("tieneAgua")]
    public bool TieneAgua { get; set; }

    [JsonPropertyName("criterioDisponibilidad")]
    public string? CriterioDisponibilidad { get; set; }

    [JsonPropertyName("fuente")]
    public string? Fuente { get; set; }

    [JsonPropertyName("registros")]
    public List<RegistroAgua>? Registros { get; set; }

    [JsonPropertyName("datosNoDisponibles")]
    public List<string>? DatosNoDisponibles { get; set; }
}

public sealed class RegistroAgua
{
    [JsonPropertyName("idCodigo")]
    public int IdCodigo { get; set; }

    [JsonPropertyName("codigoFijo")]
    public object? CodigoFijo { get; set; }

    [JsonPropertyName("codigoSig")]
    public string? CodigoSig { get; set; }

    [JsonPropertyName("nombreRegistrado")]
    public string? NombreRegistrado { get; set; }

    [JsonPropertyName("idLote")]
    public object? IdLote { get; set; }

    [JsonPropertyName("numeroLote")]
    public object? NumeroLote { get; set; }

    [JsonPropertyName("uv")]
    public object? Uv { get; set; }

    [JsonPropertyName("manzana")]
    public object? Manzana { get; set; }

    [JsonPropertyName("longitud")]
    public double? Longitud { get; set; }

    [JsonPropertyName("latitud")]
    public double? Latitud { get; set; }

    [JsonPropertyName("estadoVerificado")]
    public bool EstadoVerificado { get; set; }

    [JsonPropertyName("estadoServicio")]
    public int? EstadoServicio { get; set; }

    public string EstadoServicioTexto => EstadoServicio switch
    {
        1 => "Normal / Suministro Activo",
        2 => "Notificado para Corte",
        3 => "Servicio Suspendido / Cortado",
        4 => "Baja Parcial de Conexión",
        5 => "Baja Total de Conexión",
        _ => EstadoVerificado ? "Verificado en Campo" : "Sin Verificación de Estado"
    };

    public string EstadoServicioBadgeClass => EstadoServicio switch
    {
        1 => "badge bg-success text-white",
        2 => "badge bg-warning text-dark",
        3 => "badge bg-danger text-white",
        4 or 5 => "badge bg-secondary text-white",
        _ => "badge bg-light text-secondary border"
    };
}

public sealed class FeatureDetailResponse
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("properties")]
    public Dictionary<string, object?> Properties { get; set; } = new();

    [JsonPropertyName("bbox")]
    public double[]? Bbox { get; set; }
}

public enum WaterFilterMode
{
    Todos,
    SoloConAgua,
    SoloSinAgua
}

public sealed class ReportePredialModel
{
    [JsonPropertyName("codigoReporte")]
    public string CodigoReporte { get; set; } = string.Empty;

    [JsonPropertyName("fechaEmision")]
    public DateTime FechaEmision { get; set; }

    [JsonPropertyName("usuarioEmisor")]
    public string UsuarioEmisor { get; set; } = "Usuario SIG";

    [JsonPropertyName("titulo")]
    public string Titulo { get; set; } = string.Empty;

    [JsonPropertyName("subtitulo")]
    public string Subtitulo { get; set; } = string.Empty;

    [JsonPropertyName("idLote")]
    public int IdLote { get; set; }

    [JsonPropertyName("numeroLote")]
    public string NumeroLote { get; set; } = string.Empty;

    [JsonPropertyName("unidadVecinal")]
    public string UnidadVecinal { get; set; } = string.Empty;

    [JsonPropertyName("manzana")]
    public string Manzana { get; set; } = string.Empty;

    [JsonPropertyName("sector")]
    public string Sector { get; set; } = string.Empty;

    [JsonPropertyName("claveOrigen")]
    public string? ClaveOrigen { get; set; }

    [JsonPropertyName("latitud")]
    public double? Latitud { get; set; }

    [JsonPropertyName("longitud")]
    public double? Longitud { get; set; }

    [JsonPropertyName("coordenadasDisplay")]
    public string CoordenadasDisplay { get; set; } = string.Empty;

    [JsonPropertyName("tieneAgua")]
    public bool TieneAgua { get; set; }

    [JsonPropertyName("estadoTexto")]
    public string EstadoTexto { get; set; } = string.Empty;

    [JsonPropertyName("titular")]
    public string? Titular { get; set; }

    [JsonPropertyName("codigoSuministro")]
    public string? CodigoSuministro { get; set; }

    [JsonPropertyName("codigoSig")]
    public string? CodigoSig { get; set; }

    [JsonPropertyName("condicionOperativa")]
    public string CondicionOperativa { get; set; } = string.Empty;

    [JsonPropertyName("ubicacionToma")]
    public string UbicacionToma { get; set; } = string.Empty;

    [JsonPropertyName("totalLotesManzana")]
    public int TotalLotesManzana { get; set; }

    [JsonPropertyName("lotesConAguaManzana")]
    public int LotesConAguaManzana { get; set; }

    [JsonPropertyName("porcentajeCoberturaManzana")]
    public double PorcentajeCoberturaManzana { get; set; }

    [JsonPropertyName("clasificacionUrbana")]
    public string ClasificacionUrbana { get; set; } = string.Empty;

    [JsonPropertyName("factibilidadHidraulica")]
    public string FactibilidadHidraulica { get; set; } = string.Empty;

    [JsonPropertyName("resumenEjecutivo")]
    public string ResumenEjecutivo { get; set; } = string.Empty;

    [JsonPropertyName("recomendaciones")]
    public List<string> Recomendaciones { get; set; } = new();
}

public sealed class ReporteSectorModel
{
    [JsonPropertyName("codigoReporte")]
    public string CodigoReporte { get; set; } = string.Empty;

    [JsonPropertyName("fechaEmision")]
    public DateTime FechaEmision { get; set; }

    [JsonPropertyName("usuarioEmisor")]
    public string UsuarioEmisor { get; set; } = "Usuario SIG";

    [JsonPropertyName("titulo")]
    public string Titulo { get; set; } = string.Empty;

    [JsonPropertyName("unidadVecinal")]
    public string UnidadVecinal { get; set; } = string.Empty;

    [JsonPropertyName("manzana")]
    public string Manzana { get; set; } = string.Empty;

    [JsonPropertyName("totalPredios")]
    public int TotalPredios { get; set; }

    [JsonPropertyName("prediosConServicio")]
    public int PrediosConServicio { get; set; }

    [JsonPropertyName("prediosSinServicio")]
    public int PrediosSinServicio { get; set; }

    [JsonPropertyName("porcentajeCobertura")]
    public double PorcentajeCobertura { get; set; }

    [JsonPropertyName("prediosEnMoraOCorte")]
    public int PrediosEnMoraOCorte { get; set; }

    [JsonPropertyName("indiceConsolidacion")]
    public string IndiceConsolidacion { get; set; } = string.Empty;

    [JsonPropertyName("diagnosticoSituacional")]
    public string DiagnosticoSituacional { get; set; } = string.Empty;

    [JsonPropertyName("recomendacionesTecnicas")]
    public List<string> RecomendacionesTecnicas { get; set; } = new();

    [JsonPropertyName("predios")]
    public List<PredioReporteItemModel> Predios { get; set; } = new();
}

public sealed class PredioReporteItemModel
{
    [JsonPropertyName("idLote")]
    public int IdLote { get; set; }

    [JsonPropertyName("numeroLote")]
    public string NumeroLote { get; set; } = string.Empty;

    [JsonPropertyName("tieneAgua")]
    public bool TieneAgua { get; set; }

    [JsonPropertyName("estadoServicio")]
    public string EstadoServicio { get; set; } = string.Empty;

    [JsonPropertyName("titular")]
    public string? Titular { get; set; }

    [JsonPropertyName("codigoSuministro")]
    public string? CodigoSuministro { get; set; }

    [JsonPropertyName("condicion")]
    public string Condicion { get; set; } = string.Empty;
}

public sealed class BitacoraItemModel
{
    [JsonPropertyName("idBitacora")]
    public long IdBitacora { get; set; }

    [JsonPropertyName("fecha")]
    public DateTime Fecha { get; set; }

    [JsonPropertyName("usuario")]
    public string Usuario { get; set; } = string.Empty;

    [JsonPropertyName("tipoReporte")]
    public string TipoReporte { get; set; } = string.Empty;

    [JsonPropertyName("referencia")]
    public string Referencia { get; set; } = string.Empty;

    [JsonPropertyName("accion")]
    public string Accion { get; set; } = string.Empty;

    [JsonPropertyName("detalle")]
    public string? Detalle { get; set; }
}

public sealed class ReporteOperacionesRutasModel
{
    [JsonPropertyName("codigoReporte")] public string CodigoReporte { get; set; } = string.Empty;
    [JsonPropertyName("fechaEmision")] public DateTime FechaEmision { get; set; }
    [JsonPropertyName("usuarioEmisor")] public string UsuarioEmisor { get; set; } = "Usuario SIG";
    [JsonPropertyName("titulo")] public string Titulo { get; set; } = string.Empty;
    [JsonPropertyName("subtitulo")] public string Subtitulo { get; set; } = string.Empty;
    [JsonPropertyName("filtroAplicado")] public string FiltroAplicado { get; set; } = string.Empty;
    [JsonPropertyName("totalRutas")] public int TotalRutas { get; set; }
    [JsonPropertyName("rutasCompletadas")] public int RutasCompletadas { get; set; }
    [JsonPropertyName("rutasEnProgreso")] public int RutasEnProgreso { get; set; }
    [JsonPropertyName("rutasPendientes")] public int RutasPendientes { get; set; }
    [JsonPropertyName("totalParadas")] public int TotalParadas { get; set; }
    [JsonPropertyName("paradasCompletadas")] public int ParadasCompletadas { get; set; }
    [JsonPropertyName("paradasObservadas")] public int ParadasObservadas { get; set; }
    [JsonPropertyName("paradasPendientes")] public int ParadasPendientes { get; set; }
    [JsonPropertyName("porcentajeAvance")] public double PorcentajeAvance { get; set; }
    [JsonPropertyName("distanciaTotalKm")] public double DistanciaTotalKm { get; set; }
    [JsonPropertyName("montoTotalDeudaBs")] public decimal MontoTotalDeudaBs { get; set; }
    [JsonPropertyName("validacionesGpsTotales")] public int ValidacionesGpsTotales { get; set; }
    [JsonPropertyName("validacionesAntifraudeOk")] public int ValidacionesAntifraudeOk { get; set; }
    [JsonPropertyName("resumenEjecutivo")] public string ResumenEjecutivo { get; set; } = string.Empty;
    [JsonPropertyName("recomendaciones")] public List<string> Recomendaciones { get; set; } = new();
    [JsonPropertyName("rutas")] public List<RutaReporteItemModel> Rutas { get; set; } = new();
    [JsonPropertyName("detalleParadas")] public List<ParadaAuditoriaItemModel> DetalleParadas { get; set; } = new();
}

public sealed class RutaReporteItemModel
{
    [JsonPropertyName("id")] public int Id { get; set; }
    [JsonPropertyName("codigo")] public string Codigo { get; set; } = string.Empty;
    [JsonPropertyName("titulo")] public string Titulo { get; set; } = string.Empty;
    [JsonPropertyName("tipo")] public string Tipo { get; set; } = string.Empty;
    [JsonPropertyName("estado")] public string Estado { get; set; } = string.Empty;
    [JsonPropertyName("prioridad")] public string Prioridad { get; set; } = string.Empty;
    [JsonPropertyName("operarioAsignado")] public string OperarioAsignado { get; set; } = string.Empty;
    [JsonPropertyName("fechaCreacion")] public DateTime FechaCreacion { get; set; }
    [JsonPropertyName("distanciaKm")] public double DistanciaKm { get; set; }
    [JsonPropertyName("tiempoEstimadoMinutos")] public int TiempoEstimadoMinutos { get; set; }
    [JsonPropertyName("totalPuntos")] public int TotalPuntos { get; set; }
    [JsonPropertyName("puntosCompletados")] public int PuntosCompletados { get; set; }
    [JsonPropertyName("puntosObservados")] public int PuntosObservados { get; set; }
    [JsonPropertyName("montoDeudaTotalBs")] public decimal MontoDeudaTotalBs { get; set; }
}

public sealed class ParadaAuditoriaItemModel
{
    [JsonPropertyName("codigoRuta")] public string CodigoRuta { get; set; } = string.Empty;
    [JsonPropertyName("operario")] public string Operario { get; set; } = string.Empty;
    [JsonPropertyName("tipoRuta")] public string TipoRuta { get; set; } = string.Empty;
    [JsonPropertyName("orden")] public int Orden { get; set; }
    [JsonPropertyName("codigoSuministro")] public string CodigoSuministro { get; set; } = string.Empty;
    [JsonPropertyName("titular")] public string Titular { get; set; } = string.Empty;
    [JsonPropertyName("direccion")] public string Direccion { get; set; } = string.Empty;
    [JsonPropertyName("estado")] public string Estado { get; set; } = string.Empty;
    [JsonPropertyName("estadoFinal")] public string? EstadoFinal { get; set; }
    [JsonPropertyName("distanciaAntifraudeMetros")] public double? DistanciaAntifraudeMetros { get; set; }
    [JsonPropertyName("montoDeuda")] public decimal? MontoDeuda { get; set; }
    [JsonPropertyName("fechaEjecucion")] public DateTime? FechaEjecucion { get; set; }
}

public sealed class ReporteDesempenoCuadrillasModel
{
    [JsonPropertyName("codigoReporte")] public string CodigoReporte { get; set; } = string.Empty;
    [JsonPropertyName("fechaEmision")] public DateTime FechaEmision { get; set; }
    [JsonPropertyName("usuarioEmisor")] public string UsuarioEmisor { get; set; } = "Usuario SIG";
    [JsonPropertyName("titulo")] public string Titulo { get; set; } = string.Empty;
    [JsonPropertyName("subtitulo")] public string Subtitulo { get; set; } = string.Empty;
    [JsonPropertyName("filtroAplicado")] public string FiltroAplicado { get; set; } = string.Empty;
    [JsonPropertyName("totalOperarios")] public int TotalOperarios { get; set; }
    [JsonPropertyName("totalCortadores")] public int TotalCortadores { get; set; }
    [JsonPropertyName("totalReconectores")] public int TotalReconectores { get; set; }
    [JsonPropertyName("totalRutasAsignadas")] public int TotalRutasAsignadas { get; set; }
    [JsonPropertyName("totalParadasAsignadas")] public int TotalParadasAsignadas { get; set; }
    [JsonPropertyName("totalEjecutadas")] public int TotalEjecutadas { get; set; }
    [JsonPropertyName("totalObservadas")] public int TotalObservadas { get; set; }
    [JsonPropertyName("totalPendientes")] public int TotalPendientes { get; set; }
    [JsonPropertyName("cumplimientoPromedioPct")] public double CumplimientoPromedioPct { get; set; }
    [JsonPropertyName("distanciaTotalKm")] public double DistanciaTotalKm { get; set; }
    [JsonPropertyName("resumenEjecutivo")] public string ResumenEjecutivo { get; set; } = string.Empty;
    [JsonPropertyName("recomendaciones")] public List<string> Recomendaciones { get; set; } = new();
    [JsonPropertyName("cuadrillas")] public List<CuadrillaDesempenoItemModel> Cuadrillas { get; set; } = new();
}

public sealed class CuadrillaDesempenoItemModel
{
    [JsonPropertyName("operarioId")] public string OperarioId { get; set; } = string.Empty;
    [JsonPropertyName("nombreOperario")] public string NombreOperario { get; set; } = string.Empty;
    [JsonPropertyName("rol")] public string Rol { get; set; } = string.Empty;
    [JsonPropertyName("rutasAsignadas")] public int RutasAsignadas { get; set; }
    [JsonPropertyName("rutasCompletadas")] public int RutasCompletadas { get; set; }
    [JsonPropertyName("paradasTotales")] public int ParadasTotales { get; set; }
    [JsonPropertyName("ejecutadas")] public int Ejecutadas { get; set; }
    [JsonPropertyName("observadas")] public int Observadas { get; set; }
    [JsonPropertyName("pendientes")] public int Pendientes { get; set; }
    [JsonPropertyName("porcentajeCumplimiento")] public double PorcentajeCumplimiento { get; set; }
    [JsonPropertyName("distanciaTotalKm")] public double DistanciaTotalKm { get; set; }
    [JsonPropertyName("precisionGpsPromedioMetros")] public double? PrecisionGpsPromedioMetros { get; set; }
    [JsonPropertyName("montoGestionadoBs")] public decimal MontoGestionadoBs { get; set; }
    [JsonPropertyName("ultimaActividad")] public DateTime? UltimaActividad { get; set; }
}

public sealed class ReporteEstadoSuministrosModel
{
    [JsonPropertyName("codigoReporte")] public string CodigoReporte { get; set; } = string.Empty;
    [JsonPropertyName("fechaEmision")] public DateTime FechaEmision { get; set; }
    [JsonPropertyName("usuarioEmisor")] public string UsuarioEmisor { get; set; } = "Usuario SIG";
    [JsonPropertyName("titulo")] public string Titulo { get; set; } = string.Empty;
    [JsonPropertyName("subtitulo")] public string Subtitulo { get; set; } = string.Empty;
    [JsonPropertyName("filtroAplicado")] public string FiltroAplicado { get; set; } = string.Empty;
    [JsonPropertyName("totalSuministros")] public int TotalSuministros { get; set; }
    [JsonPropertyName("normal")] public int Normal { get; set; }
    [JsonPropertyName("paraCorte")] public int ParaCorte { get; set; }
    [JsonPropertyName("paraReconexion")] public int ParaReconexion { get; set; }
    [JsonPropertyName("cortado")] public int Cortado { get; set; }
    [JsonPropertyName("bajaParcial")] public int BajaParcial { get; set; }
    [JsonPropertyName("bajaTotal")] public int BajaTotal { get; set; }
    [JsonPropertyName("verificados")] public int Verificados { get; set; }
    [JsonPropertyName("sinVerificar")] public int SinVerificar { get; set; }
    [JsonPropertyName("resumenEjecutivo")] public string ResumenEjecutivo { get; set; } = string.Empty;
    [JsonPropertyName("recomendaciones")] public List<string> Recomendaciones { get; set; } = new();
    [JsonPropertyName("suministros")] public List<SuministroEstadoItemModel> Suministros { get; set; } = new();
}

public sealed class SuministroEstadoItemModel
{
    [JsonPropertyName("idCodigo")] public int IdCodigo { get; set; }
    [JsonPropertyName("codigoFijo")] public string CodigoFijo { get; set; } = string.Empty;
    [JsonPropertyName("codigoSig")] public string CodigoSig { get; set; } = string.Empty;
    [JsonPropertyName("titular")] public string Titular { get; set; } = string.Empty;
    [JsonPropertyName("estadoCodigo")] public int EstadoCodigo { get; set; }
    [JsonPropertyName("estadoTexto")] public string EstadoTexto { get; set; } = string.Empty;
    [JsonPropertyName("estadoVerificado")] public bool EstadoVerificado { get; set; }
    [JsonPropertyName("unidadVecinal")] public string UnidadVecinal { get; set; } = string.Empty;
    [JsonPropertyName("manzana")] public string Manzana { get; set; } = string.Empty;
    [JsonPropertyName("numeroLote")] public string NumeroLote { get; set; } = string.Empty;
    [JsonPropertyName("fechaCambioEstado")] public DateTime FechaCambioEstado { get; set; }
}

public sealed class ReporteEjecutivoGlobalModel
{
    [JsonPropertyName("codigoReporte")] public string CodigoReporte { get; set; } = string.Empty;
    [JsonPropertyName("fechaEmision")] public DateTime FechaEmision { get; set; }
    [JsonPropertyName("usuarioEmisor")] public string UsuarioEmisor { get; set; } = "Usuario SIG";
    [JsonPropertyName("titulo")] public string Titulo { get; set; } = string.Empty;
    [JsonPropertyName("subtitulo")] public string Subtitulo { get; set; } = string.Empty;
    [JsonPropertyName("totalManzanas")] public int TotalManzanas { get; set; }
    [JsonPropertyName("totalLotes")] public int TotalLotes { get; set; }
    [JsonPropertyName("totalVias")] public int TotalVias { get; set; }
    [JsonPropertyName("longitudRedVialKm")] public double LongitudRedVialKm { get; set; }
    [JsonPropertyName("totalCodigosFijos")] public int TotalCodigosFijos { get; set; }
    [JsonPropertyName("lotesConServicio")] public int LotesConServicio { get; set; }
    [JsonPropertyName("lotesSinServicio")] public int LotesSinServicio { get; set; }
    [JsonPropertyName("coberturaGlobalPct")] public double CoberturaGlobalPct { get; set; }
    [JsonPropertyName("normal")] public int Normal { get; set; }
    [JsonPropertyName("paraCorte")] public int ParaCorte { get; set; }
    [JsonPropertyName("paraReconexion")] public int ParaReconexion { get; set; }
    [JsonPropertyName("cortado")] public int Cortado { get; set; }
    [JsonPropertyName("bajaParcial")] public int BajaParcial { get; set; }
    [JsonPropertyName("bajaTotal")] public int BajaTotal { get; set; }
    [JsonPropertyName("totalRutasHistoricas")] public int TotalRutasHistoricas { get; set; }
    [JsonPropertyName("totalIntervencionesCampo")] public int TotalIntervencionesCampo { get; set; }
    [JsonPropertyName("intervencionesCompletadas")] public int IntervencionesCompletadas { get; set; }
    [JsonPropertyName("tasaEfectividadCampoPct")] public double TasaEfectividadCampoPct { get; set; }
    [JsonPropertyName("resumenEjecutivo")] public string ResumenEjecutivo { get; set; } = string.Empty;
    [JsonPropertyName("recomendaciones")] public List<string> Recomendaciones { get; set; } = new();
    [JsonPropertyName("resumenPorUv")] public List<ResumenUvItemModel> ResumenPorUv { get; set; } = new();
}

public sealed class ResumenUvItemModel
{
    [JsonPropertyName("unidadVecinal")] public string UnidadVecinal { get; set; } = string.Empty;
    [JsonPropertyName("totalManzanas")] public int TotalManzanas { get; set; }
    [JsonPropertyName("totalLotes")] public int TotalLotes { get; set; }
    [JsonPropertyName("lotesConAgua")] public int LotesConAgua { get; set; }
    [JsonPropertyName("coberturaPct")] public double CoberturaPct { get; set; }
    [JsonPropertyName("cuentasParaCorte")] public int CuentasParaCorte { get; set; }
    [JsonPropertyName("cuentasCortadas")] public int CuentasCortadas { get; set; }
    [JsonPropertyName("cuentasParaReconexion")] public int CuentasParaReconexion { get; set; }
}
