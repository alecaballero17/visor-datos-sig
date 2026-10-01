using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using Arquis.Backend.Models.Entities;
namespace Arquis.Backend.Data.Configurations {
    public class MenuOpcionConfiguration : IEntityTypeConfiguration<MenuOpcion> {
        public void Configure(EntityTypeBuilder<MenuOpcion> builder) {
            builder.HasKey(x => x.IdMenu);
            builder.Property(x => x.NombreMenu).HasMaxLength(100);
            builder.Property(x => x.Url).HasMaxLength(200);
            builder.Property(x => x.Icono).HasMaxLength(50);
            builder.HasOne(x => x.MenuPadre).WithMany(m => m.SubMenus).HasForeignKey(x => x.IdMenuPadre);
        }
    }
}
