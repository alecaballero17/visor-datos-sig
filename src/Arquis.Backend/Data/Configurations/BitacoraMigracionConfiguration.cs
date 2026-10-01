using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class BitacoraMigracionConfiguration : IEntityTypeConfiguration<BitacoraMigracion> {
        public void Configure(EntityTypeBuilder<BitacoraMigracion> builder) {
            builder.HasKey(x => x.IdMigracion);
            builder.Property(x => x.Usuario).HasMaxLength(50);
            builder.Property(x => x.Capa).HasMaxLength(50);
            builder.Property(x => x.Archivo).HasMaxLength(260);
            builder.Property(x => x.TablaDestino).HasMaxLength(128);
            builder.Property(x => x.Modalidad).HasMaxLength(20);
            builder.Property(x => x.Estado).HasMaxLength(20);
        }
    }
}
