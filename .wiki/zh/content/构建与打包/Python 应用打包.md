# Python 应用打包

<cite>
**本文引用的文件**
- [Capture_Push_Setup.iss](file://Capture_Push_Setup.iss)
- [pyproject.toml](file://pyproject.toml)
- [requirements.txt](file://requirements.txt)
- [README.md](file://README.md)
- [core/go.py](file://core/go.py)
- [core/push.py](file://core/push.py)
- [gui/gui.py](file://gui/gui.py)
</cite>

## 目录
1. [简介](#简介)
2. [打包策略](#打包策略)
3. [项目结构](#项目结构)
4. [依赖管理](#依赖管理)
5. [Inno Setup 集成](#inno-setup-集成)
6. [故障排查](#故障排查)

## 简介
本技术文档说明 Capture_Push 项目的 Python 应用打包流程。项目目前主要采用 **Inno Setup** 结合 **嵌入式 Python 环境** 的方式进行分发，以确保在目标机器上的稳定运行，无需用户手动安装 Python 环境。

## 打包策略
项目不再依赖复杂的自定义构建脚本（如已弃用的 `build.py` 或 `build_installer_exe.py`），而是采用更标准化的流程：

1.  **依赖准备**：使用 `pip` 安装项目依赖到指定目录或虚拟环境。
2.  **文件同步**：将核心代码 (`core/`, `gui/`) 和资源文件复制到构建目录。
3.  **Inno Setup 打包**：使用 `ISCC` 编译器运行 `.iss` 脚本，将 Python 环境、源代码和启动脚本打包成最终的安装程序。

这种方式的优势在于：
- **透明度高**：构建过程清晰，易于调试。
- **维护性强**：利用成熟的 Inno Setup 工具，减少自定义脚本的维护成本。
- **灵活性**：易于集成到 CI/CD 流水线（如 GitHub Actions）。

## 项目结构
在打包过程中，主要涉及以下文件和目录：

- `core/`: 核心业务逻辑模块。
- `gui/`: 图形用户界面模块。
- `Capture_Push_Setup.iss`: Inno Setup 安装脚本，定义了打包规则。
- `requirements.txt`: Python 依赖清单。
- `config.ini`: 默认配置文件。

## 依赖管理
项目依赖通过 `requirements.txt` 管理。在打包准备阶段，通常执行以下操作：

1.  创建一个干净的 Python 环境（或使用嵌入式 Python）。
2.  安装依赖：
    ```bash
    pip install -r requirements.txt --target=site-packages
    ```
    或者在虚拟环境中安装。

关键依赖包括：
- `requests`: 网络请求。
- `beautifulsoup4`: HTML 解析。
- `PySide6`: 图形界面库。
- `keyring`: 凭据存储。

## Inno Setup 集成
Inno Setup 脚本 (`Capture_Push_Setup.iss`) 是打包的核心。它负责：

1.  **文件复制**：将 Python 解释器、依赖库、项目源码复制到安装目录。
2.  **快捷方式**：创建桌面和开始菜单快捷方式。
3.  **注册表项**：配置开机自启（如果启用）。
4.  **卸载程序**：生成卸载器，清理安装文件。

### 关键配置段
```iss
[Files]
; 复制 Python 环境（如果是完整版打包）
Source: "path\to\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; 复制项目源码
Source: "core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs createallsubdirs

; 复制配置文件
Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
```

## 故障排查
- **依赖缺失**：确保在打包前已完整安装 `requirements.txt` 中的所有依赖。
- **路径错误**：检查 `.iss` 脚本中的 `Source` 路径是否与实际构建环境一致。
- **权限问题**：在 Windows 上运行打包命令时，确保有足够的权限读取文件和写入输出目录。

## 结论
通过简化打包流程，直接利用 Inno Setup 的强大功能，Capture_Push 项目实现了更高效、更可靠的应用交付。开发者应关注 `.iss` 脚本的维护，确保其随项目结构变化而更新。
