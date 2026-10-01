using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class CodigoFijoConfiguration : IEntityTypeConfiguration<CodigoFijo> {
        public void Configure(EntityTypeBuilder<CodigoFijo> builder) {
            builder.HasKey(x => x.IdCodigo);
            builder.Property(x => x.CodF_SIG).HasMaxLength(25);
            builder.Property(x => x.Nombre).HasMaxLength(120);
            builder.HasIndex(x => x.CodFijo);
            builder.HasIndex(x => x.Nombre);
            builder.HasIndex(x => x.Estado);
            builder.Property(x => x.EstadoVerificado).HasDefaultValue(false);
            builder.HasIndex(x => x.IdLote);
            builder.HasOne(x => x.Lote).WithMany(l => l.CodigosFijos).HasForeignKey(x => x.IdLote);
            builder.ToTable(t => t.HasCheckConstraint("CK_CodigosFijos_Estado", "Estado BETWEEN 1 AND 5"));
        }
    }
}
