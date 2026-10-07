using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data.Seeders;

namespace Arquis.Backend.Data
{
    public static class DbSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            await EnsureBitacoraReportesTableAsync(context);
            await RoleSeeder.SeedAsync(context);
            await UserSeeder.SeedAsync(context);
            await MenuSeeder.SeedAsync(context);
            await GeoDataSeeder.SeedAsync(context);
        }

        private static async Task EnsureBitacoraReportesTableAsync(ArquisDbContext context)
        {
            try
            {
                await context.Database.ExecuteSqlRawAsync(@"
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'BitacoraReportes')
                    BEGIN
                        CREATE TABLE dbo.BitacoraReportes (
                            IdBitacora BIGINT IDENTITY(1,1) PRIMARY KEY,
                            Fecha DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                            Usuario NVARCHAR(254) NOT NULL,
                            TipoReporte NVARCHAR(64) NOT NULL,
                            Referencia NVARCHAR(254) NOT NULL,
                            Accion NVARCHAR(128) NOT NULL,
                            Detalle NVARCHAR(1000) NULL,
                            Ip NVARCHAR(64) NULL
                        );
                        CREATE INDEX IX_BitacoraReportes_Fecha ON dbo.BitacoraReportes(Fecha DESC);
                    END
                ");
            }
            catch (System.Exception ex)
            {
                System.Console.WriteLine($"Nota de inicialización BitacoraReportes: {ex.Message}");
            }
        }
    }
}
