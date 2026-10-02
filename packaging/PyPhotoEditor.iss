#define AppName "PyPhotoEditor"
#define AppVersion "1.1.0"
#define ProjectRoot AddBackslash(SourcePath) + ".."

[Setup]
AppId={{1E4020EC-5B7F-4F94-9F17-0721E2D02346}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=PyPhotoEditor Project
AppComments=Local desktop image editor with Magic effect brushes
DefaultDirName={localappdata}\Programs\PyPhotoEditor
DefaultGroupName=PyPhotoEditor
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsePreviousTasks=no
MinVersion=10.0
OutputDir={#ProjectRoot}\work\packaging\installer
OutputBaseFilename=PyPhotoEditor-1.1.0-Windows-x64-Setup
SetupIconFile={#ProjectRoot}\work\packaging\app.ico
UninstallDisplayIcon={app}\PyPhotoEditor.exe
UninstallDisplayName=PyPhotoEditor
LicenseFile={#ProjectRoot}\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "contextmenu"; Description: "Add Edit in PyPhotoEditor to image right-click menus"; GroupDescription: "Explorer integration:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\work\packaging\dist\PyPhotoEditor\*"; DestDir: "{app}"; Excludes: "ThirdPartyLicenses\altgraph\*,ThirdPartyLicenses\colorama\*,ThirdPartyLicenses\iniconfig\*,ThirdPartyLicenses\pefile\*,ThirdPartyLicenses\pip\*,ThirdPartyLicenses\pluggy\*,ThirdPartyLicenses\Pygments\*,ThirdPartyLicenses\pyinstaller\*,ThirdPartyLicenses\pyinstaller-hooks-contrib\*,ThirdPartyLicenses\pywin32-ctypes\*,ThirdPartyLicenses\pytest\*,ThirdPartyLicenses\setuptools\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PyPhotoEditor\PyPhotoEditor"; Filename: "{app}\PyPhotoEditor.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\PyPhotoEditor\Uninstall PyPhotoEditor"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PyPhotoEditor"; Filename: "{app}\PyPhotoEditor.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\PyPhotoEditor.exe"; ValueType: string; ValueData: "{app}\PyPhotoEditor.exe"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\PyPhotoEditor.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "PyPhotoEditor"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\PyPhotoEditor.exe\shell\open\command"; ValueType: string; ValueData: """{app}\PyPhotoEditor.exe"" -- ""%1"""
#include "context-menu.iss"

[Run]
Filename: "{app}\PyPhotoEditor.exe"; Description: "Launch PyPhotoEditor"; Flags: nowait postinstall skipifsilent unchecked
