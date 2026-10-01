using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsuariosController(ArquisDbContext context) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetUsuarios()
    {
        var usuarios = await context.Usuarios
            .Select(u => new
            {
                u.IdUsuario,
                u.Login,
                u.Nombre,
                u.Email,
                u.Activo,
                u.FechaRegistro
            })
            .ToListAsync();
        return Ok(usuarios);
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetUsuario(int id)
    {
        var usuario = await context.Usuarios
            .Where(u => u.IdUsuario == id)
            .Select(u => new
            {
                u.IdUsuario,
                u.Login,
                u.Nombre,
                u.Email,
                u.Activo,
                u.FechaRegistro
            })
            .FirstOrDefaultAsync();

        if (usuario == null) return NotFound();
        return Ok(usuario);
    }
}
