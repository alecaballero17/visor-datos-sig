using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class BitacoraAccesoConfiguration : IEntityTypeConfiguration<BitacoraAcceso> {
        public void Configure(EntityTypeBuilder<BitacoraAcceso> builder) {
            builder.HasKey(x => x.IdBitacora);
            builder.Property(x => x.Login).HasMaxLength(254).IsRequired();
            builder.Property(x => x.Ip).HasMaxLength(64);
            builder.Property(x => x.Detalle).HasMaxLength(500);
            builder.HasIndex(x => x.Fecha).IsDescending();
        }
    }
}
