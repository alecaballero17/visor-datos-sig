using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class UsuarioMenuConfiguration : IEntityTypeConfiguration<UsuarioMenu> {
        public void Configure(EntityTypeBuilder<UsuarioMenu> builder) {
            builder.HasKey(x => x.IdUsuarioMenu);
            builder.HasIndex(x => new { x.IdUsuario, x.IdMenu }).IsUnique();
            builder.HasOne(x => x.Usuario).WithMany(u => u.UsuarioMenus).HasForeignKey(x => x.IdUsuario);
            builder.HasOne(x => x.Menu).WithMany(m => m.UsuarioMenus).HasForeignKey(x => x.IdMenu);
        }
    }
}
