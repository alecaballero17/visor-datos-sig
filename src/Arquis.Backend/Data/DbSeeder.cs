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
            await EnsureTrackingAndRutasTablesAsync(context);
            await RoleSeeder.SeedAsync(context);
            await UserSeeder.SeedAsync(context);
            await MenuSeeder.SeedAsync(context);
            await GeoDataSeeder.SeedAsync(context);
            await EnsureVinculacionCatastralAsync(context);
            await SeedDemoTrackingAndRutasAsync(context);
        }

        private static async Task EnsureVinculacionCatastralAsync(ArquisDbContext context)
        {
            try
            {
                // 1. Vincular CodigosFijos a Lotes mediante STIntersects si hay registros sin IdLote
                await context.Database.ExecuteSqlRawAsync(@"
                    IF EXISTS (SELECT 1 FROM dbo.CodigosFijos WHERE IdLote IS NULL)
                    BEGIN
                        UPDATE c
                        SET c.IdLote = l.IdLote
                        FROM dbo.CodigosFijos c
                        JOIN dbo.Lotes l ON c.Geom.STIntersects(l.Geom) = 1
                        WHERE c.IdLote IS NULL;
                    END
                ");

                // 2. Vincular Lotes a Manzanas mediante STIntersects si hay registros sin IdManzana
                await context.Database.ExecuteSqlRawAsync(@"
                    IF EXISTS (SELECT 1 FROM dbo.Lotes WHERE IdManzana IS NULL)
                    BEGIN
                        UPDATE l
                        SET l.IdManzana = m.IdManzana
                        FROM dbo.Lotes l
                        JOIN dbo.Manzanas m ON l.Geom.STIntersects(m.Geom) = 1
                        WHERE l.IdManzana IS NULL;
                    END
                ");
            }
            catch (System.Exception ex)
            {
                System.Console.WriteLine($"Nota de vinculación catastral: {ex.Message}");
            }
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

        private static async Task EnsureTrackingAndRutasTablesAsync(ArquisDbContext context)
        {
            try
            {
                await context.Database.ExecuteSqlRawAsync(@"
                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'TrackingPosiciones')
                    BEGIN
                        CREATE TABLE dbo.TrackingPosiciones (
                            Id BIGINT IDENTITY(1,1) PRIMARY KEY,
                            OperarioId NVARCHAR(100) NOT NULL,
                            NombreOperario NVARCHAR(150) NOT NULL,
                            Rol NVARCHAR(50) NOT NULL DEFAULT 'Cortador',
                            Latitud FLOAT NOT NULL,
                            Longitud FLOAT NOT NULL,
                            Rumbo FLOAT NOT NULL DEFAULT 0,
                            Velocidad FLOAT NOT NULL DEFAULT 0,
                            Bateria INT NOT NULL DEFAULT 100,
                            Timestamp DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                            EnLinea BIT NOT NULL DEFAULT 1
                        );
                        CREATE INDEX IX_TrackingPosiciones_Operario_Time ON dbo.TrackingPosiciones(OperarioId, Timestamp DESC);
                    END

                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RutasTrabajo')
                    BEGIN
                        CREATE TABLE dbo.RutasTrabajo (
                            Id INT IDENTITY(1,1) PRIMARY KEY,
                            Codigo NVARCHAR(50) NOT NULL,
                            Titulo NVARCHAR(200) NOT NULL,
                            Tipo NVARCHAR(50) NOT NULL DEFAULT 'Corte',
                            Estado NVARCHAR(50) NOT NULL DEFAULT 'Pendiente',
                            Prioridad NVARCHAR(50) NOT NULL DEFAULT 'Normal',
                            OperarioAsignado NVARCHAR(150) NOT NULL DEFAULT 'Pedro',
                            OperarioId NVARCHAR(100) NULL,
                            CreadoPor NVARCHAR(100) NOT NULL DEFAULT 'Gerente',
                            FechaCreacion DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                            FechaAsignacion DATETIME2 NULL,
                            FechaCompletado DATETIME2 NULL,
                            Observaciones NVARCHAR(1000) NULL
                        );
                    END

                    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PuntosRutaTrabajo')
                    BEGIN
                        CREATE TABLE dbo.PuntosRutaTrabajo (
                            Id INT IDENTITY(1,1) PRIMARY KEY,
                            RutaTrabajoId INT NOT NULL,
                            Orden INT NOT NULL DEFAULT 1,
                            IdCodigoFijo INT NULL,
                            IdLote INT NULL,
                            CodigoSuministro NVARCHAR(100) NULL,
                            Lote NVARCHAR(50) NULL,
                            Titular NVARCHAR(200) NULL,
                            Direccion NVARCHAR(250) NULL,
                            Latitud FLOAT NOT NULL,
                            Longitud FLOAT NOT NULL,
                            MontoDeuda DECIMAL(18,2) NULL,
                            Estado NVARCHAR(50) NOT NULL DEFAULT 'Pendiente',
                            FechaEjecucion DATETIME2 NULL,
                            Observaciones NVARCHAR(500) NULL,
                            CONSTRAINT FK_PuntosRuta_Rutas FOREIGN KEY (RutaTrabajoId) REFERENCES dbo.RutasTrabajo(Id) ON DELETE CASCADE
                        );
                        CREATE INDEX IX_PuntosRuta_RutaTrabajoId ON dbo.PuntosRutaTrabajo(RutaTrabajoId, Orden ASC);
                    END

                    -- Columnas para RF-WEB-04/05 (Partida y Geometría Dijkstra)
                    IF COL_LENGTH('dbo.RutasTrabajo', 'PartidaLatitud') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD PartidaLatitud FLOAT NULL;
                    IF COL_LENGTH('dbo.RutasTrabajo', 'PartidaLongitud') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD PartidaLongitud FLOAT NULL;
                    IF COL_LENGTH('dbo.RutasTrabajo', 'PartidaNombre') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD PartidaNombre NVARCHAR(250) NULL;
                    IF COL_LENGTH('dbo.RutasTrabajo', 'DistanciaTotalMetros') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD DistanciaTotalMetros FLOAT NULL;
                    IF COL_LENGTH('dbo.RutasTrabajo', 'TiempoEstimadoMinutos') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD TiempoEstimadoMinutos INT NULL;
                    IF COL_LENGTH('dbo.RutasTrabajo', 'GeometriaRutaGeoJson') IS NULL
                        ALTER TABLE dbo.RutasTrabajo ADD GeometriaRutaGeoJson NVARCHAR(MAX) NULL;

                    -- Columnas para RN-01 / RF-MOB-05 (Auditoría Antifraude)
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'LatitudEjecucion') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD LatitudEjecucion FLOAT NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'LongitudEjecucion') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD LongitudEjecucion FLOAT NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'DistanciaAntifraudeMetros') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD DistanciaAntifraudeMetros FLOAT NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'LecturaMedidor') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD LecturaMedidor DECIMAL(18,2) NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'EstadoFinal') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD EstadoFinal NVARCHAR(50) NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'MotivoObservacion') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD MotivoObservacion NVARCHAR(250) NULL;
                    IF COL_LENGTH('dbo.PuntosRutaTrabajo', 'FotosEvidenciasJson') IS NULL
                        ALTER TABLE dbo.PuntosRutaTrabajo ADD FotosEvidenciasJson NVARCHAR(MAX) NULL;
                ");
            }
            catch (System.Exception ex)
            {
                System.Console.WriteLine($"Nota de inicialización Tablas Tracking/Rutas: {ex.Message}");
            }
        }

        private static async Task SeedDemoTrackingAndRutasAsync(ArquisDbContext context)
        {
            try
            {
                if (!await context.RutasTrabajo.AnyAsync())
                {
                    var demoRuta = new Models.Entities.RutaTrabajo
                    {
                        Codigo = "RC-2026-001",
                        Titulo = "Operativo de Corte por Mora - UV 4 / MZA 12",
                        Tipo = "Corte",
                        Estado = "EnProgreso",
                        Prioridad = "Alta",
                        OperarioAsignado = "Pedro",
                        OperarioId = "Pedro",
                        CreadoPor = "Gerente de Operaciones",
                        FechaCreacion = DateTime.UtcNow.AddHours(-2),
                        FechaAsignacion = DateTime.UtcNow.AddHours(-1),
                        Observaciones = "Corte de servicio a suministros con más de 3 meses de mora. Precintar llave de paso y registrar lectura.",
                        Puntos = new List<Models.Entities.PuntoRutaTrabajo>
                        {
                            new()
                            {
                                Orden = 1,
                                CodigoSuministro = "CF-40112",
                                Lote = "Lote 3",
                                Titular = "Carlos Mendoza",
                                Direccion = "UV 4, Manzana 12, Lote 3",
                                Latitud = -17.78120,
                                Longitud = -63.18180,
                                MontoDeuda = 345.50m,
                                Estado = "Completado",
                                FechaEjecucion = DateTime.UtcNow.AddMinutes(-35),
                                Observaciones = "Precinto rojo colocado. Suministro cortado satisfactoriamente."
                            },
                            new()
                            {
                                Orden = 2,
                                CodigoSuministro = "CF-40115",
                                Lote = "Lote 7",
                                Titular = "María Elena Suárez",
                                Direccion = "UV 4, Manzana 12, Lote 7",
                                Latitud = -17.78185,
                                Longitud = -63.18235,
                                MontoDeuda = 520.00m,
                                Estado = "Pendiente",
                                Observaciones = "Deuda vencida. Verificar si hay perro en el ingreso."
                            },
                            new()
                            {
                                Orden = 3,
                                CodigoSuministro = "CF-40121",
                                Lote = "Lote 14",
                                Titular = "Roberto Gómez",
                                Direccion = "UV 4, Manzana 12, Lote 14",
                                Latitud = -17.78250,
                                Longitud = -63.18150,
                                MontoDeuda = 210.80m,
                                Estado = "Pendiente",
                                Observaciones = "Acometida con candado anterior."
                            },
                            new()
                            {
                                Orden = 4,
                                CodigoSuministro = "CF-40128",
                                Lote = "Lote 22",
                                Titular = "Juana Vaca",
                                Direccion = "UV 4, Manzana 12, Lote 22",
                                Latitud = -17.78310,
                                Longitud = -63.18280,
                                MontoDeuda = 780.00m,
                                Estado = "Pendiente",
                                Observaciones = "Mora crítica de 5 facturas."
                            }
                        }
                    };

                    context.RutasTrabajo.Add(demoRuta);
                    await context.SaveChangesAsync();
                }

                // Seed initial historical trail for Pedro so the web route player has points right away
                if (!await context.TrackingPosiciones.AnyAsync(x => x.OperarioId == "Pedro"))
                {
                    var baseTime = DateTime.UtcNow.AddMinutes(-40);
                    var points = new[]
                    {
                        new Models.Entities.TrackingPosicion { OperarioId = "Pedro", NombreOperario = "Pedro (Cortador)", Rol = "Cortador", Latitud = -17.78010, Longitud = -63.18020, Rumbo = 145, Velocidad = 18.5, Bateria = 94, Timestamp = baseTime, EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Pedro", NombreOperario = "Pedro (Cortador)", Rol = "Cortador", Latitud = -17.78055, Longitud = -63.18085, Rumbo = 140, Velocidad = 15.2, Bateria = 93, Timestamp = baseTime.AddMinutes(8), EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Pedro", NombreOperario = "Pedro (Cortador)", Rol = "Cortador", Latitud = -17.78120, Longitud = -63.18180, Rumbo = 135, Velocidad = 0.0, Bateria = 91, Timestamp = baseTime.AddMinutes(15), EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Pedro", NombreOperario = "Pedro (Cortador)", Rol = "Cortador", Latitud = -17.78150, Longitud = -63.18205, Rumbo = 190, Velocidad = 12.0, Bateria = 90, Timestamp = baseTime.AddMinutes(25), EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Pedro", NombreOperario = "Pedro (Cortador)", Rol = "Cortador", Latitud = -17.78180, Longitud = -63.18228, Rumbo = 210, Velocidad = 8.4, Bateria = 89, Timestamp = baseTime.AddMinutes(35), EnLinea = true }
                    };
                    context.TrackingPosiciones.AddRange(points);
                    await context.SaveChangesAsync();
                }

                if (!await context.TrackingPosiciones.AnyAsync(x => x.OperarioId == "Juan"))
                {
                    var baseTime = DateTime.UtcNow.AddMinutes(-30);
                    var points = new[]
                    {
                        new Models.Entities.TrackingPosicion { OperarioId = "Juan", NombreOperario = "Juan (Reconector)", Rol = "Reconector", Latitud = -17.78200, Longitud = -63.18350, Rumbo = 85, Velocidad = 16.0, Bateria = 92, Timestamp = baseTime, EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Juan", NombreOperario = "Juan (Reconector)", Rol = "Reconector", Latitud = -17.78245, Longitud = -63.18385, Rumbo = 110, Velocidad = 14.5, Bateria = 91, Timestamp = baseTime.AddMinutes(10), EnLinea = true },
                        new Models.Entities.TrackingPosicion { OperarioId = "Juan", NombreOperario = "Juan (Reconector)", Rol = "Reconector", Latitud = -17.78280, Longitud = -63.18410, Rumbo = 120, Velocidad = 0.0, Bateria = 90, Timestamp = baseTime.AddMinutes(20), EnLinea = true }
                    };
                    context.TrackingPosiciones.AddRange(points);
                    await context.SaveChangesAsync();
                }
            }
            catch (System.Exception ex)
            {
                System.Console.WriteLine($"Nota de seeding demo tracking/rutas: {ex.Message}");
            }
        }
    }
}
