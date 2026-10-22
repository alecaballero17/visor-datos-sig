using System.Data;
using System.Security.Claims;
using System.Security.Cryptography;
using Arquis.Backend.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Controllers;

[ApiController]
[Authorize(Roles="Administrador")]
[Route("api/administracion")]
public sealed class AdministracionController(SqlConnectionFactory connections) : ControllerBase
{
    private const int PasswordIterations=210000;

    [HttpGet("empleados")]
    public async Task<IActionResult> Empleados([FromQuery] string rol, CancellationToken ct)
    {
        if (rol is not ("Cortador" or "Conector")) return BadRequest(new { mensaje="Seleccione Cortador o Conector." });
        const string sql="""
            SELECT u.IdUsuario,u.Login,u.Nombre,r.NombreRol AS Rol
            FROM dbo.Usuarios u
            JOIN dbo.UsuariosRoles ur ON ur.IdUsuario=u.IdUsuario
            JOIN dbo.Roles r ON r.IdRol=ur.IdRol AND r.Estado=1
            WHERE u.Activo=1 AND r.NombreRol=@Rol
            ORDER BY u.Nombre,u.Login;
            """;
        await using var cn=connections.Create(); await cn.OpenAsync(ct);
        await using var cmd=new SqlCommand(sql,cn);
        cmd.Parameters.Add(new SqlParameter("@Rol",SqlDbType.VarChar,50){Value=rol});
        await using var rd=await cmd.ExecuteReaderAsync(ct);
        var rows=new List<object>();
        while(await rd.ReadAsync(ct)) rows.Add(new { id=(int)rd["IdUsuario"],login=(string)rd["Login"],nombre=(string)rd["Nombre"],rol=(string)rd["Rol"] });
        return Ok(rows);
    }

    [HttpPost("empleados")]
    public async Task<IActionResult> CrearEmpleado([FromBody] CrearEmpleadoRequest request, CancellationToken ct)
    {
        var login=request.Login.Trim();
        var nombre=request.Nombre.Trim();
        if (login.Length is < 2 or > 50 || nombre.Length is < 2 or > 120 || request.Password.Length is < 8 or > 128)
            return BadRequest(new { mensaje="Revise login (2–50), nombre (2–120) y contraseña (8–128 caracteres)." });
        if (request.Rol is not ("Cortador" or "Conector"))
            return BadRequest(new { mensaje="El rol operativo debe ser Cortador o Conector." });

        var salt=RandomNumberGenerator.GetBytes(32);
        var hash=Rfc2898DeriveBytes.Pbkdf2(request.Password,salt,PasswordIterations,HashAlgorithmName.SHA256,32);
        const string sql="""
            DECLARE @Rol int=(SELECT IdRol FROM dbo.Roles WHERE NombreRol=@RolNombre AND Estado=1);
            IF @Rol IS NULL THROW 52001,'El rol operativo no está instalado.',1;
            IF EXISTS(SELECT 1 FROM dbo.Usuarios WHERE Login=@Login)
                THROW 52002,'Ese login ya está registrado.',1;
            INSERT dbo.Usuarios(Login,Nombre,PasswordHash,PasswordSalt,Iteraciones,Activo)
            VALUES(@Login,@Nombre,@Hash,@Salt,@Iteraciones,1);
            DECLARE @Id int=CONVERT(int,SCOPE_IDENTITY());
            INSERT dbo.UsuariosRoles(IdUsuario,IdRol) VALUES(@Id,@Rol);
            SELECT @Id;
            """;
        await using var cn=connections.Create(); await cn.OpenAsync(ct);
        await using var tx=(SqlTransaction)await cn.BeginTransactionAsync(IsolationLevel.Serializable,ct);
        await using var cmd=new SqlCommand(sql,cn,tx);
        cmd.Parameters.Add(new SqlParameter("@Login",SqlDbType.NVarChar,50){Value=login});
        cmd.Parameters.Add(new SqlParameter("@Nombre",SqlDbType.NVarChar,120){Value=nombre});
        cmd.Parameters.Add(new SqlParameter("@Hash",SqlDbType.VarBinary,32){Value=hash});
        cmd.Parameters.Add(new SqlParameter("@Salt",SqlDbType.VarBinary,32){Value=salt});
        cmd.Parameters.Add(new SqlParameter("@Iteraciones",SqlDbType.Int){Value=PasswordIterations});
        cmd.Parameters.Add(new SqlParameter("@RolNombre",SqlDbType.VarChar,50){Value=request.Rol});
        try
        {
            var id=Convert.ToInt32(await cmd.ExecuteScalarAsync(ct));
            await tx.CommitAsync(ct);
            return Created($"/api/administracion/empleados?rol={request.Rol}",new { id,login,nombre,rol=request.Rol });
        }
        catch(SqlException ex) when(ex.Number is 2601 or 2627 or 52002)
        {
            await tx.RollbackAsync(ct);
            return Conflict(new { mensaje="Ese login ya está registrado." });
        }
    }

    [HttpGet("asignaciones")]
    public async Task<IActionResult> Asignaciones(CancellationToken ct)
    {
        const string sql="""
            SELECT TOP(100) o.IdOrden,o.IdCodigo,o.TipoTrabajo,o.Estado,o.FechaAsignacion,
                   u.Login AS EmpleadoLogin,u.Nombre AS EmpleadoNombre,
                   c.CodFijo,c.CodF_SIG,c.Nombre AS ServicioNombre,c.Estado AS EstadoServicio,c.EstadoVerificado,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.STX ELSE c.Longitud END AS Longitud,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.STY ELSE c.Latitud END AS Latitud
            FROM dbo.OrdenesTrabajo o
            JOIN dbo.Usuarios u ON u.IdUsuario=o.IdEmpleado
            JOIN dbo.CodigosFijos c ON c.IdCodigo=o.IdCodigo
            ORDER BY CASE o.Estado WHEN 'Pendiente' THEN 0 ELSE 1 END,o.FechaAsignacion DESC,o.IdOrden DESC;
            """;
        await using var cn=connections.Create(); await cn.OpenAsync(ct);
        await using var cmd=new SqlCommand(sql,cn); await using var rd=await cmd.ExecuteReaderAsync(ct);
        var rows=new List<object>();
        while(await rd.ReadAsync(ct))
        {
            object? Value(string name)=>rd[name] is DBNull?null:rd[name];
            rows.Add(new {
                idOrden=(long)rd["IdOrden"],idCodigo=(int)rd["IdCodigo"],tipoTrabajo=(string)rd["TipoTrabajo"],
                estado=(string)rd["Estado"],fechaAsignacion=(DateTime)rd["FechaAsignacion"],
                empleadoLogin=(string)rd["EmpleadoLogin"],empleadoNombre=(string)rd["EmpleadoNombre"],
                codigoFijo=Value("CodFijo"),codigoSig=Value("CodF_SIG"),nombreServicio=Value("ServicioNombre"),
                estadoServicio=(byte)rd["EstadoServicio"],estadoVerificado=(bool)rd["EstadoVerificado"],
                longitud=Value("Longitud"),latitud=Value("Latitud")
            });
        }
        return Ok(rows);
    }

    [HttpPost("asignaciones")]
    public async Task<IActionResult> CrearAsignacion([FromBody] CrearAsignacionRequest request, CancellationToken ct)
    {
        if(request.IdCodigo<1 || request.IdEmpleado<1 || request.TipoTrabajo is not ("Corte" or "Reconexion"))
            return BadRequest(new { mensaje="Código, empleado o tipo de trabajo no válido." });
        if(!int.TryParse(User.FindFirstValue(ClaimTypes.NameIdentifier),out var idAdmin)) return Unauthorized();

        await using var cn=connections.Create(); await cn.OpenAsync(ct);
        await using var tx=(SqlTransaction)await cn.BeginTransactionAsync(IsolationLevel.Serializable,ct);
        try
        {
            const string employeeSql="""
                SELECT TOP(1) u.IdUsuario
                FROM dbo.Usuarios u WITH(UPDLOCK,HOLDLOCK)
                JOIN dbo.UsuariosRoles ur ON ur.IdUsuario=u.IdUsuario
                JOIN dbo.Roles r ON r.IdRol=ur.IdRol AND r.Estado=1
                WHERE u.IdUsuario=@IdEmpleado AND u.Activo=1
                  AND r.NombreRol=CASE @Tipo WHEN 'Corte' THEN 'Cortador' ELSE 'Conector' END;
                """;
            await using(var employee=new SqlCommand(employeeSql,cn,tx))
            {
                employee.Parameters.Add(new SqlParameter("@IdEmpleado",SqlDbType.Int){Value=request.IdEmpleado});
                employee.Parameters.Add(new SqlParameter("@Tipo",SqlDbType.VarChar,20){Value=request.TipoTrabajo});
                if(await employee.ExecuteScalarAsync(ct) is null)
                {
                    await tx.RollbackAsync(ct);
                    return BadRequest(new { mensaje=request.TipoTrabajo=="Corte"?"Seleccione un empleado activo con rol Cortador.":"Seleccione un empleado activo con rol Conector." });
                }
            }

            const string codeSql="""
                SELECT Estado,
                       CASE WHEN Geom IS NOT NULL AND Geom.STGeometryType()='Point' THEN 1 ELSE 0 END AS TienePunto
                FROM dbo.CodigosFijos WITH(UPDLOCK,HOLDLOCK)
                WHERE IdCodigo=@IdCodigo;
                """;
            byte estadoServicio;
            bool tienePunto;
            await using(var code=new SqlCommand(codeSql,cn,tx))
            {
                code.Parameters.Add(new SqlParameter("@IdCodigo",SqlDbType.Int){Value=request.IdCodigo});
                await using var rd=await code.ExecuteReaderAsync(ct);
                if(!await rd.ReadAsync(ct))
                {
                    await rd.DisposeAsync(); await tx.RollbackAsync(ct);
                    return NotFound(new { mensaje="No existe ese código fijo." });
                }
                estadoServicio=Convert.ToByte(rd["Estado"]);
                tienePunto=Convert.ToInt32(rd["TienePunto"])==1;
            }
            if(!tienePunto)
            {
                await tx.RollbackAsync(ct);
                return Conflict(new { mensaje="El código fijo no tiene un punto geográfico válido." });
            }
            if(request.TipoTrabajo=="Corte" && estadoServicio!=1)
            {
                await tx.RollbackAsync(ct);
                return Conflict(new { mensaje="Solo se puede asignar un corte a un servicio Normal." });
            }
            if(request.TipoTrabajo=="Reconexion" && estadoServicio!=3)
            {
                await tx.RollbackAsync(ct);
                return Conflict(new { mensaje="Solo se puede asignar una reconexión a un servicio Cortado." });
            }

            const string pendingSql="SELECT COUNT_BIG(1) FROM dbo.OrdenesTrabajo WITH(UPDLOCK,HOLDLOCK) WHERE IdCodigo=@IdCodigo AND Estado='Pendiente';";
            await using(var pending=new SqlCommand(pendingSql,cn,tx))
            {
                pending.Parameters.Add(new SqlParameter("@IdCodigo",SqlDbType.Int){Value=request.IdCodigo});
                if(Convert.ToInt64(await pending.ExecuteScalarAsync(ct))>0)
                {
                    await tx.RollbackAsync(ct);
                    return Conflict(new { mensaje="Ese punto ya tiene una asignación pendiente." });
                }
            }

            const string insertSql="""
                INSERT dbo.OrdenesTrabajo(IdCodigo,TipoTrabajo,IdEmpleado,IdAsignador,Estado)
                VALUES(@IdCodigo,@Tipo,@IdEmpleado,@IdAdmin,'Pendiente');
                DECLARE @IdOrden BIGINT=CONVERT(BIGINT,SCOPE_IDENTITY());
                IF @Tipo='Corte' UPDATE dbo.CodigosFijos SET Estado=2 WHERE IdCodigo=@IdCodigo;
                SELECT @IdOrden;
                """;
            await using var insert=new SqlCommand(insertSql,cn,tx);
            insert.Parameters.Add(new SqlParameter("@IdCodigo",SqlDbType.Int){Value=request.IdCodigo});
            insert.Parameters.Add(new SqlParameter("@Tipo",SqlDbType.VarChar,20){Value=request.TipoTrabajo});
            insert.Parameters.Add(new SqlParameter("@IdEmpleado",SqlDbType.Int){Value=request.IdEmpleado});
            insert.Parameters.Add(new SqlParameter("@IdAdmin",SqlDbType.Int){Value=idAdmin});
            var idOrden=Convert.ToInt64(await insert.ExecuteScalarAsync(ct));
            await tx.CommitAsync(ct);
            return Created($"/api/administracion/asignaciones/{idOrden}",new { idOrden,request.IdCodigo,request.TipoTrabajo,request.IdEmpleado,estado="Pendiente" });
        }
        catch(SqlException ex) when(ex.Number is 2601 or 2627)
        {
            await tx.RollbackAsync(ct);
            return Conflict(new { mensaje="Ese punto ya tiene una asignación pendiente." });
        }
    }

    [HttpPost("asignaciones/{idOrden:long}/cancelar")]
    public async Task<IActionResult> CancelarAsignacion(long idOrden,CancellationToken ct)
    {
        const string sql="""
            SET XACT_ABORT ON;
            BEGIN TRANSACTION;
            DECLARE @IdCodigo int,@Tipo varchar(20);
            SELECT @IdCodigo=IdCodigo,@Tipo=TipoTrabajo
              FROM dbo.OrdenesTrabajo WITH(UPDLOCK,HOLDLOCK)
             WHERE IdOrden=@IdOrden AND Estado='Pendiente';
            IF @IdCodigo IS NULL BEGIN ROLLBACK; SELECT CAST(0 AS int); RETURN; END;
            UPDATE dbo.OrdenesTrabajo SET Estado='Cancelada',FechaActualizacion=SYSDATETIME() WHERE IdOrden=@IdOrden;
            IF @Tipo='Corte' UPDATE dbo.CodigosFijos SET Estado=1 WHERE IdCodigo=@IdCodigo AND Estado=2;
            COMMIT;
            SELECT CAST(1 AS int);
            """;
        await using var cn=connections.Create(); await cn.OpenAsync(ct);
        await using var cmd=new SqlCommand(sql,cn);
        cmd.Parameters.Add(new SqlParameter("@IdOrden",SqlDbType.BigInt){Value=idOrden});
        var changed=Convert.ToInt32(await cmd.ExecuteScalarAsync(ct));
        return changed==1?Ok(new { mensaje="Asignación cancelada." }):NotFound(new { mensaje="No existe una asignación pendiente con ese identificador." });
    }
}

public sealed record CrearEmpleadoRequest(
    [System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.StringLength(50,MinimumLength=2)] string Login,
    [System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.StringLength(120,MinimumLength=2)] string Nombre,
    [System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.StringLength(128,MinimumLength=8)] string Password,
    [System.ComponentModel.DataAnnotations.Required] string Rol);

public sealed record CrearAsignacionRequest(int IdCodigo,int IdEmpleado,string TipoTrabajo);
