# -*- coding: utf-8 -*-
"""
学校插件模板
这是一个示例插件，展示了插件的基本结构
"""

from getCourseGrades import fetch_grades, parse_grades
from getCourseSchedule import fetch_course_schedule, parse_schedule

SCHOOL_NAME = "示例学校12345"  # 学校名称
PLUGIN_VERSION = "1.0.0"      # 插件版本

__all__ = ['fetch_grades', 'parse_grades', 'fetch_course_schedule', 'parse_schedule', 
           'SCHOOL_NAME', 'PLUGIN_VERSION']