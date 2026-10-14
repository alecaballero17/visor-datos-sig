using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data.Seeders
{
    public static class RoleSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            var rolesToSeed = new[]
            {
                new Rol { NombreRol = "Administrador", Descripcion = "Administrador del Sistema", Estado = true },
                new Rol { NombreRol = "Catastro", Descripcion = "Rol para crear, modificar y eliminar Manzanas, Lotes, Codigo Fijo y Vias", Estado = true },
                new Rol { NombreRol = "Lecturador", Descripcion = "Rol para lecturar medidores", Estado = true },
                new Rol { NombreRol = "Cortador", Descripcion = "Rol para corte y suspensión de servicios de agua potable", Estado = true },
                new Rol { NombreRol = "Reconector", Descripcion = "Rol para reconexión y restitución de servicios de agua potable", Estado = true },
                new Rol { NombreRol = "Reconexion", Descripcion = "Rol para reconexión de servicios", Estado = true },
                new Rol { NombreRol = "Consultor", Descripcion = "Consulta del visor cartográfico", Estado = true },
                new Rol { NombreRol = "Operador", Descripcion = "Operador de campo en aplicación móvil", Estado = true }
            };

            foreach (var r in rolesToSeed)
            {
                if (!await context.Roles.AnyAsync(x => x.NombreRol == r.NombreRol))
                {
                    context.Roles.Add(r);
                }
            }
            await context.SaveChangesAsync();
        }
    }
}
