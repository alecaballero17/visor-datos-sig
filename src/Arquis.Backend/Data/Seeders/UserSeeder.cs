using System;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data.Seeders
{
    public static class UserSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
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
        }
    }
}
