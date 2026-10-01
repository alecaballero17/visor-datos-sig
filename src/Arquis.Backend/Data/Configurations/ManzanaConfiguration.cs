using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class ManzanaConfiguration : IEntityTypeConfiguration<Manzana> {
        public void Configure(EntityTypeBuilder<Manzana> builder) {
            builder.HasKey(x => x.IdManzana);
            builder.Property(x => x.UV_MZA).HasMaxLength(100);
            builder.Property(x => x.UV).HasMaxLength(100);
            builder.Property(x => x.MZA).HasMaxLength(50);
            builder.HasIndex(x => new { x.UV, x.MZA });
        }
    }
}
