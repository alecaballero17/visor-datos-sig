using System.Linq.Expressions;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Services;

public static class CandidatosServicio
{
    // EstadoVerificado informa la calidad del dato, no la operación pendiente.
    public static Expression<Func<CodigoFijo, bool>> ParaTipo(string? tipo) => tipo?.Trim().ToLowerInvariant() switch
    {
        "corte" or "cortador" => c => c.Estado == 2,
        "reconexion" or "reconexión" or "reconector" or "reponedor" or "reposicion" or "reposición" => c => c.Estado == 0,
        "cortado" => c => c.Estado == 3,
        _ => c => false
    };

    public static Expression<Func<CodigoFijo, bool>> PuedePasarAReconexion(int id) =>
        c => c.IdCodigo == id && c.Estado == 3;
}
