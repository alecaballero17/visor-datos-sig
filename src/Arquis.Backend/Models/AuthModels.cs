using System.ComponentModel.DataAnnotations;
namespace Arquis.Backend.Models;

public sealed record LoginRequest(string Usuario, string Password, string? Origen = null);
public sealed record RegisterRequest(
    [Required, StringLength(120, MinimumLength=2)] string Nombre,
    [Required, EmailAddress, StringLength(254)] string Email,
    [Required, StringLength(128, MinimumLength=8)] string Password,
    string? Origen = null);
public sealed record UserSession(int Id, string Usuario, string Nombre, IReadOnlyList<string> Roles);
