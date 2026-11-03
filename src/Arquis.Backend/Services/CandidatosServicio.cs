using System.Linq.Expressions;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Services;

public static class CandidatosServicio
{
    // EstadoVerificado informa la calidad del dato, no la operación pendiente.
    public static Expression<Func<CodigoFijo, bool>> ParaTipo(string? tipo) => tipo?.ToLowerInvariant() switch
    {
        "corte" => c => c.Estado == 2,
        "reconexion" => c => c.Estado == 0,
        "cortado" => c => c.Estado == 3,
        _ => c => false
    };

    public static Expression<Func<CodigoFijo, bool>> PuedePasarAReconexion(int id) =>
        c => c.IdCodigo == id && c.Estado == 3;
}
