# -*- coding: utf-8 -*-
"""
课表窗口模块
显示课表信息的GUI窗口
"""

import sys
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QComboBox, 
    QFileDialog, QMessageBox, QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import json
import csv
from pathlib import Path

# 添加项目根目录到模块搜索路径
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.log import get_logger
from core.push import PushManager
from core.plugins.plugin_manager import get_plugin_manager

logger = get_logger()


class ScheduleCaptureWorker(QThread):
    """课表抓取工作线程"""
    finished = Signal(bool, str, dict)  # 成功标志、消息、数据
    progress = Signal(int, str)  # 进度百分比、状态信息

    def __init__(self, school_code: str, username: str, password: str, force_update: bool = False):
        super().__init__()
        self.school_code = school_code
        self.username = username
        self.password = password
        self.force_update = force_update

    def run(self):
        try:
            self.progress.emit(10, "正在加载插件...")
            
            # 获取插件管理器
            plugin_manager = get_plugin_manager()
            
            # 加载指定院校的插件
            school_module = plugin_manager.load_plugin(self.school_code)
            if not school_module:
                self.finished.emit(False, f"未能加载院校 {self.school_code} 的插件", {})
                return
            
            self.progress.emit(30, "正在抓取课表信息...")
            
            # 调用插件的fetch_course_schedule函数
            schedule_data = school_module.fetch_course_schedule(self.username, self.password, self.force_update)
            
            if schedule_data:
                self.progress.emit(90, "处理完成")
                self.finished.emit(True, "课表抓取成功", schedule_data)
            else:
                self.finished.emit(False, "未能获取课表数据", {})
                
        except Exception as e:
            logger.error(f"课表抓取失败: {e}", exc_info=True)
            self.finished.emit(False, f"课表抓取失败: {str(e)}", {})


class ScheduleWindow(QMainWindow):
    """课表窗口类"""
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.plugin_manager = get_plugin_manager()
        self.schedule_data = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('课表查看')
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.school_code_label = QLabel('院校代码:')
        self.school_code_combo = QComboBox()
        self.school_code_combo.setEditable(True)
        
        self.username_label = QLabel('用户名:')
        self.username_input = QLineEdit()
        
        self.password_label = QLabel('密码:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.force_update_checkbox = QPushButton('强制更新')
        self.force_update_checkbox.setCheckable(True)
        
        self.capture_btn = QPushButton('抓取课表')
        self.capture_btn.clicked.connect(self.capture_schedule)
        
        self.export_btn = QPushButton('导出课表')
        self.export_btn.clicked.connect(self.export_schedule)
        
        self.push_btn = QPushButton('推送课表')
        self.push_btn.clicked.connect(self.push_schedule)
        
        control_layout.addWidget(self.school_code_label)
        control_layout.addWidget(self.school_code_combo)
        control_layout.addWidget(self.username_label)
        control_layout.addWidget(self.username_input)
        control_layout.addWidget(self.password_label)
        control_layout.addWidget(self.password_input)
        control_layout.addWidget(self.force_update_checkbox)
        control_layout.addWidget(self.capture_btn)
        control_layout.addWidget(self.export_btn)
        control_layout.addWidget(self.push_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态栏
        self.status_label = QLabel('就绪')
        layout.addWidget(self.status_label)
        
        # 课表表格
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(7)  # 课程名称、教师、教室、星期、节次、周次、学期
        self.schedule_table.setHorizontalHeaderLabels(['课程名称', '教师', '教室', '星期', '节次', '周次', '学期'])
        
        # 设置表格列宽
        header = self.schedule_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 课程名称占最大空间
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 教师
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 教室
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 星期
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 节次
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 周次
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 学期
        
        layout.addWidget(self.schedule_table)
        
        # 加载配置
        self.load_config()
        
        # 连接信号
        self.capture_btn.clicked.connect(self.capture_schedule)
        self.export_btn.clicked.connect(self.export_schedule)
        self.push_btn.clicked.connect(self.push_schedule)
        
    def load_config(self):
        """加载配置"""
        if self.config_manager:
            config = self.config_manager.get_config()
            # 加载常用院校代码
            recent_schools = config.get('recent_schools', [])
            self.school_code_combo.addItems(recent_schools)
            
            # 加载最近使用的用户名
            recent_username = config.get('recent_username', '')
            self.username_input.setText(recent_username)
    
    def save_config(self):
        """保存配置"""
        if self.config_manager:
            config = self.config_manager.get_config()
            
            # 保存最近使用的院校代码
            school_code = self.school_code_combo.currentText()
            recent_schools = config.get('recent_schools', [])
            if school_code not in recent_schools:
                recent_schools.insert(0, school_code)
                # 只保留最近的10个院校代码
                recent_schools = recent_schools[:10]
            config['recent_schools'] = recent_schools
            
            # 保存最近使用的用户名
            config['recent_username'] = self.username_input.text()
            
            self.config_manager.save_config(config)
    
    def capture_schedule(self):
        """抓取课表"""
        school_code = self.school_code_combo.currentText().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        force_update = self.force_update_checkbox.isChecked()
        
        if not school_code or not username or not password:
            QMessageBox.warning(self, '警告', '请填写完整的院校代码、用户名和密码')
            return
        
        # 保存配置
        self.save_config()
        
        # 创建并启动工作线程
        self.worker = ScheduleCaptureWorker(school_code, username, password, force_update)
        self.worker.finished.connect(self.on_capture_finished)
        self.worker.progress.connect(self.on_progress_update)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.capture_btn.setEnabled(False)
        
        self.worker.start()
        
    def on_progress_update(self, progress: int, status: str):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        
    def on_capture_finished(self, success: bool, message: str, data: dict):
        """抓取完成回调"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.capture_btn.setEnabled(True)
        
        if success:
            self.schedule_data = data
            self.display_schedule(data)
            self.status_label.setText(f'课表抓取成功 - 共{len(data.get("schedule", []))}门课程')
            QMessageBox.information(self, '成功', message)
        else:
            self.status_label.setText('课表抓取失败')
            QMessageBox.critical(self, '错误', message)
    
    def display_schedule(self, schedule_data: dict):
        """显示课表数据"""
        if not schedule_data or 'schedule' not in schedule_data:
            return
            
        schedule = schedule_data['schedule']
        self.schedule_table.setRowCount(len(schedule))
        
        # 星期映射
        weekday_map = {
            1: '星期一', 2: '星期二', 3: '星期三', 4: '星期四', 
            5: '星期五', 6: '星期六', 7: '星期日'
        }
        
        for row, course in enumerate(schedule):
            # 课程名称
            course_name_item = QTableWidgetItem(course.get('course_name', ''))
            self.schedule_table.setItem(row, 0, course_name_item)
            
            # 教师
            teacher_item = QTableWidgetItem(course.get('teacher', ''))
            self.schedule_table.setItem(row, 1, teacher_item)
            
            # 教室
            classroom_item = QTableWidgetItem(course.get('classroom', ''))
            self.schedule_table.setItem(row, 2, classroom_item)
            
            # 星期
            week_day = course.get('week_day', 0)
            weekday_item = QTableWidgetItem(weekday_map.get(week_day, f'星期{week_day}'))
            weekday_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.schedule_table.setItem(row, 3, weekday_item)
            
            # 节次
            period_start = course.get('period_start', '')
            period_end = course.get('period_end', '')
            if period_start == period_end:
                period_item = QTableWidgetItem(f'第{period_start}节')
            else:
                period_item = QTableWidgetItem(f'第{period_start}-{period_end}节')
            period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.schedule_table.setItem(row, 4, period_item)
            
            # 周次
            weeks_item = QTableWidgetItem(course.get('weeks', ''))
            self.schedule_table.setItem(row, 5, weeks_item)
            
            # 学期
            semester_item = QTableWidgetItem(course.get('semester', ''))
            self.schedule_table.setItem(row, 6, semester_item)
    
    def export_schedule(self):
        """导出课表"""
        if not self.schedule_data:
            QMessageBox.warning(self, '警告', '没有可导出的课表数据')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出课表', '', 'CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*)'
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                # 导出为CSV
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['course_name', 'teacher', 'classroom', 'week_day', 'period_start', 'period_end', 'weeks', 'semester']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for course in self.schedule_data.get('schedule', []):
                        writer.writerow({
                            'course_name': course.get('course_name', ''),
                            'teacher': course.get('teacher', ''),
                            'classroom': course.get('classroom', ''),
                            'week_day': course.get('week_day', ''),
                            'period_start': course.get('period_start', ''),
                            'period_end': course.get('period_end', ''),
                            'weeks': course.get('weeks', ''),
                            'semester': course.get('semester', '')
                        })
            elif file_path.endswith('.json'):
                # 导出为JSON
                with open(file_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(self.schedule_data, jsonfile, ensure_ascii=False, indent=2)
            else:
                # 默认导出为JSON
                with open(file_path + '.json', 'w', encoding='utf-8') as jsonfile:
                    json.dump(self.schedule_data, jsonfile, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, '成功', f'课表已导出到: {file_path}')
        except Exception as e:
            logger.error(f"导出课表失败: {e}", exc_info=True)
            QMessageBox.critical(self, '错误', f'导出课表失败: {str(e)}')
    
    def push_schedule(self):
        """推送课表"""
        if not self.schedule_data:
            QMessageBox.warning(self, '警告', '没有可推送的课表数据')
            return
            
        try:
            push_manager = PushManager()
            success = push_manager.push_schedule(self.schedule_data, 'email')  # 默认使用邮件推送
            
            if success:
                QMessageBox.information(self, '成功', '课表推送成功')
            else:
                QMessageBox.critical(self, '错误', '课表推送失败')
        except Exception as e:
            logger.error(f"推送课表失败: {e}", exc_info=True)
            QMessageBox.critical(self, '错误', f'推送课表失败: {str(e)}')