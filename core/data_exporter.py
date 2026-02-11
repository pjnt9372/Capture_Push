# -*- coding: utf-8 -*-
"""
数据导出模块
负责将课表和成绩数据导出为标准JSON格式，供安卓伴侣应用使用
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 导入日志模块
try:
    from log import get_logger
    from config_manager import load_config
except ImportError:
    from core.log import get_logger
    from core.config_manager import load_config

# 导入线性化模块
try:
    from core.schedule_linearizer import load_linear_schedule
except ImportError:
    load_linear_schedule = None

logger = get_logger('data_exporter')

# 定义数据存储路径
APPDATA_DIR = Path.home() / "AppData" / "Local" / "Capture_Push"


def get_current_school_code() -> str:
    """获取当前院校代码"""
    try:
        cfg = load_config()
        return cfg.get("account", "school_code", fallback="10546")
    except Exception as e:
        logger.warning(f"获取院校代码失败: {e}")
        return "10546"


# 成绩数据加载功能已移除（根据用户要求）


def export_full_data(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    导出完整的课表和成绩数据
    
    Args:
        output_path: 输出文件路径，如果为None则返回数据字典
        
    Returns:
        包含完整数据的字典
    """
    logger.info("开始导出完整数据...")
    
    # 构建元数据
    metadata = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "school_code": get_current_school_code(),
        "data_source": "capture_push_python"
    }
    
    # 加载线性化课表数据
    schedule_data = {}
    try:
        if load_linear_schedule:
            linear_data = load_linear_schedule("linear_schedule.json")
            if linear_data:
                schedule_data = {
                    "linear_data": linear_data
                }
                logger.info("成功加载线性化课表数据")
            else:
                logger.warning("线性化课表数据为空")
        else:
            logger.warning("线性化模块不可用")
    except Exception as e:
        logger.error(f"加载线性化课表数据失败: {e}")
    
    # 成绩数据已移除（根据用户要求）
    grades_data = []
    
    # 构建完整数据结构（不含成绩数据）
    export_data = {
        "metadata": metadata,
        "schedule": schedule_data
    }
    
    # 如果指定了输出路径，则保存到文件
    if output_path:
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已导出到: {output_file}")
            return {"status": "success", "file_path": str(output_file)}
        except Exception as e:
            logger.error(f"保存数据到文件失败: {e}")
            return {"status": "error", "message": str(e)}
    
    logger.info("数据导出完成")
    return export_data


def export_schedule_only(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    仅导出课表数据
    
    Args:
        output_path: 输出文件路径
        
    Returns:
        包含课表数据的字典
    """
    logger.info("开始导出课表数据...")
    
    metadata = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "school_code": get_current_school_code(),
        "data_type": "schedule_only"
    }
    
    schedule_data = {}
    try:
        if load_linear_schedule:
            linear_data = load_linear_schedule("linear_schedule.json")
            if linear_data:
                schedule_data = {
                    "linear_data": linear_data
                }
                logger.info("成功加载线性化课表数据")
    except Exception as e:
        logger.error(f"加载线性化课表数据失败: {e}")
    
    export_data = {
        "metadata": metadata,
        "schedule": schedule_data
    }
    
    if output_path:
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"课表数据已导出到: {output_file}")
            return {"status": "success", "file_path": str(output_file)}
        except Exception as e:
            logger.error(f"保存课表数据到文件失败: {e}")
            return {"status": "error", "message": str(e)}
    
    return export_data


# export_grades_only函数已移除（根据用户要求）


def get_export_summary() -> Dict[str, Any]:
    """
    获取导出数据摘要信息
    
    Returns:
        包含数据统计信息的字典
    """
    try:
        # 获取课表信息
        schedule_count = 0
        week_count = 0
        if load_linear_schedule:
            linear_data = load_linear_schedule("linear_schedule.json")
            if linear_data and "data" in linear_data:
                week_count = len(linear_data["data"])
                for week_data in linear_data["data"].values():
                    schedule_count += week_data.get("课程数量", 0)
        
        return {
            "schedule_courses": schedule_count,
            "schedule_weeks": week_count,
            "school_code": get_current_school_code(),
            "last_export": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取导出摘要失败: {e}")
        return {"error": str(e)}


# 命令行接口
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture_Push 数据导出工具")
    parser.add_argument("--export-full", help="导出完整数据到指定文件")
    parser.add_argument("--export-schedule", help="仅导出课表数据到指定文件")
    parser.add_argument("--summary", action="store_true", help="显示数据摘要信息")
    
    args = parser.parse_args()
    
    if args.summary:
        summary = get_export_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.export_full:
        result = export_full_data(args.export_full)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.export_schedule:
        result = export_schedule_only(args.export_schedule)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()