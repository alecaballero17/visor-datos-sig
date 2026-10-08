using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data.Configurations
{
    public class BitacoraReporteConfiguration : IEntityTypeConfiguration<BitacoraReporte>
    {
        public void Configure(EntityTypeBuilder<BitacoraReporte> builder)
        {
            builder.ToTable("BitacoraReportes");
            builder.HasKey(x => x.IdBitacora);
            builder.Property(x => x.Usuario).HasMaxLength(254).IsRequired();
            builder.Property(x => x.TipoReporte).HasMaxLength(64).IsRequired();
            builder.Property(x => x.Referencia).HasMaxLength(254).IsRequired();
            builder.Property(x => x.Accion).HasMaxLength(128).IsRequired();
            builder.Property(x => x.Detalle).HasMaxLength(1000);
            builder.Property(x => x.Ip).HasMaxLength(64);
            builder.HasIndex(x => x.Fecha).IsDescending();
        }
    }
}
