using Arquis.Backend.Data;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace Arquis.Backend.Migrations;

[DbContext(typeof(ArquisDbContext))]
[Migration("20261103120000_CandidatosReconexion")]
public class CandidatosReconexion : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        // Compatible con bases preparadas manualmente usando 02_BaseDatos.
        migrationBuilder.Sql("""
            IF EXISTS (SELECT 1 FROM sys.check_constraints
                       WHERE name = N'CK_CodigosFijos_Estado'
                         AND parent_object_id = OBJECT_ID(N'dbo.CodigosFijos'))
                ALTER TABLE dbo.CodigosFijos DROP CONSTRAINT CK_CodigosFijos_Estado;
            ALTER TABLE dbo.CodigosFijos WITH CHECK
                ADD CONSTRAINT CK_CodigosFijos_Estado CHECK (Estado BETWEEN 0 AND 5);
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        // No reclasificar silenciosamente candidatos existentes al revertir.
        migrationBuilder.Sql("""
            IF EXISTS (SELECT 1 FROM dbo.CodigosFijos WHERE Estado = 0)
                THROW 51000, 'No se puede revertir mientras existan candidatos a reconexion.', 1;
            ALTER TABLE dbo.CodigosFijos DROP CONSTRAINT CK_CodigosFijos_Estado;
            ALTER TABLE dbo.CodigosFijos WITH CHECK
                ADD CONSTRAINT CK_CodigosFijos_Estado CHECK (Estado BETWEEN 1 AND 5);
            """);
    }
}
