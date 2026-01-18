# -*- coding: utf-8 -*-
"""
Capture_Push 综合构建脚本
1. 准备便携式 Python 环境 (.venv)
2. 收集所有必要的程序文件到 build/ 目录
3. 为 Inno Setup 准备最终的打包目录
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[*] {msg}", flush=True)

def error(msg):
    print(f"[!] 错误: {msg}", file=sys.stderr)
    sys.exit(1)

def copy_tree(src, dst):
    if not src.exists():
        log(f"跳过不存在的目录: {src}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    log(f"已复制: {src.name} -> {dst}")

def main():
    project_root = Path(__file__).parent.parent.absolute()
    build_dir = project_root / "build"
    venv_dir = build_dir / ".venv"
    requirements_file = project_root / "requirements.txt"
    
    # 嵌入式 Python 配置
    py_version = "3.11.9"
    py_url = f"https://www.python.org/ftp/python/{py_version}/python-{py_version}-embed-amd64.zip"
    zip_path = build_dir / "python_embed.zip"
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = venv_dir / "get-pip.py"

    log("=" * 60)
    log(f"开始构建隔离环境 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"项目根目录: {project_root}")
    log(f"隔离构建空间: {build_dir}")
    log("=" * 60)

    # 1. 准备构建目录
    if not build_dir.exists():
        build_dir.mkdir(parents=True)
    
    # 2. 准备便携式 Python 环境 (在 build 目录下)
    if venv_dir.exists():
        log(f"清理旧的 .venv 目录...")
        shutil.rmtree(venv_dir)
    venv_dir.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists():
        log(f"正在下载嵌入式 Python ({py_version})...")
        try:
            urllib.request.urlretrieve(py_url, zip_path)
        except Exception as e:
            error(f"下载失败: {e}")
    else:
        log("使用本地已存在的 python_embed.zip")

    log("正在解压 Python 核心...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(venv_dir)

    log("配置 ._pth 文件以支持 site-packages...")
    pth_files = list(venv_dir.glob("python*._pth"))
    if pth_files:
        pth_file = pth_files[0]
        with open(pth_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(pth_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line.replace("#import site", "import site"))

    log("安装 pip...")
    urllib.request.urlretrieve(get_pip_url, get_pip_path)
    subprocess.run([str(venv_dir / "python.exe"), str(get_pip_path), "--no-warn-script-location"], cwd=venv_dir, check=True)
    os.remove(get_pip_path)

    log("安装项目依赖...")
    if requirements_file.exists():
        subprocess.run([str(venv_dir / "python.exe"), "-m", "pip", "install", "-r", str(requirements_file), "--no-warn-script-location"], cwd=venv_dir, check=True)
    
    # 3. 同步源码到构建空间 (保持与仓库相同的相对结构，以便 .iss 无需修改即可运行)
    log("正在同步组件到构建空间...")
    copy_tree(project_root / "core", build_dir / "core")
    copy_tree(project_root / "gui", build_dir / "gui")
    
    # 复制必要文件到 build 根目录
    files_to_copy = ["VERSION", "config.ini", "generate_config.py", "Capture_Push_Setup.iss", "Capture_Push_Lite_Setup.iss", "ChineseSimplified.isl"]
    for f_name in files_to_copy:
        src_f = project_root / f_name
        if src_f.exists():
            shutil.copy2(src_f, build_dir / f_name)
            log(f"已同步: {f_name}")

    # 4. 确保语言包资源存在 (如果仓库没有，则下载)
    isl_file = build_dir / "ChineseSimplified.isl"
    if not isl_file.exists():
        isl_url = "https://raw.githubusercontent.com/kira-96/Inno-Setup-Chinese-Simplified-Translation/master/ChineseSimplified.isl"
        log("正在从远程获取中文语言包...")
        try:
            urllib.request.urlretrieve(isl_url, isl_file)
            log("语言包拉取成功")
        except Exception as e:
            log(f"[!] 语言包拉取失败 (这可能导致打包报错): {e}")

    # 5. 创建托盘程序的适配目录结构 (适配 .iss 中的 Source 路径)
    # .iss 默认路径: tray\build\Release\Capture_Push_tray.exe
    iss_tray_path = build_dir / "tray" / "build" / "Release"
    iss_tray_path.mkdir(parents=True, exist_ok=True)
    
    tray_exe_src = project_root / "tray" / "build" / "Release" / "Capture_Push_tray.exe"
    if tray_exe_src.exists():
        shutil.copy2(tray_exe_src, iss_tray_path / "Capture_Push_tray.exe")
        log("已适配托盘程序路径结构")
    else:
        log("[!] 警告: 未找到托盘程序，请确保已进行 CMake 编译。")

    log("=" * 60)
    log("构建空间准备就绪！")
    log("打包指令:")
    log(f"完整版: ISCC build\\Capture_Push_Setup.iss")
    log(f"轻量版: ISCC build\\Capture_Push_Lite_Setup.iss")
    log("=" * 60)

if __name__ == "__main__":
    if sys.platform != "win32":
        print("[!] 该脚本仅支持 Windows 平台。")
        sys.exit(1)
    main()
