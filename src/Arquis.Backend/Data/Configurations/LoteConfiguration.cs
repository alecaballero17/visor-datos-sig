using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class LoteConfiguration : IEntityTypeConfiguration<Lote> {
        public void Configure(EntityTypeBuilder<Lote> builder) {
            builder.HasKey(x => x.IdLote);
            builder.Property(x => x.NroLote).HasMaxLength(15);
            builder.HasIndex(x => x.NroLote);
            builder.HasOne(x => x.Manzana).WithMany(m => m.Lotes).HasForeignKey(x => x.IdManzana);
        }
    }
}
