using Microsoft.Data.SqlClient;
using System;
using System.Threading;
using System.Threading.Tasks;

namespace Arquis.Migrador.Services;

public sealed class SqlConnectionValidator
{
    public async Task<ConnectionTestResult> TestAsync(string connectionString, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(connectionString))
            return new(false, "Ingrese una cadena de conexión de SQL Server.");

        try
        {
            var builder = new SqlConnectionStringBuilder(connectionString);
            if (string.IsNullOrWhiteSpace(builder.DataSource) || string.IsNullOrWhiteSpace(builder.InitialCatalog))
                return new(false, "La cadena debe indicar el servidor y la base de datos.");

            await using var connection = new SqlConnection(builder.ConnectionString);
            await connection.OpenAsync(cancellationToken);
            await using var command = new SqlCommand("SELECT DB_NAME(), SERVERPROPERTY('ProductVersion')", connection);
            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            if (!await reader.ReadAsync(cancellationToken)) return new(false, "SQL Server no devolvió información de la conexión.");
            var database = reader.GetString(0);
            return new(true, $"Conexión correcta con SQL Server. Base de datos activa: {database}.");
        }
        catch (SqlException ex)
        {
            return new(false, $"No se pudo conectar a SQL Server: {ex.Message}");
        }
        catch (ArgumentException)
        {
            return new(false, "La cadena de conexión no tiene un formato válido.");
        }
    }
}

public sealed record ConnectionTestResult(bool IsValid, string Message);
