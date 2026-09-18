using System.Security.Cryptography;
using Arquis.Backend.Data;
using Arquis.Backend.Models;
using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Services;

public sealed class AuthService(SqlConnectionFactory connectionFactory)
{
    public async Task<UserSession?> ValidateAsync(string login, string password, CancellationToken ct)
    {
        const string sql = """
        SELECT u.IdUsuario, u.Login, u.Nombre, u.PasswordHash, u.PasswordSalt, u.Iteraciones,
               STRING_AGG(r.NombreRol, ',') AS Roles
        FROM dbo.Usuarios u
        LEFT JOIN dbo.UsuariosRoles ur ON ur.IdUsuario = u.IdUsuario
        LEFT JOIN dbo.Roles r ON r.IdRol = ur.IdRol AND r.Estado = 1
        WHERE (u.Login = @Login OR u.Email = @Login) AND u.Activo = 1
        GROUP BY u.IdUsuario, u.Login, u.Nombre, u.PasswordHash, u.PasswordSalt, u.Iteraciones;
        """;

        await using var cn = connectionFactory.Create();
        await cn.OpenAsync(ct);
        await using var cmd = new SqlCommand(sql, cn);
        cmd.Parameters.AddWithValue("@Login", login.Trim());
        await using var rd = await cmd.ExecuteReaderAsync(ct);
        if (!await rd.ReadAsync(ct)) return null;

        var hash = (byte[])rd["PasswordHash"];
        var salt = (byte[])rd["PasswordSalt"];
        var iterations = Convert.ToInt32(rd["Iteraciones"]);
        var computed = Rfc2898DeriveBytes.Pbkdf2(password, salt, iterations, HashAlgorithmName.SHA256, hash.Length);
        if (!CryptographicOperations.FixedTimeEquals(hash, computed)) return null;

        var rolesRaw = rd["Roles"] as string;
        var roles = string.IsNullOrWhiteSpace(rolesRaw)
            ? Array.Empty<string>()
            : rolesRaw.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

        return new UserSession(
            Convert.ToInt32(rd["IdUsuario"]),
            Convert.ToString(rd["Login"])!,
            Convert.ToString(rd["Nombre"])!,
            roles);
    }

    public async Task RegisterAsync(RegisterRequest request, CancellationToken ct)
    {
        var salt = RandomNumberGenerator.GetBytes(32);
        const int iterations = 210000;
        var hash = Rfc2898DeriveBytes.Pbkdf2(request.Password, salt, iterations, HashAlgorithmName.SHA256, 32);
        await using var cn = connectionFactory.Create();
        await cn.OpenAsync(ct);
        await using var transaction = (SqlTransaction)await cn.BeginTransactionAsync(ct);
        const string sql = """
            DECLARE @Rol int=(SELECT IdRol FROM dbo.Roles WHERE NombreRol='Consultor' AND Estado=1);
            IF @Rol IS NULL THROW 50001, 'El rol de registro no esta disponible.', 1;
            IF EXISTS(SELECT 1 FROM dbo.Usuarios WHERE Login=@Email OR Email=@Email)
                THROW 50002, 'El email ya esta registrado.', 1;
            INSERT dbo.Usuarios(Login,Nombre,Email,PasswordHash,PasswordSalt,Iteraciones,Activo)
            VALUES(@Login,@Nombre,@Email,@Hash,@Salt,@Iterations,1);
            DECLARE @Id int=CONVERT(int,SCOPE_IDENTITY());
            INSERT dbo.UsuariosRoles(IdUsuario,IdRol) VALUES(@Id,@Rol);
            INSERT dbo.UsuarioMenu(IdUsuario,IdMenu,PuedeVer)
            SELECT @Id,IdMenu,1 FROM dbo.MenuOpciones
            WHERE Estado=1 AND NombreMenu IN(N'Dashboard',N'Visualización General');
            """;
        await using var cmd = new SqlCommand(sql, cn, transaction);
        cmd.Parameters.AddWithValue("@Login", "u" + Guid.NewGuid().ToString("N"));
        cmd.Parameters.AddWithValue("@Nombre", request.Nombre.Trim());
        cmd.Parameters.AddWithValue("@Email", request.Email.Trim().ToLowerInvariant());
        cmd.Parameters.AddWithValue("@Hash", hash);
        cmd.Parameters.AddWithValue("@Salt", salt);
        cmd.Parameters.AddWithValue("@Iterations", iterations);
        await cmd.ExecuteNonQueryAsync(ct);
        await transaction.CommitAsync(ct);
    }

    public async Task LogAccessAsync(string login, bool success, string? ip, string? detail, CancellationToken ct)
    {
        const string sql = """
        IF OBJECT_ID('dbo.BitacoraAcceso','U') IS NOT NULL
        INSERT dbo.BitacoraAcceso(Login, Exitoso, Ip, Detalle)
        VALUES(@Login, @Exitoso, @Ip, @Detalle);
        """;
        await using var cn = connectionFactory.Create();
        await cn.OpenAsync(ct);
        await using var cmd = new SqlCommand(sql, cn);
        cmd.Parameters.AddWithValue("@Login", login);
        cmd.Parameters.AddWithValue("@Exitoso", success);
        cmd.Parameters.AddWithValue("@Ip", (object?)ip ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@Detalle", (object?)detail ?? DBNull.Value);
        await cmd.ExecuteNonQueryAsync(ct);
    }
}
