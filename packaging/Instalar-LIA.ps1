# Instalador de LIA sin dependencias (solo PowerShell de Windows).
# Copia LIA.exe a la carpeta elegida, crea accesos directos y registra un
# desinstalador en "Agregar o quitar programas". No necesita permisos de admin.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here "LIA.exe"
if (-not (Test-Path $src)) {
    Write-Host "No encuentro LIA.exe junto a este instalador." -ForegroundColor Red
    pause; exit 1
}

Write-Host "==== Instalador de LIA Assistant ====" -ForegroundColor Cyan
$default = Join-Path $env:LOCALAPPDATA "Programs\LIA"
$dir = Read-Host "Carpeta de instalacion (Enter para usar: $default)"
if ([string]::IsNullOrWhiteSpace($dir)) { $dir = $default }
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Copy-Item $src (Join-Path $dir "LIA.exe") -Force
$exe = Join-Path $dir "LIA.exe"

$ws = New-Object -ComObject WScript.Shell
$desktop  = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

function New-Lnk($path) {
    $l = $ws.CreateShortcut($path)
    $l.TargetPath = $exe
    $l.WorkingDirectory = $dir
    $l.IconLocation = $exe
    $l.Description = "LIA Assistant"
    $l.Save()
}
New-Lnk (Join-Path $desktop "LIA.lnk")
New-Lnk (Join-Path $startMenu "LIA.lnk")

$auto = Read-Host "Abrir LIA al iniciar Windows? (s/N)"
if ($auto -match '^[sS]') {
    $startup = [Environment]::GetFolderPath("Startup")
    New-Lnk (Join-Path $startup "LIA.lnk")
}

# Desinstalador
$uninst = Join-Path $dir "Desinstalar-LIA.ps1"
@"
`$ErrorActionPreference = 'SilentlyContinue'
Remove-Item '$([Environment]::GetFolderPath("Desktop"))\LIA.lnk' -Force
Remove-Item '$startMenu\LIA.lnk' -Force
Remove-Item '$([Environment]::GetFolderPath("Startup"))\LIA.lnk' -Force
Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\LIA' -Recurse -Force
Start-Sleep 1
Remove-Item '$dir' -Recurse -Force
"@ | Set-Content -Encoding UTF8 $uninst

# Registro en "Agregar o quitar programas" (HKCU, sin admin)
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\LIA"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty $key DisplayName "LIA Assistant"
Set-ItemProperty $key DisplayIcon $exe
Set-ItemProperty $key DisplayVersion "1.0"
Set-ItemProperty $key Publisher "Hugo Catalan"
Set-ItemProperty $key InstallLocation $dir
Set-ItemProperty $key UninstallString "powershell -NoProfile -ExecutionPolicy Bypass -File `"$uninst`""
Set-ItemProperty $key NoModify 1
Set-ItemProperty $key NoRepair 1

Write-Host ""
Write-Host "LIA instalada en: $dir" -ForegroundColor Green
Write-Host "Accesos directos creados. Puedes desinstalarla desde 'Agregar o quitar programas'." -ForegroundColor Green
pause
