; Instalador de LIA (Inno Setup). Genera LIA-Setup.exe: un instalador real que
; deja al usuario elegir la carpeta, crea accesos directos y un desinstalador.
;
; Requisitos: tener el LIA.exe ya construido (packaging\dist\LIA.exe, lo hace
; build.bat) e Inno Setup instalado (https://jrsoftware.org/isdl.php).
; Para compilar:  doble clic en este .iss y boton "Compile", o:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss

#define MyAppName "LIA Assistant"
#define MyAppVersion "1.0"
#define MyAppPublisher "Hugo Catalan"
#define MyAppExeName "LIA.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; El usuario puede cambiar esta carpeta en el asistente:
DefaultDirName={autopf}\LIA
DefaultGroupName=LIA
AllowNoIcons=yes
; Sin admin: instala en la carpeta del usuario, sin UAC molesto (plug and play):
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=LIA-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "startup"; Description: "Abrir LIA al iniciar Windows"; GroupDescription: "Inicio con Windows:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\LIA"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar LIA"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LIA"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\LIA"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir LIA ahora"; Flags: nowait postinstall skipifsilent
