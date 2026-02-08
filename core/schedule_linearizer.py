# -*- coding: utf-8 -*-
"""
课表线性化模块
将传统课表数据重排为线性模式，按周次组织课程数据，并智能合并连续节次
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

# 导入日志模块
try:
    from .log import get_log_file_path, get_logger
except ImportError:
    from core.log import get_log_file_path, get_logger

logger = get_logger('schedule_linearizer')

def get_appdata_dir():
    """获取AppData目录"""
    # 使用固定的Capture_Push目录路径
    return Path.home() / "AppData" / "Local" / "Capture_Push"

def calculate_date_from_week(week_num: int, weekday: int, first_monday: str) -> str:
    """
    根据周次和星期计算具体日期
    
    Args:
        week_num: 第几周 (1-20)
        weekday: 星期几 (1-7, 周一到周日)
        first_monday: 第一周周一的日期字符串 "YYYY-MM-DD"
    
    Returns:
        日期字符串 "YYYY-MM-DD"
    """
    try:
        first_monday_date = datetime.strptime(first_monday, "%Y-%m-%d")
        # 计算目标日期：第N周的周M
        target_date = first_monday_date + timedelta(weeks=week_num-1, days=weekday-1)
        return target_date.strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"日期计算失败: {e}")
        return ""

def linearize_schedule(schedule_data: List[Dict], first_monday: str = None) -> Dict[str, Any]:
    """
    将原始课表数据重排为线性化周次结构，并智能合并同一周内同课程同日的连续节次
    
    参数:
        schedule_data: 原始课表数据列表，每项含"星期","开始小节","结束小节","课程名称","周次列表"
        first_monday: 学期开始日期（预留扩展，当前逻辑未使用）
    
    返回:
        标准化JSON结构：{"data": {"第X周": {"课程列表": [...]}}}
    """
    if not schedule_data:
        logger.warning("输入的课表数据为空")
        return {}
    
    # ===== 步骤1：按周次展开原始数据 =====
    week_courses = defaultdict(list)  # {周次整数: [课程条目...]}
    
    for item in schedule_data:
        weeks = item.get("周次列表", [])
        # 构建基础课程信息，保留所有必要字段
        base_course = {
            "星期": item["星期"],
            "开始小节": item["开始小节"],
            "结束小节": item["结束小节"],
            "课程名称": item["课程名称"],
            "教师": item.get("教师", ""),
            "教室": item.get("教室", "")
        }
        
        for week in weeks:
            # 为当前周创建独立条目（避免引用问题）
            entry = base_course.copy()
            entry["周次"] = week  # 标记所属周次
            week_courses[week].append(entry)
    
    # ===== 步骤2：按周处理并智能合并连续节次 =====
    result_data = {}
    
    for week in sorted(week_courses.keys()):
        courses = week_courses[week]
        # 关键排序：确保同课程同日的节次按开始小节升序排列
        courses.sort(key=lambda x: (x["星期"], x["课程名称"], x["开始小节"]))
        
        merged = []
        for course in courses:
            if not merged:
                merged.append(course)
                continue
            
            last = merged[-1]
            # 合并条件：同日 + 同课程 + 节次严格连续（当前开始 = 上一结束+1）
            if (last["星期"] == course["星期"] and 
                last["课程名称"] == course["课程名称"] and 
                course["开始小节"] == last["结束小节"] + 1):
                # 原地扩展结束小节（保留其他字段如教室、教师等）
                last["结束小节"] = course["结束小节"]
            else:
                merged.append(course)
        
        # 构建周次键（支持中文格式）
        week_key = f"第{week}周"
        result_data[week_key] = {
            "周次": week,
            "课程数量": len(merged),
            "课程列表": merged
        }
    
    # 构建完整的返回结构
    linear_data = {
        "metadata": {
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "总课程数": len(schedule_data),
            "数据格式": "线性周次模式"
        },
        "data": result_data
    }
    
    # 如果提供了学期开始日期，则记录在metadata中
    if first_monday:
        linear_data["metadata"]["第一周周一"] = first_monday
    
    logger.info(f"课表线性化完成，共处理 {len(schedule_data)} 条原始课程，生成 {len(result_data)} 周数据")
    return linear_data

def save_linear_schedule(linear_data: Dict[str, Any], filename: str = None) -> str:
    """
    保存线性化课表数据到JSON文件
    
    Args:
        linear_data: 线性化的课表数据
        filename: 文件名，默认为 linear_schedule.json
    
    Returns:
        保存的文件路径
    """
    if filename is None:
        filename = "linear_schedule.json"
    
    appdata_dir = get_appdata_dir()
    save_path = appdata_dir / filename
    
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(linear_data, f, ensure_ascii=False, indent=2)
        logger.info(f"线性课表数据已保存到: {save_path}")
        return str(save_path)
    except Exception as e:
        logger.error(f"保存线性课表数据失败: {e}")
        raise

def load_linear_schedule(filename: str = None) -> Dict[str, Any]:
    """
    从JSON文件加载线性化课表数据
    
    Args:
        filename: 文件名，默认为 linear_schedule.json
    
    Returns:
        线性化的课表数据字典
    """
    if filename is None:
        filename = "linear_schedule.json"
    
    appdata_dir = get_appdata_dir()
    load_path = appdata_dir / filename
    
    try:
        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"成功加载线性课表数据: {load_path}")
        return data
    except FileNotFoundError:
        logger.warning(f"线性课表文件不存在: {load_path}")
        return {}
    except Exception as e:
        logger.error(f"加载线性课表数据失败: {e}")
        return {}

def format_linear_schedule_for_display(linear_data: Dict[str, Any]) -> str:
    """
    格式化线性课表数据用于显示
    
    Args:
        linear_data: 线性化的课表数据
    
    Returns:
        格式化的字符串
    """
    if not linear_data or "data" not in linear_data:
        return "暂无线性课表数据"
    
    output = []
    output.append("=" * 60)
    output.append("_CAPTURE PUSH 线性课表_")
    output.append("=" * 60)
    
    # 显示元数据
    metadata = linear_data.get("metadata", {})
    output.append(f"生成时间: {metadata.get('生成时间', '未知')}")
    output.append(f"学期开始: {metadata.get('第一周周一', '未知')}")
    output.append(f"总课程数: {metadata.get('总课程数', 0)}")
    output.append("")
    
    # 显示每周课程
    week_data = linear_data.get("data", {})
    for week_key, week_info in week_data.items():
        output.append(f"【{week_key}】")
        output.append(f"课程数量: {week_info.get('课程数量', 0)}")
        output.append("-" * 40)
        
        courses = week_info.get("课程列表", [])
        if not courses:
            output.append("本周无课程")
        else:
            for i, course in enumerate(courses, 1):
                date_str = course.get("日期", "未知日期")
                weekday_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
                weekday_str = weekday_map.get(course.get("星期", 0), "未知")
                periods = f"{course.get('开始小节', 0)}-{course.get('结束小节', 0)}节"
                course_name = course.get("课程名称", "未知课程")
                teacher = course.get("教师", "未知教师")
                classroom = course.get("教室", "未知教室")
                
                output.append(f"{i:2d}. {date_str} ({weekday_str}) {periods}")
                output.append(f"    {course_name}")
                output.append(f"    教师: {teacher} | 教室: {classroom}")
                output.append("")
        
        output.append("")
    
    return "\n".join(output)

# 示例使用函数
def demo_linearization():
    """
    演示课表线性化功能
    """
    # 示例原始课表数据
    sample_schedule = [
        {
            "星期": 1,  # 周一
            "开始小节": 1,
            "结束小节": 2,
            "课程名称": "高等数学",
            "教师": "张教授",
            "教室": "A101",
            "周次列表": [1, 2, 3, 4, 5]  # 第1-5周
        },
        {
            "星期": 3,  # 周三
            "开始小节": 3,
            "结束小节": 4,
            "课程名称": "大学英语",
            "教师": "李老师",
            "教室": "B201",
            "周次列表": [1, 2, 3, 4, 5, 6, 7, 8]  # 第1-8周
        }
    ]
    
    # 线性化处理
    first_monday = "2024-09-02"  # 假设第一周周一
    linear_data = linearize_schedule(sample_schedule, first_monday)
    
    # 保存到文件
    save_path = save_linear_schedule(linear_data, "demo_linear_schedule.json")
    
    # 格式化显示
    display_text = format_linear_schedule_for_display(linear_data)
    print(display_text)
    
    return linear_data, save_path

if __name__ == "__main__":
    # 运行演示
    demo_linearization()