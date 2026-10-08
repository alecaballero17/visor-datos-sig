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
