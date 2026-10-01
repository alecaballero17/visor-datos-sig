using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data.Seeders
{
    public static class MenuSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            var menusNivel1 = new[]
            {
                new MenuOpcion { NombreMenu = "Dashboard", Icono = "▦", Nivel = 1, Orden = 1, Estado = true },
                new MenuOpcion { NombreMenu = "Asignaciones", Icono = "✓", Nivel = 1, Orden = 2, Estado = true },
                new MenuOpcion { NombreMenu = "Ejecución", Icono = "▶", Nivel = 1, Orden = 3, Estado = true },
                new MenuOpcion { NombreMenu = "Monitoreo", Icono = "◉", Nivel = 1, Orden = 4, Estado = true }
            };
            foreach (var m in menusNivel1)
            {
                if (!await context.MenuOpciones.AnyAsync(x => x.NombreMenu == m.NombreMenu && x.Nivel == 1))
                {
                    context.MenuOpciones.Add(m);
                }
            }
            await context.SaveChangesAsync();

            var dashboardId = (await context.MenuOpciones.FirstAsync(x => x.NombreMenu == "Dashboard")).IdMenu;
            var asignacionesId = (await context.MenuOpciones.FirstAsync(x => x.NombreMenu == "Asignaciones")).IdMenu;
            var ejecucionId = (await context.MenuOpciones.FirstAsync(x => x.NombreMenu == "Ejecución")).IdMenu;
            var monitoreoId = (await context.MenuOpciones.FirstAsync(x => x.NombreMenu == "Monitoreo")).IdMenu;

            var menusNivel2 = new[]
            {
                new MenuOpcion { IdMenuPadre = dashboardId, Nivel = 2, NombreMenu = "Visualización General", Url = "~/Mapa.aspx", Orden = 1, Estado = true },
                new MenuOpcion { IdMenuPadre = asignacionesId, Nivel = 2, NombreMenu = "Asignación de Lecturación", Url = null, Orden = 1, Estado = true },
                new MenuOpcion { IdMenuPadre = asignacionesId, Nivel = 2, NombreMenu = "Asignación de Cortes", Url = "~/AsigCortes.aspx", Orden = 2, Estado = true },
                new MenuOpcion { IdMenuPadre = asignacionesId, Nivel = 2, NombreMenu = "Asignación de Reconexión", Url = "~/AsigReconexion.aspx", Orden = 3, Estado = true },
                new MenuOpcion { IdMenuPadre = asignacionesId, Nivel = 2, NombreMenu = "Asignación de Orden de Trabajo", Url = null, Orden = 4, Estado = true },
                
                new MenuOpcion { IdMenuPadre = ejecucionId, Nivel = 2, NombreMenu = "Ejecución de Lecturación", Url = null, Orden = 1, Estado = true },
                new MenuOpcion { IdMenuPadre = ejecucionId, Nivel = 2, NombreMenu = "Ejecución de Cortes", Url = "~/EjeCortes.aspx", Orden = 2, Estado = true },
                new MenuOpcion { IdMenuPadre = ejecucionId, Nivel = 2, NombreMenu = "Ejecución de Reconexión", Url = "~/EjeReconexion.aspx", Orden = 3, Estado = true },
                new MenuOpcion { IdMenuPadre = ejecucionId, Nivel = 2, NombreMenu = "Ejecución de Orden de Trabajo", Url = null, Orden = 4, Estado = true },

                new MenuOpcion { IdMenuPadre = monitoreoId, Nivel = 2, NombreMenu = "Monitoreo de Lecturación", Url = null, Orden = 1, Estado = true },
                new MenuOpcion { IdMenuPadre = monitoreoId, Nivel = 2, NombreMenu = "Monitoreo de Cortes", Url = "~/MoniCortes.aspx", Orden = 2, Estado = true },
                new MenuOpcion { IdMenuPadre = monitoreoId, Nivel = 2, NombreMenu = "Monitoreo de Reconexión", Url = "~/MoniReconexion.aspx", Orden = 3, Estado = true },
                new MenuOpcion { IdMenuPadre = monitoreoId, Nivel = 2, NombreMenu = "Monitoreo de Orden de Trabajo", Url = null, Orden = 4, Estado = true }
            };
            foreach (var m in menusNivel2)
            {
                if (!await context.MenuOpciones.AnyAsync(x => x.NombreMenu == m.NombreMenu && x.IdMenuPadre == m.IdMenuPadre))
                {
                    context.MenuOpciones.Add(m);
                }
            }
            await context.SaveChangesAsync();

            var allMenus = await context.MenuOpciones.ToListAsync();
            var adminUser = await context.Usuarios.FirstAsync(x => x.Login == "admin");
            var juanUser = await context.Usuarios.FirstAsync(x => x.Login == "Juan");
            var pedroUser = await context.Usuarios.FirstAsync(x => x.Login == "Pedro");
            
            // Admin permissions
            foreach (var m in allMenus)
            {
                if (!await context.UsuarioMenus.AnyAsync(x => x.IdUsuario == adminUser.IdUsuario && x.IdMenu == m.IdMenu))
                {
                    context.UsuarioMenus.Add(new UsuarioMenu { IdUsuario = adminUser.IdUsuario, IdMenu = m.IdMenu, PuedeVer = true, PuedeCrear = true, PuedeEditar = true, PuedeEliminar = true });
                }
            }

            // Juan permissions
            var juanMenus = new[] { "Dashboard", "Ejecución", "Monitoreo", "Visualización General", "Ejecución de Lecturación", "Monitoreo de Lecturación" };
            foreach (var m in allMenus.Where(x => juanMenus.Contains(x.NombreMenu)))
            {
                if (!await context.UsuarioMenus.AnyAsync(x => x.IdUsuario == juanUser.IdUsuario && x.IdMenu == m.IdMenu))
                {
                    context.UsuarioMenus.Add(new UsuarioMenu { IdUsuario = juanUser.IdUsuario, IdMenu = m.IdMenu, PuedeVer = true });
                }
            }

            // Pedro permissions
            var pedroMenus = new[] { "Dashboard", "Ejecución", "Monitoreo", "Visualización General", "Ejecución de Cortes", "Monitoreo de Cortes" };
            foreach (var m in allMenus.Where(x => pedroMenus.Contains(x.NombreMenu)))
            {
                if (!await context.UsuarioMenus.AnyAsync(x => x.IdUsuario == pedroUser.IdUsuario && x.IdMenu == m.IdMenu))
                {
                    context.UsuarioMenus.Add(new UsuarioMenu { IdUsuario = pedroUser.IdUsuario, IdMenu = m.IdMenu, PuedeVer = true });
                }
            }
            
            await context.SaveChangesAsync();
        }
    }
}
