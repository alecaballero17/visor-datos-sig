using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class UsuarioRolConfiguration : IEntityTypeConfiguration<UsuarioRol> {
        public void Configure(EntityTypeBuilder<UsuarioRol> builder) {
            builder.HasKey(x => x.IdUsuarioRol);
            builder.HasIndex(x => new { x.IdUsuario, x.IdRol }).IsUnique();
            builder.HasOne(x => x.Usuario).WithMany(u => u.UsuariosRoles).HasForeignKey(x => x.IdUsuario);
            builder.HasOne(x => x.Rol).WithMany(r => r.UsuariosRoles).HasForeignKey(x => x.IdRol);
        }
    }
}
