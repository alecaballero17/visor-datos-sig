using System;
using System.Data.SqlClient;

class Program {
    static void Main() {
        var cnStr = "Server=.\\SQLSERVER;Database=VisorDatosSIG;Trusted_Connection=True;TrustServerCertificate=True;";
        using (var cn = new SqlConnection(cnStr)) {
            cn.Open();
            var sql = @"
            SELECT c.IdCodigo,c.CodFijo,c.CodF_SIG,c.Nombre,c.Estado,c.EstadoVerificado,
                   CASE WHEN 0=1 THEN 912 ELSE c.IdLote END AS IdLote,l.NroLote,m.UV,m.MZA,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.Long END AS Longitud,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.Lat END AS Latitud
            FROM dbo.CodigosFijos c
            LEFT JOIN dbo.Lotes l ON l.IdLote=CASE WHEN 0=1 THEN 912 ELSE c.IdLote END
            LEFT JOIN dbo.Manzanas m ON m.IdManzana=l.IdManzana
            WHERE c.IdCodigo=912 ORDER BY c.IdCodigo";
            try {
                using (var cmd = new SqlCommand(sql, cn)) {
                    using (var reader = cmd.ExecuteReader()) {
                        while (reader.Read()) {
                            Console.WriteLine("Read row");
                        }
                    }
                    Console.WriteLine("Success");
                }
            } catch (Exception ex) {
                Console.WriteLine(ex.Message);
            }
        }
    }
}
