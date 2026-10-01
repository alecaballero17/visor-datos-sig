using Microsoft.EntityFrameworkCore;
using System.Threading.Tasks;

namespace Arquis.Backend.Data
{
    public static class SpatialIndexOptimizer
    {
        public static async Task OptimizeIndicesAsync(ArquisDbContext context)
        {
            // Ejecuta el procedimiento almacenado que contiene toda la lógica dinámica de reconstrucción de índices
            await context.Database.ExecuteSqlRawAsync("EXEC dbo.sp_OptimizarIndicesEspaciales;");
        }
    }
}
