using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Data;

public sealed class SqlConnectionFactory(IConfiguration configuration)
{
    private readonly string _connectionString = configuration.GetConnectionString("DefaultConnection")
        ?? throw new InvalidOperationException("No se configuró ConnectionStrings:DefaultConnection.");

    public SqlConnection Create() => new(_connectionString);
}
