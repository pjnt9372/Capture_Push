# -*- coding: utf-8 -*-
"""
统一日志管理模块
提供项目级别的日志配置和初始化功能
支持脚本形式在用户处运行，配置和日志统一使用 AppData 目录
"""
import logging
import logging.config
import logging.handlers
import sys
import os
import platform
import subprocess
import configparser
import datetime
import shutil
import zipfile
from pathlib import Path

# 用于获取用户桌面路径
try:
    import winreg
except ImportError:
    # 非Windows系统时的备用方案
    pass


def pack_logs():
    """
    将 AppData 中的日志目录打包成ZIP压缩包并放在桌面。
    包含本机硬件相关信息。
    返回打包文件的路径。
    """
    def get_desktop_path():
        """获取真实的桌面路径，优先使用Windows API"""
        try:
            # Windows系统使用注册表获取真实桌面路径
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            winreg.CloseKey(key)
            return Path(desktop_path)
        except (NameError, OSError):
            # 如果无法使用Windows API，则回退到用户目录下的Desktop
            try:
                import ctypes
                from ctypes import wintypes
                # 使用CSIDL_DESKTOP常量获取桌面路径
                CSIDL_DESKTOP = 0
                buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOP, None, 0, buf)
                return Path(buf.value)
            except:
                # 最终回退到用户目录下的Desktop
                return Path(os.path.expanduser("~/Desktop"))

    def collect_hardware_info():
        """收集本机硬件信息"""
        hardware_info = []
        hardware_info.append(f"Capture Push 硬件信息报告")
        hardware_info.append(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        hardware_info.append("="*50)
        
        # 系统信息
        hardware_info.append(f"操作系统: {platform.system()}")
        hardware_info.append(f"操作系统版本: {platform.version()}")
        hardware_info.append(f"操作系统发行版: {platform.platform()}")
        hardware_info.append(f"计算机架构: {platform.architecture()[0]}")
        hardware_info.append(f"机器类型: {platform.machine()}")
        hardware_info.append(f"处理器: {platform.processor()}")
        hardware_info.append(f"CPU 信息: {platform.uname().processor}")
        
        # 内存信息 (Windows)
        if platform.system() == "Windows":
            try:
                # 使用wmic命令获取更详细的硬件信息
                mem_info = subprocess.run(['wmic', 'computersystem', 'get', 'TotalPhysicalMemory'], 
                                          capture_output=True, text=True, timeout=10)
                if mem_info.returncode == 0:
                    lines = mem_info.stdout.strip().split('\n')
                    if len(lines) > 1:
                        total_mem = lines[1].strip()
                        if total_mem:
                            hardware_info.append(f"物理内存: {total_mem} bytes")
                
                # 获取磁盘信息
                disk_info = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption'], 
                                           capture_output=True, text=True, timeout=10)
                if disk_info.returncode == 0:
                    hardware_info.append("磁盘信息:")
                    lines = disk_info.stdout.strip().split('\n')
                    for line in lines[1:]:  # 跳过标题行
                        line = line.strip()
                        if line:
                            hardware_info.append(f"  {line}")
                            
                # 获取Windows更新补丁信息
                try:
                    # 使用wmic获取最近安装的补丁
                    patches_info = subprocess.run(['wmic', 'qfe', 'get', 'HotFixID,InstalledOn,Description'], 
                                               capture_output=True, text=True, timeout=15)
                    if patches_info.returncode == 0:
                        lines = patches_info.stdout.strip().split('\n')
                        if len(lines) > 1:
                            hardware_info.append("Windows更新补丁:")
                            # 提取并格式化补丁信息（跳过标题行）
                            for line in lines[1:]:
                                line = line.strip()
                                if line:
                                    # 清理多余的空白字符
                                    clean_line = ' '.join(line.split())
                                    if clean_line:  # 确保不是空行
                                        hardware_info.append(f"  {clean_line}")
                        else:
                            hardware_info.append("Windows更新补丁: 无信息或无法获取")
                except Exception as patch_error:
                    hardware_info.append(f"Windows更新补丁: 获取失败 ({str(patch_error)})")
                    
            except Exception as e:
                hardware_info.append(f"获取详细硬件信息失败: {str(e)}")
        else:
            # 非Windows系统使用通用方法
            try:
                mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')  
                mem_gib = mem_bytes / (1024.**3)
                hardware_info.append(f"物理内存: ~{mem_gib:.2f} GB")
            except:
                hardware_info.append("物理内存: 无法获取")
        
        return "\n".join(hardware_info)

    try:
        localappdata = os.environ.get('LOCALAPPDATA')
        if not localappdata:
            raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
        
        desktop_path = get_desktop_path()
        log_dir = Path(localappdata) / 'Capture_Push'
        if not log_dir.exists():
            raise FileNotFoundError(f"日志目录不存在: {log_dir}")
        
        # 确定输出文件名和路径
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"capture_push_log_report_{timestamp}.zip"
        archive_path = desktop_path / archive_name

        # 创建ZIP文件并添加日志文件和硬件信息
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有日志文件
            for log_file_path in log_dir.glob("*.log"):
                zipf.write(log_file_path, log_file_path.name)
            
            # 添加配置文件（如果有）
            config_file = log_dir / 'config.ini'
            if config_file.exists():
                zipf.write(config_file, config_file.name)
            
            # 添加硬件信息到ZIP文件
            hardware_info_content = collect_hardware_info()
            zipf.writestr("hardware_info.txt", hardware_info_content)
        
        return str(archive_path)
    except Exception as e:
        print(f"打包日志失败: {e}")
        return None


def get_config_path():
    """
    获取配置文件路径（AppData 目录）
    
    Returns:
        Path: 配置文件路径对象
    
    Raises:
        RuntimeError: 如果无法获取 AppData 目录
    """
    # 获取 AppData 目录
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")

    config_path = Path(localappdata) / 'Capture_Push' / 'config.ini'
    
    return config_path


def cleanup_old_logs(log_dir, max_total_size_mb=50, max_days=7):
    """
    清理旧日志文件，按大小和天数限制清理。
    
    Args:
        log_dir: 日志目录路径
        max_total_size_mb: 最大大小限制(MB)
        max_days: 最大保留天数
    """
    try:
        import time
        
        # 计算7天前的时间戳
        seven_days_ago = time.time() - (max_days * 24 * 60 * 60)
        
        # 按大小清理的文件
        size_cleanup_files = []
        # 按天数清理的文件
        day_cleanup_files = []
        
        for f in log_dir.glob("*.log*"):
            if f.is_file():
                stat_info = f.stat()
                mtime = stat_info.st_mtime
                size = stat_info.st_size
                
                # 检查是否超过7天
                if mtime < seven_days_ago:
                    day_cleanup_files.append((f, mtime, size))
                else:
                    size_cleanup_files.append((f, mtime, size))
        
        # 首先删除超过7天的文件
        for file_info in day_cleanup_files:
            expired_file, _, _ = file_info
            try:
                expired_file.unlink()
                print(f"[*] 已自动删除超过{max_days}天的日志: {expired_file.name}")
            except Exception as e:
                print(f"[!] 无法删除过期日志文件 {expired_file.name}: {e}")
        
        # 对剩余文件按大小进行清理
        log_files = size_cleanup_files
        # 按修改时间从旧到新排序
        log_files.sort(key=lambda x: x[1])
        
        total_size = sum(f[2] for f in log_files)
        max_total_size = max_total_size_mb * 1024 * 1024
        
        while total_size > max_total_size and log_files:
            oldest_file, _, size = log_files.pop(0)
            try:
                oldest_file.unlink()
                total_size -= size
                print(f"[*] 已自动删除过旧日志: {oldest_file.name}")
            except Exception as e:
                print(f"[!] 无法删除日志文件 {oldest_file.name}: {e}")
                
    except Exception as e:
        print(f"[!] 清理日志目录失败: {e}")


def get_log_file_path(module_name=None):
    """
    获取日志文件路径（AppData 目录）。
    现在统一使用当前日期作为文件名。
    """
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
    
    appdata_dir = Path(localappdata) / 'Capture_Push'
    appdata_dir.mkdir(parents=True, exist_ok=True)
    
    # 统一使用日期命名
    today = datetime.date.today().strftime("%Y-%m-%d")
    return appdata_dir / f'{today}.log'


def init_logger(module_name):
    """
    初始化日志系统（AppData 目录）
    
    Args:
        module_name: 模块名称，将显示在日志条目中
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    config_path = get_config_path()
    log_file_path = get_log_file_path()
    appdata_dir = log_file_path.parent
    
    # 1. 自动清理旧日志
    cleanup_old_logs(appdata_dir)
    
    # 2. 读取配置文件获取日志级别
    try:
        from core.config_manager import load_config, ConfigDecodingError
        config = load_config()
    except ImportError:
        # 兜底：如果无法从 config_manager 导入，尝试普通读取
        config = configparser.ConfigParser()
        try:
            config.read(str(config_path), encoding='utf-8')
        except Exception:
            # 如果配置文件无法读取，使用默认配置
            config = configparser.ConfigParser()
    except ConfigDecodingError:
        # 如果配置文件解码错误，使用默认配置
        config = configparser.ConfigParser()
    
    log_level_str = config.get('logging', 'level', fallback='DEBUG')
    log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)
    
    # 3. 配置 Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 避免重复添加处理器（针对同进程内多次调用）
    has_console = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    has_file = any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file_path.absolute()) for h in root_logger.handlers)
    
    # 统一的格式化器：包含模块名 (%(name)s)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    if not has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
    
    if not has_file:
        # 清除所有旧的文件处理器（如果有的话）
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)
        
        # 添加新的统一文件处理器
        # 单个文件上限 10MB，保留多个备份（总大小由 cleanup_old_logs 控制）
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file_path), 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=20,         # 保留足够多的滚动文件，清理逻辑在 cleanup_old_logs 中
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # 返回子 logger
    logger = logging.getLogger(module_name)
    logger.info(f"[INIT] 模块日志初始化: {module_name} -> {log_file_path.name}")
    
    return logger


def get_logger(module_name=None):
    """
    获取日志记录器
    
    Args:
        module_name: 模块名称，如果为 None 则返回 root logger
        
    Returns:
        logging.Logger: 日志记录器
    """
    if module_name:
        return logging.getLogger(module_name)
    return logging.getLogger()
