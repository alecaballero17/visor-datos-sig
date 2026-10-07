using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data
{
    public class ArquisDbContext : DbContext
    {
        public ArquisDbContext(DbContextOptions<ArquisDbContext> options) : base(options)
        {
        }

        public DbSet<Usuario> Usuarios { get; set; } = null!;
        public DbSet<Rol> Roles { get; set; } = null!;
        public DbSet<UsuarioRol> UsuariosRoles { get; set; } = null!;
        public DbSet<MenuOpcion> MenuOpciones { get; set; } = null!;
        public DbSet<UsuarioMenu> UsuarioMenus { get; set; } = null!;
        public DbSet<CodigoFijo> CodigosFijos { get; set; } = null!;
        public DbSet<Manzana> Manzanas { get; set; } = null!;
        public DbSet<Lote> Lotes { get; set; } = null!;
        public DbSet<Via> Vias { get; set; } = null!;
        public DbSet<BitacoraAcceso> BitacoraAccesos { get; set; } = null!;
        public DbSet<BitacoraMigracion> BitacoraMigraciones { get; set; } = null!;
        public DbSet<BitacoraReporte> BitacoraReportes { get; set; } = null!;

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
            modelBuilder.ApplyConfigurationsFromAssembly(System.Reflection.Assembly.GetExecutingAssembly());
        }
    }
}
