using System;
using System.Data.SqlClient;

class Program {
    static void Main() {
        var cnStr = "Server=.\\SQLSERVER;Database=VisorDatosSIG;Trusted_Connection=True;TrustServerCertificate=True;";
        using (var cn = new SqlConnection(cnStr)) {
            cn.Open();
            var sql = "SELECT TOP 1 CASE WHEN Geom.STGeometryType()='Point' THEN Geom.Long END FROM CodigosFijos WHERE Geom IS NOT NULL";
            try {
                using (var cmd = new SqlCommand(sql, cn)) {
                    cmd.ExecuteNonQuery();
                    Console.WriteLine("Success");
                }
            } catch (Exception ex) {
                Console.WriteLine(ex.Message);
            }
        }
    }
}
