using System.Collections.Generic;
namespace Arquis.Backend.Models.Entities {
    public class MenuOpcion {
        public int IdMenu { get; set; }
        public int? IdMenuPadre { get; set; }
        public int Nivel { get; set; }
        public string NombreMenu { get; set; } = null!;
        public string? Url { get; set; }
        public string? Icono { get; set; }
        public int Orden { get; set; } = 0;
        public bool Estado { get; set; } = true;
        public MenuOpcion? MenuPadre { get; set; }
        public ICollection<MenuOpcion> SubMenus { get; set; } = new List<MenuOpcion>();
        public ICollection<UsuarioMenu> UsuarioMenus { get; set; } = new List<UsuarioMenu>();
    }
}
