param(
    [string]$Exe = "$env:USERPROFILE\Downloads\LIA.exe",
    [switch]$Startup
)
# Crea un acceso directo a LIA en el Escritorio y, con -Startup, tambien en la
# carpeta de Inicio (para que se abra al encender el PC).

if (-not (Test-Path $Exe)) {
    Write-Host "No encuentro $Exe. Construye antes el .exe con build.bat." -ForegroundColor Yellow
    exit 1
}

$ws = New-Object -ComObject WScript.Shell

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = $ws.CreateShortcut("$desktop\LIA.lnk")
$lnk.TargetPath = $Exe
$lnk.WorkingDirectory = Split-Path $Exe
$lnk.IconLocation = $Exe
$lnk.Description = "LIA Assistant"
$lnk.Save()
Write-Host "Acceso directo creado en el Escritorio." -ForegroundColor Green

if ($Startup) {
    $startup = [Environment]::GetFolderPath("Startup")
    $slnk = $ws.CreateShortcut("$startup\LIA.lnk")
    $slnk.TargetPath = $Exe
    $slnk.WorkingDirectory = Split-Path $Exe
    $slnk.IconLocation = $Exe
    $slnk.Description = "LIA Assistant"
    $slnk.Save()
    Write-Host "LIA se abrira al iniciar Windows." -ForegroundColor Green
}
