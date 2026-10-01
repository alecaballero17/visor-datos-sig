using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class UsuarioConfiguration : IEntityTypeConfiguration<Usuario> {
        public void Configure(EntityTypeBuilder<Usuario> builder) {
            builder.HasKey(x => x.IdUsuario);
            builder.HasIndex(x => x.Login).IsUnique();
            builder.Property(x => x.Login).HasMaxLength(50);
            builder.Property(x => x.Email).HasMaxLength(254);
            builder.HasIndex(x => x.Email).IsUnique().HasDatabaseName("UX_Usuarios_Email").HasFilter("[Email] IS NOT NULL");
            builder.Property(x => x.Nombre).HasMaxLength(120);
            builder.Property(x => x.PasswordHash).HasMaxLength(32);
            builder.Property(x => x.PasswordSalt).HasMaxLength(32);
        }
    }
}
