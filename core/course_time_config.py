# -*- coding: utf-8 -*-
"""
课程时间配置模块
用于管理和获取课程时间相关信息
支持两种配置格式：
1. school_time 节（现有格式）
2. course_time 节（新格式）
"""

from typing import Dict, Any
from core.config_manager import load_config
from core.log import get_logger

logger = get_logger('course_time_config')

def get_course_time_config() -> Dict[str, Any]:
    """
    获取课程时间配置信息
    
    Returns:
        包含课程时间配置的字典
    """
    try:
        cfg = load_config()
        
        # 首先尝试从 school_time 节读取配置（兼容现有配置）
        if cfg.has_section("school_time"):
            return _parse_school_time_config(cfg)
        
        # 如果没有 school_time 节，则尝试 course_time 节
        if cfg.has_section("course_time"):
            return _parse_course_time_config(cfg)
        
        # 如果都没有，返回默认配置
        logger.warning("未找到课程时间配置节，使用默认配置")
        return _get_default_config()
        
    except Exception as e:
        logger.warning(f"获取课程时间配置失败: {e}")
        return _get_default_config()


def _parse_school_time_config(cfg) -> Dict[str, Any]:
    """解析 school_time 配置节"""
    try:
        # 从 school_time 节读取配置
        morning_classes = cfg.getint("school_time", "morning_count", fallback=4)
        afternoon_classes = cfg.getint("school_time", "afternoon_count", fallback=4)
        evening_classes = cfg.getint("school_time", "evening_count", fallback=2)
        class_duration = cfg.getint("school_time", "class_duration", fallback=45)
        first_class_start = cfg.get("school_time", "first_class_start", fallback="08:30")
        
        # 解析课程时间列表
        class_times_str = cfg.get("school_time", "class_times", fallback="")
        class_times_list = [time.strip() for time in class_times_str.split(",") if time.strip()]
        
        # 构建 class_times 字典
        class_times = {}
        for i, start_time in enumerate(class_times_list, 1):
            if i <= len(class_times_list):
                class_times[f"class_{i}"] = {
                    "start": start_time,
                    "end": _calculate_end_time(start_time, class_duration)
                }
        
        return {
            "morning_classes": morning_classes,
            "afternoon_classes": afternoon_classes,
            "evening_classes": evening_classes,
            "total_classes": morning_classes + afternoon_classes + evening_classes,
            "class_duration": class_duration,
            "first_class_start": first_class_start,
            "class_times": class_times
        }
    except Exception as e:
        logger.warning(f"解析 school_time 配置失败: {e}")
        return _get_default_config()


def _parse_course_time_config(cfg) -> Dict[str, Any]:
    """解析 course_time 配置节"""
    try:
        # 从 course_time 节读取配置
        morning_classes = cfg.getint("course_time", "morning_classes", fallback=4)
        afternoon_classes = cfg.getint("course_time", "afternoon_classes", fallback=4)
        evening_classes = cfg.getint("course_time", "evening_classes", fallback=2)
        
        # 读取每节课的具体时间
        class_times = {}
        for i in range(1, morning_classes + afternoon_classes + evening_classes + 1):
            start_time = cfg.get("course_time", f"class_{i}_start", fallback="")
            end_time = cfg.get("course_time", f"class_{i}_end", fallback="")
            if start_time and end_time:
                class_times[f"class_{i}"] = {
                    "start": start_time,
                    "end": end_time
                }
        
        return {
            "morning_classes": morning_classes,
            "afternoon_classes": afternoon_classes,
            "evening_classes": evening_classes,
            "total_classes": morning_classes + afternoon_classes + evening_classes,
            "class_times": class_times
        }
    except Exception as e:
        logger.warning(f"解析 course_time 配置失败: {e}")
        return _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """获取默认配置"""
    return {
        "morning_classes": 4,
        "afternoon_classes": 4,
        "evening_classes": 2,
        "total_classes": 10,
        "class_times": {}
    }


def _calculate_end_time(start_time: str, duration: int) -> str:
    """根据开始时间和持续时间计算结束时间"""
    try:
        # 解析开始时间
        hours, minutes = map(int, start_time.split(":"))
        
        # 计算结束时间
        total_minutes = hours * 60 + minutes + duration
        end_hours = total_minutes // 60
        end_minutes = total_minutes % 60
        
        # 格式化输出
        return f"{end_hours:02d}:{end_minutes:02d}"
    except Exception:
        # 如果计算失败，返回空字符串
        return ""


# 示例配置文件内容（供参考）
"""
[school_time]
morning_count = 4
afternoon_count = 4
evening_count = 2
class_duration = 45
first_class_start = 08:30
class_times = 08:30,09:15,10:00,10:45,11:30,12:15,13:00,13:45,14:30,15:15

或者使用新的格式：

[course_time]
morning_classes = 4
afternoon_classes = 4
evening_classes = 2

class_1_start = 08:00
class_1_end = 08:45
class_2_start = 08:55
class_2_end = 09:40
# ... 继续添加其他课程时间
"""