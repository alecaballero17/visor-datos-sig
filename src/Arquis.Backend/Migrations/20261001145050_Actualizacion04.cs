using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arquis.Backend.Migrations
{
    /// <inheritdoc />
    public partial class Actualizacion04 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddCheckConstraint(
                name: "CK_CodigosFijos_Estado",
                table: "CodigosFijos",
                sql: "Estado BETWEEN 1 AND 5");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "CK_CodigosFijos_Estado",
                table: "CodigosFijos");
        }
    }
}
