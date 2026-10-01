using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class ViaConfiguration : IEntityTypeConfiguration<Via> {
        public void Configure(EntityTypeBuilder<Via> builder) {
            builder.HasKey(x => x.IdVia);
            builder.Property(x => x.Nombre).HasMaxLength(200);
            builder.Property(x => x.TipoVia).HasMaxLength(100);
            builder.Property(x => x.OSMID).HasMaxLength(50);
        }
    }
}
