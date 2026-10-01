using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data
{
    public static class DbSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            // 1. Seed Roles
            var rolesToSeed = new[]
            {
                new Rol { NombreRol = "Administrador", Descripcion = "Administrador del Sistema", Estado = true },
                new Rol { NombreRol = "Catastro", Descripcion = "Rol para crear, modificar y eliminar Manzanas, Lotes, Codigo Fijo y Vias", Estado = true },
                new Rol { NombreRol = "Lecturador", Descripcion = "Rol para lecturar medidores", Estado = true },
                new Rol { NombreRol = "Cortador", Descripcion = "Rol para cortar servicios", Estado = true },
                new Rol { NombreRol = "Reconexion", Descripcion = "Rol para la reconnexion por corte", Estado = true },
                new Rol { NombreRol = "Consultor", Descripcion = "Consulta del visor cartográfico", Estado = true }
            };

            foreach (var r in rolesToSeed)
            {
                if (!await context.Roles.AnyAsync(x => x.NombreRol == r.NombreRol))
                {
                    context.Roles.Add(r);
                }
            }
            await context.SaveChangesAsync();

            // 2. Seed Usuarios
            byte[] StringToByteArray(string hex)
            {
                if (hex.StartsWith("0x")) hex = hex.Substring(2);
                int NumberChars = hex.Length;
                byte[] bytes = new byte[NumberChars / 2];
                for (int i = 0; i < NumberChars; i += 2)
                    bytes[i / 2] = Convert.ToByte(hex.Substring(i, 2), 16);
                return bytes;
            }

            var adminHash = StringToByteArray("0x599F3972C925D7D968B215FB5385865FDF961BCA18BB332E13AB9F014903F89B");
            var adminSalt = StringToByteArray("0x82A4FC4EE67761C1A4E95BCD6BF9CF9B63344B9E665C839C8F9F654D1718B665");

            var juanHash = StringToByteArray("0xB14BC9A077C4CC29BC030A25AD517456D88224BBB57ECA2C5D977C4E85131676");
            var juanSalt = StringToByteArray("0x3F2B95B127A4E8C161A840BDF72EA6623E318F7969B3CCF7A7B66BA33A90D89C");

            var pedroHash = StringToByteArray("0xC1BA4D699543F1E1D12C302CD0FD1BB4DDECF6A9C55620B9CC718E918930A528");
            var pedroSalt = StringToByteArray("0xA4E75D92036F1B847CD4298A18D3F16B2746AE50A81683CD375943EE15F7BD01");

            var usuariosToSeed = new[]
            {
                new Usuario { Login = "admin", Nombre = "Administrador", PasswordHash = adminHash, PasswordSalt = adminSalt, Iteraciones = 100000, Activo = true, FechaRegistro = DateTime.UtcNow },
                new Usuario { Login = "Juan", Nombre = "Juan", PasswordHash = juanHash, PasswordSalt = juanSalt, Iteraciones = 100000, Activo = true, FechaRegistro = DateTime.UtcNow },
                new Usuario { Login = "Pedro", Nombre = "Pedro", PasswordHash = pedroHash, PasswordSalt = pedroSalt, Iteraciones = 100000, Activo = true, FechaRegistro = DateTime.UtcNow }
            };

            foreach (var u in usuariosToSeed)
            {
                if (!await context.Usuarios.AnyAsync(x => x.Login == u.Login))
                {
                    context.Usuarios.Add(u);
                }
            }
            await context.SaveChangesAsync();

            // 3. Seed UsuariosRoles
            var adminUser = await context.Usuarios.FirstAsync(x => x.Login == "admin");
            var juanUser = await context.Usuarios.FirstAsync(x => x.Login == "Juan");
            var pedroUser = await context.Usuarios.FirstAsync(x => x.Login == "Pedro");

            var adminRole = await context.Roles.FirstAsync(x => x.NombreRol == "Administrador");
            var lecturadorRole = await context.Roles.FirstAsync(x => x.NombreRol == "Lecturador");
            var cortadorRole = await context.Roles.FirstAsync(x => x.NombreRol == "Cortador");

            var userRoles = new[]
            {
                new { U = adminUser.IdUsuario, R = adminRole.IdRol },
                new { U = juanUser.IdUsuario, R = lecturadorRole.IdRol },
                new { U = pedroUser.IdUsuario, R = cortadorRole.IdRol }
            };

            foreach (var ur in userRoles)
            {
                if (!await context.UsuariosRoles.AnyAsync(x => x.IdUsuario == ur.U && x.IdRol == ur.R))
                {
                    context.UsuariosRoles.Add(new UsuarioRol { IdUsuario = ur.U, IdRol = ur.R });
                }
            }
            await context.SaveChangesAsync();

            // 4. Seed Menus Nivel 1
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

            // 5. Seed Menus Nivel 2
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

            // 6. Seed UsuarioMenu
            var allMenus = await context.MenuOpciones.ToListAsync();
            
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
