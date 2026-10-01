using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;

#nullable disable

namespace Arquis.Backend.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Manzanas",
                columns: table => new
                {
                    IdManzana = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IdOrigen = table.Column<int>(type: "int", nullable: true),
                    UV_MZA = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: true),
                    UV = table.Column<string>(type: "nvarchar(15)", maxLength: 15, nullable: true),
                    MZA = table.Column<string>(type: "nvarchar(10)", maxLength: 10, nullable: true),
                    Geom = table.Column<Geometry>(type: "geography", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Manzanas", x => x.IdManzana);
                });

            migrationBuilder.CreateTable(
                name: "MenuOpciones",
                columns: table => new
                {
                    IdMenu = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IdMenuPadre = table.Column<int>(type: "int", nullable: true),
                    Nivel = table.Column<int>(type: "int", nullable: false),
                    NombreMenu = table.Column<string>(type: "nvarchar(100)", maxLength: 100, nullable: false),
                    Url = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    Icono = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: true),
                    Orden = table.Column<int>(type: "int", nullable: false),
                    Estado = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_MenuOpciones", x => x.IdMenu);
                    table.ForeignKey(
                        name: "FK_MenuOpciones_MenuOpciones_IdMenuPadre",
                        column: x => x.IdMenuPadre,
                        principalTable: "MenuOpciones",
                        principalColumn: "IdMenu");
                });

            migrationBuilder.CreateTable(
                name: "Roles",
                columns: table => new
                {
                    IdRol = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    NombreRol = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Descripcion = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: true),
                    Estado = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Roles", x => x.IdRol);
                });

            migrationBuilder.CreateTable(
                name: "Usuarios",
                columns: table => new
                {
                    IdUsuario = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Login = table.Column<string>(type: "nvarchar(50)", maxLength: 50, nullable: false),
                    Nombre = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: false),
                    PasswordHash = table.Column<byte[]>(type: "varbinary(32)", maxLength: 32, nullable: false),
                    PasswordSalt = table.Column<byte[]>(type: "varbinary(32)", maxLength: 32, nullable: false),
                    Iteraciones = table.Column<int>(type: "int", nullable: false),
                    Activo = table.Column<bool>(type: "bit", nullable: false),
                    FechaRegistro = table.Column<DateTime>(type: "datetime2", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Usuarios", x => x.IdUsuario);
                });

            migrationBuilder.CreateTable(
                name: "Vias",
                columns: table => new
                {
                    IdVia = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    OBJECTID = table.Column<int>(type: "int", nullable: true),
                    Nombre = table.Column<string>(type: "nvarchar(40)", maxLength: 40, nullable: true),
                    TipoVia = table.Column<string>(type: "nvarchar(30)", maxLength: 30, nullable: true),
                    OSMID = table.Column<string>(type: "nvarchar(20)", maxLength: 20, nullable: true),
                    Geom = table.Column<Geometry>(type: "geography", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Vias", x => x.IdVia);
                });

            migrationBuilder.CreateTable(
                name: "Lotes",
                columns: table => new
                {
                    IdLote = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IdOrigen = table.Column<int>(type: "int", nullable: true),
                    NroLote = table.Column<string>(type: "nvarchar(15)", maxLength: 15, nullable: true),
                    IdManzana = table.Column<int>(type: "int", nullable: true),
                    Geom = table.Column<Geometry>(type: "geography", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Lotes", x => x.IdLote);
                    table.ForeignKey(
                        name: "FK_Lotes_Manzanas_IdManzana",
                        column: x => x.IdManzana,
                        principalTable: "Manzanas",
                        principalColumn: "IdManzana");
                });

            migrationBuilder.CreateTable(
                name: "UsuarioMenus",
                columns: table => new
                {
                    IdUsuarioMenu = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IdUsuario = table.Column<int>(type: "int", nullable: false),
                    IdMenu = table.Column<int>(type: "int", nullable: false),
                    PuedeVer = table.Column<bool>(type: "bit", nullable: false),
                    PuedeCrear = table.Column<bool>(type: "bit", nullable: false),
                    PuedeEditar = table.Column<bool>(type: "bit", nullable: false),
                    PuedeEliminar = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UsuarioMenus", x => x.IdUsuarioMenu);
                    table.ForeignKey(
                        name: "FK_UsuarioMenus_MenuOpciones_IdMenu",
                        column: x => x.IdMenu,
                        principalTable: "MenuOpciones",
                        principalColumn: "IdMenu",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UsuarioMenus_Usuarios_IdUsuario",
                        column: x => x.IdUsuario,
                        principalTable: "Usuarios",
                        principalColumn: "IdUsuario",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "UsuariosRoles",
                columns: table => new
                {
                    IdUsuarioRol = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    IdUsuario = table.Column<int>(type: "int", nullable: false),
                    IdRol = table.Column<int>(type: "int", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UsuariosRoles", x => x.IdUsuarioRol);
                    table.ForeignKey(
                        name: "FK_UsuariosRoles_Roles_IdRol",
                        column: x => x.IdRol,
                        principalTable: "Roles",
                        principalColumn: "IdRol",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UsuariosRoles_Usuarios_IdUsuario",
                        column: x => x.IdUsuario,
                        principalTable: "Usuarios",
                        principalColumn: "IdUsuario",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "CodigosFijos",
                columns: table => new
                {
                    IdCodigo = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    CodF_SQL = table.Column<int>(type: "int", nullable: true),
                    CodF_SIG = table.Column<string>(type: "nvarchar(25)", maxLength: 25, nullable: true),
                    CodFijo = table.Column<int>(type: "int", nullable: true),
                    Nombre = table.Column<string>(type: "nvarchar(120)", maxLength: 120, nullable: true),
                    Estado = table.Column<byte>(type: "tinyint", nullable: false),
                    FechaCambioEstado = table.Column<DateTime>(type: "datetime2", nullable: false),
                    IdLote = table.Column<int>(type: "int", nullable: true),
                    Longitud = table.Column<double>(type: "float", nullable: true),
                    Latitud = table.Column<double>(type: "float", nullable: true),
                    Geom = table.Column<Geometry>(type: "geography", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CodigosFijos", x => x.IdCodigo);
                    table.ForeignKey(
                        name: "FK_CodigosFijos_Lotes_IdLote",
                        column: x => x.IdLote,
                        principalTable: "Lotes",
                        principalColumn: "IdLote");
                });

            migrationBuilder.CreateIndex(
                name: "IX_CodigosFijos_CodFijo",
                table: "CodigosFijos",
                column: "CodFijo");

            migrationBuilder.CreateIndex(
                name: "IX_CodigosFijos_Estado",
                table: "CodigosFijos",
                column: "Estado");

            migrationBuilder.CreateIndex(
                name: "IX_CodigosFijos_IdLote",
                table: "CodigosFijos",
                column: "IdLote");

            migrationBuilder.CreateIndex(
                name: "IX_CodigosFijos_Nombre",
                table: "CodigosFijos",
                column: "Nombre");

            migrationBuilder.CreateIndex(
                name: "IX_Lotes_IdManzana",
                table: "Lotes",
                column: "IdManzana");

            migrationBuilder.CreateIndex(
                name: "IX_Lotes_NroLote",
                table: "Lotes",
                column: "NroLote");

            migrationBuilder.CreateIndex(
                name: "IX_Manzanas_UV_MZA",
                table: "Manzanas",
                columns: new[] { "UV", "MZA" });

            migrationBuilder.CreateIndex(
                name: "IX_MenuOpciones_IdMenuPadre",
                table: "MenuOpciones",
                column: "IdMenuPadre");

            migrationBuilder.CreateIndex(
                name: "IX_Roles_NombreRol",
                table: "Roles",
                column: "NombreRol",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_UsuarioMenus_IdMenu",
                table: "UsuarioMenus",
                column: "IdMenu");

            migrationBuilder.CreateIndex(
                name: "IX_UsuarioMenus_IdUsuario_IdMenu",
                table: "UsuarioMenus",
                columns: new[] { "IdUsuario", "IdMenu" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Usuarios_Login",
                table: "Usuarios",
                column: "Login",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_UsuariosRoles_IdRol",
                table: "UsuariosRoles",
                column: "IdRol");

            migrationBuilder.CreateIndex(
                name: "IX_UsuariosRoles_IdUsuario_IdRol",
                table: "UsuariosRoles",
                columns: new[] { "IdUsuario", "IdRol" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "CodigosFijos");

            migrationBuilder.DropTable(
                name: "UsuarioMenus");

            migrationBuilder.DropTable(
                name: "UsuariosRoles");

            migrationBuilder.DropTable(
                name: "Vias");

            migrationBuilder.DropTable(
                name: "Lotes");

            migrationBuilder.DropTable(
                name: "MenuOpciones");

            migrationBuilder.DropTable(
                name: "Roles");

            migrationBuilder.DropTable(
                name: "Usuarios");

            migrationBuilder.DropTable(
                name: "Manzanas");
        }
    }
}
