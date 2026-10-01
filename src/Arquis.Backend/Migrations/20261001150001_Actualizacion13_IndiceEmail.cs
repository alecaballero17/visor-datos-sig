using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arquis.Backend.Migrations
{
    /// <inheritdoc />
    public partial class Actualizacion13_IndiceEmail : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateIndex(
                name: "UX_Usuarios_Email",
                table: "Usuarios",
                column: "Email",
                unique: true,
                filter: "[Email] IS NOT NULL");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "UX_Usuarios_Email",
                table: "Usuarios");
        }
    }
}
