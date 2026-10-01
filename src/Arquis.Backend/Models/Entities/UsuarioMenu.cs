namespace Arquis.Backend.Models.Entities {
    public class UsuarioMenu {
        public int IdUsuarioMenu { get; set; }
        public int IdUsuario { get; set; }
        public int IdMenu { get; set; }
        public bool PuedeVer { get; set; } = true;
        public bool PuedeCrear { get; set; } = false;
        public bool PuedeEditar { get; set; } = false;
        public bool PuedeEliminar { get; set; } = false;
        public Usuario Usuario { get; set; } = null!;
        public MenuOpcion Menu { get; set; } = null!;
    }
}
