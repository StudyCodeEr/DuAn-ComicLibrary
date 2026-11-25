; Inno Setup Script for Comic Library
; Generates a single .exe installer from the PyInstaller output

#define MyAppName "Comic Library"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "MangaLib"
#define MyAppExeName "ComicLibrary.exe"
#define MyAppURL "http://127.0.0.1:8000"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{B7E8F3A1-5C2D-4E6F-9A8B-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; data/ nam CANH exe (paths.data_root khi dong bang), nen thu muc cai PHAI ghi duoc:
; vao Program Files thi tai truyen se loi quyen ghi. Vi vay co dinh per-user.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output settings
OutputDir=..\installer_output
OutputBaseFilename=ComicLibrary-3.0.0-Setup
SetupIconFile=..\app_icon.ico
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; UI
WizardStyle=modern
; Privileges - user-level install by default
PrivilegesRequired=lowest
; Misc
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
vietnamese.LaunchAfterInstall=Chạy {#MyAppName} sau khi cài đặt
vietnamese.CreateDesktopShortcut=Tạo biểu tượng trên Màn hình
vietnamese.CreateStartMenuShortcut=Tạo biểu tượng trong Start Menu
vietnamese.AutoStartWithWindows=Tự khởi động cùng Windows

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopShortcut}"; GroupDescription: "Biểu tượng:"; Flags: unchecked
Name: "autostart"; Description: "{cm:AutoStartWithWindows}"; GroupDescription: "Tùy chọn:"; Flags: unchecked

[Dirs]
; Thu vien truyen + DB nguoi dung tao ra sau khi cai. Go cai dat KHONG duoc xoa.
Name: "{app}\data"; Flags: uninsneveruninstall

[Files]
; Include entire PyInstaller output directory
Source: "..\dist\ComicLibrary\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "app"
Name: "{group}\Gỡ cài đặt {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "app"; Tasks: desktopicon

[Registry]
; Autostart with Windows (hidden mode)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ComicLibrary"; ValueData: """{app}\{#MyAppExeName}"" app --hidden"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "app"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent
