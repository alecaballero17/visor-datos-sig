using System;
using System.Data.SqlClient;

class Program {
    static void Main() {
        var cnStr = "Server=localhost;Database=ArquisDB;Integrated Security=True;TrustServerCertificate=True";
        using var cn = new SqlConnection(cnStr);
        cn.Open();
        var sql = "SELECT CASE WHEN Geom.STGeometryType()='Point' THEN Geom.Long END FROM CodigosFijos";
        try {
            using var cmd = new SqlCommand(sql, cn);
            cmd.ExecuteNonQuery();
            Console.WriteLine("Success");
        } catch (Exception ex) {
            Console.WriteLine(ex.Message);
        }
    }
}
