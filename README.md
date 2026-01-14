# Capture_Push 项目总体介绍

## 项目概述

Capture_Push 是一个课程成绩和课表自动追踪推送系统，能够自动获取学生课程成绩和课表信息，并通过邮件等方式推送更新通知。

## 核心功能

### 1. 成绩追踪
- **自动获取成绩**：定期从学校教务系统获取最新成绩信息
- **成绩变化检测**：智能检测成绩更新，仅在有变化时推送通知
- **循环检测**：支持配置循环检测间隔，可自定义检测频率

### 2. 课表追踪  
- **自动获取课表**：定期从学校教务系统获取课表信息
- **课表推送**：支持推送今日、明日及完整课表
- **循环检测**：支持课表循环检测功能

### 3. 推送通知
- **邮件推送**：通过邮件发送成绩和课表更新通知
- **推送管理**：支持多种推送方式的管理框架
- **推送记录**：完整的推送日志记录

### 4. 托盘程序
- **系统托盘**：后台运行的系统托盘程序
- **菜单操作**：通过托盘菜单执行各种操作
- **循环检测**：支持后台自动循环检测成绩和课表变化
- **配置管理**：便捷的配置界面和编辑功能

## 技术特性

### 1. 日志系统
- **Python 日志**：所有 Python 模块包含完整的日志记录
- **C++ 日志**：托盘程序包含完整的日志记录
- **路径处理**：打包后自动使用用户可写目录存储日志
- **日志级别**：支持 INFO、DEBUG、ERROR、WARNING 等多个级别

### 2. 依赖管理
- **uv 支持**：现代化依赖管理工具支持
- **requirements.txt**：标准依赖文件支持
- **虚拟环境**：完整的虚拟环境管理
- **PyInstaller**：打包工具集成

### 3. 配置管理
- **配置文件**：支持 `config.ini` 配置文件
- **运行模式**：支持 DEV（开发）和 BUILD（生产）两种模式
- **灵活配置**：支持账户、邮箱、循环检测等多种配置

## 项目结构

```
Capture_Push/
├── core/                   # 核心功能模块
│   ├── getCourseGrades.py  # 成绩获取模块
│   ├── getCourseSchedule.py # 课表获取模块  
│   ├── push.py            # 推送模块（原 mailer）
│   └── go.py              # 主执行模块
├── gui/                   # GUI 界面模块
│   └── gui.py             # 配置界面
├── tray/                  # 系统托盘程序
│   └── tray_app.cpp       # C++ 托盘程序
├── installer.py           # 安装脚本
├── build_installer_exe.py # 打包脚本
├── config.ini             # 配置文件
└── GradeTracker_Setup.iss # Inno Setup 配置
```

## 安装与使用

### 开发环境安装
```bash
# 使用 uv 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/Scripts/activate  # Windows
# 或
source .venv/bin/activate      # Unix

# 安装依赖
uv pip install -r requirements.txt
```

### 使用标准 Python 工具
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # Unix

# 安装依赖
pip install -r requirements.txt
```

## 部署与打包

- 支持使用 PyInstaller 打包为独立可执行文件
- 托盘程序使用 C++ 编写，性能优秀
- 完整的安装程序打包支持（Inno Setup）

## 日志文件位置

打包后程序的日志文件存储在：
- `%LOCALAPPDATA%\GradeTracker` 