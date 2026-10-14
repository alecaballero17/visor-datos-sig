# Launcher for SIG Vector Studio in PowerShell
Set-Location -Path $PSScriptRoot
Write-Host "Iniciando SIG Vector Studio..." -ForegroundColor Cyan
python "$PSScriptRoot\sig_vector_studio\main.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al ejecutar la aplicacion." -ForegroundColor Red
}
