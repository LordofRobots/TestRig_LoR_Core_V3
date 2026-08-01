#define MyAppName "LoR Core V3 Test Station"
#define MyAppVersion "1.14.0"
#define MyAppPublisher "Lord of Robots"
#define MyAppExeName "LoR Core V3 Test Station.exe"

[Setup]
AppId={{7C69FC40-ED8E-4A91-8B38-84FA493FEE07}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Lord of Robots\{#MyAppName}
DefaultGroupName=Lord of Robots
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=LoR_Core_V3_Test_Station_Setup_{#MyAppVersion}
SetupIconFile=..\production_test\assets\lor-test-station.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "output\app\LoR Core V3 Test Station\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{commonappdata}\Lord of Robots\LoR Core V3 Test Station"; Permissions: users-modify
Name: "{commonappdata}\Lord of Robots\LoR Core V3 Test Station\results"; Permissions: users-modify
Name: "{commonappdata}\Lord of Robots\LoR Core V3 Test Station\build"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
