using System;
using System.Collections.Generic;
namespace Arquis.Backend.Models.Entities {
    public class Usuario {
        public int IdUsuario { get; set; }
        public string Login { get; set; } = null!;
        public string Nombre { get; set; } = null!;
        public byte[] PasswordHash { get; set; } = null!;
        public byte[] PasswordSalt { get; set; } = null!;
        public int Iteraciones { get; set; } = 100000;
        public bool Activo { get; set; } = true;
        public DateTime FechaRegistro { get; set; } = DateTime.UtcNow;
        public string? Email { get; set; }
        public ICollection<UsuarioRol> UsuariosRoles { get; set; } = new List<UsuarioRol>();
        public ICollection<UsuarioMenu> UsuarioMenus { get; set; } = new List<UsuarioMenu>();
    }
}
