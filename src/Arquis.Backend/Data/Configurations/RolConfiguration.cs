using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class RolConfiguration : IEntityTypeConfiguration<Rol> {
        public void Configure(EntityTypeBuilder<Rol> builder) {
            builder.HasKey(x => x.IdRol);
            builder.HasIndex(x => x.NombreRol).IsUnique();
            builder.Property(x => x.NombreRol).HasMaxLength(50);
            builder.Property(x => x.Descripcion).HasMaxLength(200);
        }
    }
}
