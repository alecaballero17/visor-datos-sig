param([switch]$LocalDB)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

. "$PSScriptRoot/conexion-base.ps1"
$connectionString = Get-ArquisConnectionString -LocalDB:$LocalDB
$sqlFile = Join-Path $PSScriptRoot '.setup\capas.sql'
if (-not (Test-Path -LiteralPath $sqlFile)) { throw 'No existe .setup\capas.sql. Ejecute primero convertir-capas.py.' }

$layers = @(
    @{ Table = 'Manzanas'; Before = @('CodigosFijos', 'Lotes', 'Manzanas', 'Vias') },
    @{ Table = 'Lotes'; Before = @() },
    @{ Table = 'CodigosFijos'; Before = @() },
    @{ Table = 'Vias'; Before = @() }
)

$lines = Get-Content -LiteralPath $sqlFile -Encoding UTF8
$connection = New-Object System.Data.SqlClient.SqlConnection $connectionString
$connection.Open()
try {
    # La muestra de demo se sustituye por la carga total antes de procesar capas.
    foreach ($table in $layers[0].Before) {
        $delete = $connection.CreateCommand()
        $delete.CommandText = "DELETE FROM dbo.[$table];"
        [void]$delete.ExecuteNonQuery()
    }

    foreach ($layer in $layers) {
        $table = $layer.Table
        $inserts = @($lines | Where-Object { $_ -like "INSERT dbo.$table*" })
        if ($inserts.Count -eq 0) { throw "No se encontraron registros de $table en $sqlFile." }

        $transaction = $connection.BeginTransaction()
        try {
            for ($offset = 0; $offset -lt $inserts.Count; $offset += 100) {
                $last = [Math]::Min($offset + 99, $inserts.Count - 1)
                $batch = $inserts[$offset..$last] -join [Environment]::NewLine
                $command = $connection.CreateCommand()
                $command.Transaction = $transaction
                $command.CommandTimeout = 180
                $command.CommandText = "SET XACT_ABORT ON;`n$batch"
                [void]$command.ExecuteNonQuery()
                Write-Output "${table}: $($last + 1) de $($inserts.Count)"
            }
            $transaction.Commit()
            Write-Output "${table}: completada"
        }
        catch {
            $transaction.Rollback()
            throw "La capa $table se revirtió: $($_.Exception.Message)"
        }
        finally { $transaction.Dispose() }
    }

    $associate = $connection.CreateCommand()
    $associate.CommandTimeout = 600
    $associate.CommandText = 'EXEC dbo.sp_ActualizarLoteCodigosFijos;'
    [void]$associate.ExecuteNonQuery()
    Write-Output 'Carga total y asociaciones espaciales completadas.'
}
finally { $connection.Dispose() }
