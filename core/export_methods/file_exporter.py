# -*- coding: utf-8 -*-
"""
文件导出模块
负责将数据导出为JSON文件并提供分享功能
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 导入日志模块
try:
    from log import get_logger
except ImportError:
    from core.log import get_logger

# 导入数据导出器
try:
    from core.data_exporter import export_full_data, export_schedule_only
except ImportError:
    # 备用导入
    from data_exporter import export_full_data, export_schedule_only

logger = get_logger('file_exporter')

# 默认导出目录
DEFAULT_EXPORT_DIR = Path.home() / "Documents" / "Capture_Push_Exports"


def generate_filename(data_type: str = "full") -> str:
    """
    生成导出文件名
    
    Args:
        data_type: 数据类型 (full/schedule)
        
    Returns:
        生成的文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"capture_push_{data_type}_{timestamp}.json"


def export_to_file(data_type: str = "full", output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    导出数据到文件
    
    Args:
        data_type: 数据类型 (full/schedule)
        output_dir: 输出目录，如果为None使用默认目录
        
    Returns:
        导出结果字典
    """
    try:
        # 确定输出目录
        if output_dir:
            export_dir = Path(output_dir)
        else:
            export_dir = DEFAULT_EXPORT_DIR
        
        # 创建目录
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        filename = generate_filename(data_type)
        file_path = export_dir / filename
        
        logger.info(f"开始导出 {data_type} 数据到: {file_path}")
        
        # 根据数据类型调用相应的导出函数
        if data_type == "full":
            result = export_full_data(str(file_path))
        elif data_type == "schedule":
            result = export_schedule_only(str(file_path))
        else:
            return {"status": "error", "message": f"不支持的数据类型: {data_type}"}
        
        if result.get("status") == "success":
            logger.info(f"数据导出成功: {result.get('file_path')}")
            return {
                "status": "success",
                "file_path": result.get("file_path"),
                "file_size": os.path.getsize(result.get("file_path")),
                "export_time": datetime.now().isoformat()
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"文件导出失败: {e}")
        return {"status": "error", "message": str(e)}


def get_recent_exports(count: int = 5) -> list:
    """
    获取最近的导出文件列表
    
    Args:
        count: 返回文件数量限制
        
    Returns:
        导出文件信息列表
    """
    try:
        if not DEFAULT_EXPORT_DIR.exists():
            return []
        
        # 获取所有JSON文件并按修改时间排序
        json_files = list(DEFAULT_EXPORT_DIR.glob("*.json"))
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        recent_files = []
        for file_path in json_files[:count]:
            try:
                file_stat = file_path.stat()
                # 尝试读取文件元数据
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                recent_files.append({
                    "filename": file_path.name,
                    "filepath": str(file_path),
                    "size": file_stat.st_size,
                    "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "export_time": data.get("metadata", {}).get("export_time", "Unknown"),
                    "data_type": data.get("metadata", {}).get("data_type", "full")
                })
            except Exception as e:
                logger.warning(f"读取文件 {file_path} 信息失败: {e}")
                continue
        
        return recent_files
    except Exception as e:
        logger.error(f"获取最近导出文件失败: {e}")
        return []


def cleanup_old_exports(keep_days: int = 30) -> Dict[str, Any]:
    """
    清理过期的导出文件
    
    Args:
        keep_days: 保留天数
        
    Returns:
        清理结果
    """
    try:
        if not DEFAULT_EXPORT_DIR.exists():
            return {"status": "success", "deleted_count": 0, "message": "导出目录不存在"}
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (keep_days * 24 * 3600)
        
        deleted_files = []
        for file_path in DEFAULT_EXPORT_DIR.glob("*.json"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    logger.info(f"已删除过期文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除文件 {file_path} 失败: {e}")
        
        return {
            "status": "success",
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files
        }
    except Exception as e:
        logger.error(f"清理过期文件失败: {e}")
        return {"status": "error", "message": str(e)}


# GUI集成函数
def get_export_directory() -> str:
    """获取默认导出目录路径"""
    return str(DEFAULT_EXPORT_DIR)


def open_export_directory():
    """在文件资源管理器中打开导出目录"""
    try:
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            subprocess.run(["explorer", str(DEFAULT_EXPORT_DIR)], check=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(DEFAULT_EXPORT_DIR)], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(DEFAULT_EXPORT_DIR)], check=True)
            
        logger.info(f"已打开导出目录: {DEFAULT_EXPORT_DIR}")
        return True
    except Exception as e:
        logger.error(f"打开导出目录失败: {e}")
        return False


# 命令行接口
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture_Push 文件导出工具")
    parser.add_argument("--export", choices=["full", "schedule"], 
                       default="full", help="导出数据类型")
    parser.add_argument("--directory", help="指定导出目录")
    parser.add_argument("--recent", type=int, default=5, help="显示最近导出文件数量")
    parser.add_argument("--cleanup", type=int, help="清理指定天数前的文件")
    parser.add_argument("--open-dir", action="store_true", help="打开导出目录")
    
    args = parser.parse_args()
    
    if args.open_dir:
        success = open_export_directory()
        if success:
            print("导出目录已打开")
        else:
            print("打开导出目录失败")
    elif args.cleanup:
        result = cleanup_old_exports(args.cleanup)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.recent > 0:
        recent_files = get_recent_exports(args.recent)
        print(json.dumps(recent_files, ensure_ascii=False, indent=2))
    else:
        result = export_to_file(args.export, args.directory)
        print(json.dumps(result, ensure_ascii=False, indent=2))