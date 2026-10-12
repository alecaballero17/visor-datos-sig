using System.Security.Claims;
using Arquis.Backend.Models;
using Arquis.Backend.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Controllers;

[ApiController]
[Route("api/autenticacion")]
public sealed class AuthController(AuthService authService) : ControllerBase
{
    [AllowAnonymous]
    [HttpPost("registrar")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request, CancellationToken ct)
    {
        if (request.Nombre.Trim().Length < 2) return BadRequest(new { mensaje="Ingrese su nombre." });
        try { await authService.RegisterAsync(request, ct); }
        catch (SqlException ex) when (ex.Number is 2601 or 2627 or 50002)
        { return Conflict(new { mensaje="Ese email ya está registrado." }); }
        return StatusCode(201, new { mensaje="Cuenta creada. Ingrese con su email y contraseña." });
    }

    [AllowAnonymous]
    [HttpPost("iniciar")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Usuario) || string.IsNullOrWhiteSpace(request.Password))
            return BadRequest(new { mensaje="Usuario y contraseña son obligatorios." });
        if (request.Usuario.Trim().Length > 254 || request.Password.Length > 128)
            return BadRequest(new { mensaje="Credenciales demasiado largas." });
        var session = await authService.ValidateAsync(request.Usuario, request.Password, ct);
        if (session is null)
        {
            await authService.LogAccessAsync(request.Usuario, false, HttpContext.Connection.RemoteIpAddress?.ToString(), "Credenciales inválidas", ct);
            return Unauthorized(new { mensaje="Credenciales inválidas." });
        }

        var esOrigenMovil = string.Equals(request.Origen, "movil", StringComparison.OrdinalIgnoreCase);

        bool tieneRolOperador = session.Roles.Any(r => 
            r.Equals("Operador", StringComparison.OrdinalIgnoreCase) ||
            r.Equals("Cortador", StringComparison.OrdinalIgnoreCase) ||
            r.Equals("Lecturador", StringComparison.OrdinalIgnoreCase) ||
            r.Equals("Reconexion", StringComparison.OrdinalIgnoreCase));

        bool esAdmin = session.Roles.Any(r => r.Equals("Administrador", StringComparison.OrdinalIgnoreCase));

        // REGLA 1: Acceso a Plataforma WEB (esOrigenMovil == false)
        // Las cuentas de Operador son exclusivas para móvil y no pueden ingresar a la plataforma web
        if (!esOrigenMovil && tieneRolOperador && !esAdmin)
        {
            await authService.LogAccessAsync(session.Usuario, false, HttpContext.Connection.RemoteIpAddress?.ToString(), "Acceso web denegado: rol Operador exclusivo de móvil", ct);
            return StatusCode(StatusCodes.Status403Forbidden, new 
            { 
                mensaje = "Acceso denegado: Esta cuenta tiene rol de Operador y es exclusiva de la aplicación móvil. No tiene autorización para ingresar a la plataforma web." 
            });
        }

        // REGLA 2: Acceso a Aplicación MÓVIL (esOrigenMovil == true)
        // Todos los que ocupan la app móvil deben ser operador (o administrador)
        if (esOrigenMovil && !tieneRolOperador && !esAdmin)
        {
            await authService.LogAccessAsync(session.Usuario, false, HttpContext.Connection.RemoteIpAddress?.ToString(), "Acceso móvil denegado: cuenta sin rol de operador", ct);
            return StatusCode(StatusCodes.Status403Forbidden, new 
            { 
                mensaje = "Acceso denegado: La aplicación móvil es de uso exclusivo para Operadores de campo. Esta cuenta pertenece a la plataforma web." 
            });
        }

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, session.Id.ToString()),
            new(ClaimTypes.Name, session.Usuario),
            new("nombre", session.Nombre)
        };
        claims.AddRange(session.Roles.Select(r => new Claim(ClaimTypes.Role, r)));
        var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, new ClaimsPrincipal(identity));
        await authService.LogAccessAsync(session.Usuario, true, HttpContext.Connection.RemoteIpAddress?.ToString(), null, ct);
        return Ok(session);
    }

    [Authorize]
    [HttpPost("cerrar")]
    public async Task<IActionResult> Logout()
    {
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        return Ok(new { mensaje="Sesión cerrada." });
    }

    [Authorize]
    [HttpGet("sesion")]
    public IActionResult Session() => Ok(new
    {
        usuario = User.Identity?.Name,
        nombre = User.FindFirstValue("nombre"),
        roles = User.FindAll(ClaimTypes.Role).Select(x=>x.Value).ToArray()
    });
}
