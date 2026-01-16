; -- Capture_Push_Setup.iss --
; Capture_Push 安装脚本（内置Python环境，无需系统Python）

[Setup]
AppName=Capture_Push
AppVersion=0.2.0_Dev
AppPublisher=pjnt9372
DefaultDirName={autopf}\Capture_Push
DefaultGroupName=Capture_Push
OutputDir=Output
OutputBaseFilename=Capture_Push_Setup
Compression=lzma2/normal
SolidCompression=yes
InternalCompressLevel=normal
PrivilegesRequired=admin
WizardStyle=modern
SetupIconFile=
UninstallDisplayIcon={app}\Capture_Push_tray.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
; Python 3.11.9 安装包（需提前下载到项目根目录）
Source: "python-3.11.9-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

; 环境安装器（PyInstaller 打包的独立 exe）- 使用低压缩级别避免内存溢出
Source: "dist\Capture_Push_Installer.exe"; DestDir: "{app}"; Flags: ignoreversion solidbreak

; Python脚本和配置
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs

; 配置文件 - 同时释放到程序目录和 AppData 目录
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{localappdata}\Capture_Push"; Flags: ignoreversion

; 配置生成脚本
Source: "generate_config.py"; DestDir: "{app}"; Flags: ignoreversion

; C++托盘程序（需要预先编译）
Source: "tray\build\Release\Capture_Push_tray.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 创建 AppData 目录
Name: "{localappdata}\Capture_Push"

[Icons]
Name: "{group}\Capture_Push托盘"; Filename: "{app}\Capture_Push_tray.exe"
Name: "{group}\配置工具"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""
Name: "{group}\查看配置信息"; Filename: "{app}\install_config.txt"
Name: "{group}\卸载Capture_Push"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Capture_Push"; Filename: "{app}\Capture_Push_tray.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "附加选项:"
Name: autostart; Description: "开机自动启动托盘程序"; GroupDescription: "附加选项:"

[Registry]
; 注册安装路径
Root: HKLM; Subkey: "SOFTWARE\Capture_Push"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

; 自启动托盘程序（如果用户选择了autostart任务）
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Capture_Push_Tray"; ValueData: """{app}\Capture_Push_tray.exe"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; 1. 检测并安装 Python（仅在不存在时）
Filename: "{tmp}\python-3.11.9-amd64.exe"; Parameters: "/quiet InstallAllUsers=0 TargetDir=""{app}\python"" PrependPath=0 Include_test=0 Include_tcltk=0"; StatusMsg: "正在安装 Python 3.11.9 到软件目录..."; Flags: waituntilterminated; Check: NeedInstallPython; AfterInstall: AfterPythonInstall

; 2. 运行环境安装器创建虚拟环境（命令行模式，自动检测地区并选择镜像）
Filename: "{app}\Capture_Push_Installer.exe"; Parameters: """{app}"""; StatusMsg: "正在配置虚拟环境..."; Flags: waituntilterminated; Check: CheckPythonReady

; 3. 生成配置文件（仅在虚拟环境创建成功后）
Filename: "{app}\.venv\Scripts\python.exe"; Parameters: """{app}\generate_config.py"" ""{app}"""; StatusMsg: "正在生成配置信息..."; Flags: runhidden waituntilterminated; Check: CheckVenvReady

; 安装后选项
Filename: "{app}\Capture_Push_tray.exe"; Description: "启动 Capture_Push 托盘程序"; Flags: nowait postinstall skipifsilent
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\gui\gui.py"""; Description: "打开配置工具"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; 清理程序目录
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\.venv"
Type: files; Name: "{app}\install_config.txt"
Type: files; Name: "{app}\app.log"
Type: filesandordirs; Name: "{app}\core\state"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\gui\__pycache__"
; 清理 AppData 目录中的日志文件（保留配置文件让用户自行删除）
Type: files; Name: "{localappdata}\Capture_Push\*.log"

[Code]
// 全局变量：记录是否需要安装 Python
var
  g_NeedInstallPython: Boolean;
  g_PythonInstalled: Boolean;

// 检查 Python 是否已存在
function CheckPythonExists(): Boolean;
var
  PythonExePath: String;
begin
  PythonExePath := ExpandConstant('{app}\python\python.exe');
  Result := FileExists(PythonExePath);
end;

// 检查是否需要安装 Python
function NeedInstallPython(): Boolean;
begin
  Result := g_NeedInstallPython;
end;

// Python 安装后的回调函数
procedure AfterPythonInstall();
begin
  Log('Python installation command completed. Verifying...');
  // 验证安装
  g_PythonInstalled := VerifyPythonInstallation();
  if not g_PythonInstalled then
  begin
    Log('CRITICAL: Python installation failed verification!');
    // 这里用户已经看到错误提示，后续步骤会被阻止
  end;
end;

// 检查 Python 是否就绪（用于后续步骤的前置条件）
function CheckPythonReady(): Boolean;
begin
  Result := g_PythonInstalled;
  if not Result then
  begin
    Log('ERROR: Cannot proceed - Python is not ready.');
    MsgBox('Python 环境未就绪！' + #13#10 + #13#10 +
           '无法继续安装虚拟环境。' + #13#10 +
           '请检查安装日志并重试。',
           mbError, MB_OK);
  end;
end;

// 检查虚拟环境是否就绪
function CheckVenvReady(): Boolean;
var
  VenvPython: String;
begin
  VenvPython := ExpandConstant('{app}\.venv\Scripts\python.exe');
  Result := FileExists(VenvPython);
  if not Result then
  begin
    Log('ERROR: Virtual environment not found at: ' + VenvPython);
  end;
end;

// 验证 Python 是否安装成功
function VerifyPythonInstallation(): Boolean;
var
  PythonExePath: String;
  ResultCode: Integer;
begin
  Result := False;
  PythonExePath := ExpandConstant('{app}\python\python.exe');
  
  // 检查 python.exe 是否存在
  if not FileExists(PythonExePath) then
  begin
    Log('ERROR: Python installation failed - python.exe not found at: ' + PythonExePath);
    MsgBox('Python 安装失败！' + #13#10 + #13#10 +
           '找不到 python.exe，安装无法继续。' + #13#10 +
           '请重新运行安装程序。',
           mbError, MB_OK);
    Exit;
  end;
  
  // 尝试执行 python --version 验证
  if Exec(PythonExePath, '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      Log('Python installation verified successfully.');
      Result := True;
    end
    else
    begin
      Log('ERROR: Python verification failed with exit code: ' + IntToStr(ResultCode));
      MsgBox('Python 安装验证失败！' + #13#10 + #13#10 +
             '退出代码: ' + IntToStr(ResultCode) + #13#10 +
             '请重新运行安装程序。',
             mbError, MB_OK);
    end;
  end
  else
  begin
    Log('ERROR: Failed to execute Python for verification.');
    MsgBox('Python 验证失败！' + #13#10 + #13#10 +
           '无法执行 Python，安装无法继续。' + #13#10 +
           '请重新运行安装程序。',
           mbError, MB_OK);
  end;
end;

// 初始化安装
function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // 显示欢迎信息
  MsgBox('Capture_Push 安装程序' + #13#10 + #13#10 + 
         '✓ 内置Python环境：Python 3.11.9' + #13#10 +
         '✓ 安装位置：软件同一目录' + #13#10 +
         '✓ 环境隔离：不污染系统环境' + #13#10 +
         '✓ 安装大小：约 1500 MB' + #13#10 + #13#10 + 
         '点击"下一步"继续安装', 
         mbInformation, MB_OK);
end;

// 安装完成后的处理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // 在安装开始前检测 Python 是否存在
    if CheckPythonExists() then
    begin
      g_NeedInstallPython := False;
      g_PythonInstalled := True;
      Log('Python already exists, skip installation.');
    end
    else
    begin
      g_NeedInstallPython := True;
      g_PythonInstalled := False;
      Log('Python not found, will install to: ' + ExpandConstant('{app}\python'));
      MsgBox('未检测到 Python 环境' + #13#10 + #13#10 +
             '我们将安装 Python 3.11.9 到软件同一目录：' + #13#10 +
             ExpandConstant('{app}\python') + #13#10 + #13#10 +
             '• 不会污染系统环境' + #13#10 +
             '• 不会添加到系统 PATH' + #13#10 +
             '• 卸载时会一并删除',
             mbInformation, MB_OK);
    end;
  end;
  
  if CurStep = ssPostInstall then
  begin
    // 这里可以添加额外的安装后处理
    if g_PythonInstalled then
    begin
      Log('Installation completed successfully with Python ready.');
    end
    else
    begin
      Log('WARNING: Installation completed but Python status is uncertain.');
    end;
  end;
end;

// 卸载前的清理
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // 停止可能正在运行的托盘程序
    if MsgBox('检测到托盘程序可能正在运行，是否尝试关闭？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 这里可以添加关闭程序的代码
    end;
  end;
end;
