# -*- coding: utf-8 -*-
"""
主执行模块
协调各组件工作，实现成绩和课表抓取、处理与推送
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到模块搜索路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.log import get_logger, get_log_file_path
from core.push import PushManager
from core.plugins.plugin_manager import get_plugin_manager

logger = get_logger()


def save_html_file(content: str, filename: str) -> bool:
    """
    保存HTML内容到文件
    
    Args:
        content: HTML内容
        filename: 文件名
    
    Returns:
        bool: 保存是否成功
    """
    try:
        # 获取APPDATA目录
        appdata_dir = get_log_file_path('gui').parent
        html_file = appdata_dir / filename
        
        # 确保目录存在
        html_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"HTML文件已保存: {html_file}")
        return True
    except Exception as e:
        logger.error(f"保存HTML文件失败: {e}", exc_info=True)
        return False


def run_capture(school_code: str, username: str, password: str, 
               push_method: str = "email", 
               force_update: bool = False,
               fetch_grade: bool = False,
               fetch_schedule: bool = False) -> Dict[str, Any]:
    """
    执行抓取任务主函数
    
    Args:
        school_code: 院校代码
        username: 用户名
        password: 密码
        push_method: 推送方式
        force_update: 是否强制更新
        fetch_grade: 是否抓取成绩
        fetch_schedule: 是否抓取课表
    
    Returns:
        包含抓取结果的字典
    """
    logger.info(f"开始执行抓取任务 - 院校: {school_code}, 用户: {username}")
    
    try:
        # 获取插件管理器
        plugin_manager = get_plugin_manager()
        
        # 加载指定院校的插件
        school_module = plugin_manager.load_plugin(school_code)
        if not school_module:
            logger.error(f"未能加载院校 {school_code} 的插件")
            return {"success": False, "error": f"未能加载院校 {school_code} 的插件"}
        
        logger.info(f"成功加载院校 {school_code} 的插件")
        
        # 创建推送管理器
        push_manager = PushManager()
        
        grades_result = None
        schedule_result = None
        
        # 执行成绩抓取
        if fetch_grade:
            logger.info("开始抓取成绩信息...")
            grades_raw = school_module.fetch_grades(username, password, force_update)
            
            if grades_raw:
                logger.info("成绩抓取成功")
                # 保存原始HTML到文件
                if isinstance(grades_raw, str):
                    save_html_file(grades_raw, "grade.html")
                
                # 解析成绩数据
                grades_result = school_module.parse_grades(grades_raw)
                
                # 推送成绩信息
                push_success = push_manager.push_grades(grades_result, push_method)
                if push_success:
                    logger.info("成绩推送成功")
                else:
                    logger.error("成绩推送失败")
            else:
                logger.warning("成绩抓取未返回有效数据")
        
        # 执行课表抓取
        if fetch_schedule:
            logger.info("开始抓取课表信息...")
            schedule_raw = school_module.fetch_course_schedule(username, password, force_update)
            
            if schedule_raw:
                logger.info("课表抓取成功")
                # 保存原始HTML到文件
                if isinstance(schedule_raw, str):
                    save_html_file(schedule_raw, "schedule.html")
                
                # 解析课表数据
                schedule_result = school_module.parse_schedule(schedule_raw)
                
                # 推送课表信息
                push_success = push_manager.push_schedule(schedule_result, push_method)
                if push_success:
                    logger.info("课表推送成功")
                else:
                    logger.error("课表推送失败")
            else:
                logger.warning("课表抓取未返回有效数据")
        
        # 返回结果
        result = {
            "success": bool(grades_result or schedule_result),
            "grades_captured": bool(grades_result),
            "schedule_captured": bool(schedule_result),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"抓取任务完成 - 结果: {result}")
        return result
        
    except Exception as e:
        logger.error(f"执行抓取任务时发生错误: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_school_info(school_code: str) -> Dict[str, Any]:
    """
    获取院校信息
    
    Args:
        school_code: 院校代码
    
    Returns:
        院校信息字典
    """
    try:
        # 获取插件管理器
        plugin_manager = get_plugin_manager()
        
        # 加载指定院校的插件
        school_module = plugin_manager.load_plugin(school_code)
        if not school_module:
            logger.error(f"未能加载院校 {school_code} 的插件")
            return {}
        
        # 获取院校信息
        school_info = {
            "school_code": school_code,
            "school_name": getattr(school_module, "SCHOOL_NAME", school_code),
            "plugin_version": getattr(school_module, "PLUGIN_VERSION", "unknown")
        }
        
        return school_info
    except Exception as e:
        logger.error(f"获取院校 {school_code} 信息时发生错误: {e}", exc_info=True)
        return {}


if __name__ == "__main__":
    # 示例用法
    result = run_capture("10546", "username", "password", "email")
    print(result)
