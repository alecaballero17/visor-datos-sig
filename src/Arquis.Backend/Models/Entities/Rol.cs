using System.Collections.Generic;
namespace Arquis.Backend.Models.Entities {
    public class Rol {
        public int IdRol { get; set; }
        public string NombreRol { get; set; } = null!;
        public string? Descripcion { get; set; }
        public bool Estado { get; set; } = true;
        public ICollection<UsuarioRol> UsuariosRoles { get; set; } = new List<UsuarioRol>();
    }
}
