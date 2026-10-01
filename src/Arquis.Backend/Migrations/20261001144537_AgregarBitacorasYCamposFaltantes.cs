using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arquis.Backend.Migrations
{
    /// <inheritdoc />
    public partial class AgregarBitacorasYCamposFaltantes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Email",
                table: "Usuarios",
                type: "nvarchar(254)",
                maxLength: 254,
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "EstadoVerificado",
                table: "CodigosFijos",
                type: "bit",
                nullable: false,
                defaultValue: false);

            migrationBuilder.CreateTable(
                name: "BitacoraAccesos",
                columns: table => new
                {
                    IdBitacora = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Fecha = table.Column<DateTime>(type: "datetime2", nullable: false),
                    Login = table.Column<string>(type: "nvarchar(254)", maxLength: 254, nullable: false),
                    Exitoso = table.Column<bool>(type: "bit", nullable: false),
                    Ip = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: true),
                    Detalle = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_BitacoraAccesos", x => x.IdBitacora);
                });

            migrationBuilder.CreateTable(
                name: "BitacoraMigraciones",
                columns: table => new
                {
                    IdMigracion = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    FechaInicio = table.Column<DateTime>(type: "datetime2", nullable: false),
                    FechaFin = table.Column<DateTime>(type: "datetime2", nullable: true),
                    Usuario = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Capa = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Archivo = table.Column<string>(type: "nvarchar(260)", maxLength: 260, nullable: false),
                    TablaDestino = table.Column<string>(type: "nvarchar(128)", maxLength: 128, nullable: false),
                    Modalidad = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Procesados = table.Column<int>(type: "int", nullable: false),
                    Exitosos = table.Column<int>(type: "int", nullable: false),
                    Omitidos = table.Column<int>(type: "int", nullable: false),
                    Fallidos = table.Column<int>(type: "int", nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: false),
                    Detalle = table.Column<string>(type: "nvarchar(max)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_BitacoraMigraciones", x => x.IdMigracion);
                });

            migrationBuilder.CreateIndex(
                name: "IX_BitacoraAccesos_Fecha",
                table: "BitacoraAccesos",
                column: "Fecha",
                descending: new bool[0]);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "BitacoraAccesos");

            migrationBuilder.DropTable(
                name: "BitacoraMigraciones");

            migrationBuilder.DropColumn(
                name: "Email",
                table: "Usuarios");

            migrationBuilder.DropColumn(
                name: "EstadoVerificado",
                table: "CodigosFijos");
        }
    }
}
