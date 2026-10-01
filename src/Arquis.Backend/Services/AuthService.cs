using System.Security.Cryptography;
using Arquis.Backend.Data;
using Arquis.Backend.Models;
using Arquis.Backend.Models.Entities;
using Microsoft.EntityFrameworkCore;

namespace Arquis.Backend.Services;

public sealed class AuthService(ArquisDbContext context)
{
    public async Task<UserSession?> ValidateAsync(string login, string password, CancellationToken ct)
    {
        var loginTrimmed = login.Trim();

        var usuario = await context.Usuarios
            .Include(u => u.UsuariosRoles!)
                .ThenInclude(ur => ur.Rol)
            .Where(u => (u.Login == loginTrimmed || u.Email == loginTrimmed) && u.Activo)
            .FirstOrDefaultAsync(ct);

        if (usuario == null) return null;

        var computed = Rfc2898DeriveBytes.Pbkdf2(
            password, 
            usuario.PasswordSalt!, 
            usuario.Iteraciones, 
            HashAlgorithmName.SHA256, 
            usuario.PasswordHash!.Length);

        if (!CryptographicOperations.FixedTimeEquals(usuario.PasswordHash, computed)) 
            return null;

        var roles = usuario.UsuariosRoles?
            .Where(ur => ur.Rol != null && ur.Rol.Estado)
            .Select(ur => ur.Rol!.NombreRol)
            .Where(r => !string.IsNullOrWhiteSpace(r))
            .ToArray() ?? Array.Empty<string>();

        return new UserSession(
            usuario.IdUsuario,
            usuario.Login!,
            usuario.Nombre!,
            roles!);
    }

    public async Task RegisterAsync(RegisterRequest request, CancellationToken ct)
    {
        var rolConsultor = await context.Roles
            .FirstOrDefaultAsync(r => r.NombreRol == "Consultor" && r.Estado, ct);

        if (rolConsultor == null)
            throw new Exception("El rol de registro no esta disponible.");

        var emailTrimmed = request.Email.Trim().ToLowerInvariant();

        var exists = await context.Usuarios
            .AnyAsync(u => u.Login == emailTrimmed || u.Email == emailTrimmed, ct);

        if (exists)
            throw new Exception("El email ya esta registrado.");

        var salt = RandomNumberGenerator.GetBytes(32);
        const int iterations = 210000;
        var hash = Rfc2898DeriveBytes.Pbkdf2(request.Password, salt, iterations, HashAlgorithmName.SHA256, 32);

        var nuevoUsuario = new Usuario
        {
            Login = "u" + Guid.NewGuid().ToString("N"),
            Nombre = request.Nombre.Trim(),
            Email = emailTrimmed,
            PasswordHash = hash,
            PasswordSalt = salt,
            Iteraciones = iterations,
            Activo = true,
            FechaRegistro = DateTime.UtcNow
        };

        context.Usuarios.Add(nuevoUsuario);
        await context.SaveChangesAsync(ct);

        context.UsuariosRoles.Add(new UsuarioRol
        {
            IdUsuario = nuevoUsuario.IdUsuario,
            IdRol = rolConsultor.IdRol
        });

        var menusDefault = await context.MenuOpciones
            .Where(m => m.Estado && (m.NombreMenu == "Dashboard" || m.NombreMenu == "Visualización General"))
            .ToListAsync(ct);

        foreach (var menu in menusDefault)
        {
            context.UsuarioMenus.Add(new UsuarioMenu
            {
                IdUsuario = nuevoUsuario.IdUsuario,
                IdMenu = menu.IdMenu,
                PuedeVer = true,
                PuedeCrear = false,
                PuedeEditar = false,
                PuedeEliminar = false
            });
        }

        await context.SaveChangesAsync(ct);
    }

    public async Task LogAccessAsync(string login, bool success, string? ip, string? detail, CancellationToken ct)
    {
        context.BitacoraAccesos.Add(new BitacoraAcceso
        {
            Login = login,
            Exitoso = success,
            Ip = ip,
            Detalle = detail,
            Fecha = DateTime.UtcNow
        });

        await context.SaveChangesAsync(ct);
    }
}
