# -*- coding: utf-8 -*-
"""
成绩窗口模块
显示成绩信息的GUI窗口
"""

import sys
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QComboBox, 
    QFileDialog, QMessageBox, QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
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


class GradesCaptureWorker(QThread):
    """成绩抓取工作线程"""
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
            
            self.progress.emit(30, "正在抓取成绩信息...")
            
            # 调用插件的fetch_grades函数
            grades_data = school_module.fetch_grades(self.username, self.password, self.force_update)
            
            if grades_data:
                self.progress.emit(90, "处理完成")
                self.finished.emit(True, "成绩抓取成功", grades_data)
            else:
                self.finished.emit(False, "未能获取成绩数据", {})
                
        except Exception as e:
            logger.error(f"成绩抓取失败: {e}", exc_info=True)
            self.finished.emit(False, f"成绩抓取失败: {str(e)}", {})


class GradesWindow(QMainWindow):
    """成绩窗口类"""
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.plugin_manager = get_plugin_manager()
        self.grades_data = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('成绩查看')
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
        
        self.capture_btn = QPushButton('抓取成绩')
        self.capture_btn.clicked.connect(self.capture_grades)
        
        self.export_btn = QPushButton('导出成绩')
        self.export_btn.clicked.connect(self.export_grades)
        
        self.push_btn = QPushButton('推送成绩')
        self.push_btn.clicked.connect(self.push_grades)
        
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
        
        # 成绩表格
        self.grades_table = QTableWidget()
        self.grades_table.setColumnCount(7)  # 课程名称、学分、成绩、绩点、学期、考试类型、备注
        self.grades_table.setHorizontalHeaderLabels(['课程名称', '学分', '成绩', '绩点', '学期', '考试类型', '备注'])
        
        # 设置表格列宽
        header = self.grades_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 课程名称占最大空间
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 学分
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 成绩
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 绩点
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 学期
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 考试类型
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 备注
        
        layout.addWidget(self.grades_table)
        
        # 加载配置
        self.load_config()
        
        # 连接信号
        self.capture_btn.clicked.connect(self.capture_grades)
        self.export_btn.clicked.connect(self.export_grades)
        self.push_btn.clicked.connect(self.push_grades)
        
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
    
    def capture_grades(self):
        """抓取成绩"""
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
        self.worker = GradesCaptureWorker(school_code, username, password, force_update)
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
            self.grades_data = data
            self.display_grades(data)
            self.status_label.setText(f'成绩抓取成功 - 共{len(data.get("grades", []))}门课程')
            QMessageBox.information(self, '成功', message)
        else:
            self.status_label.setText('成绩抓取失败')
            QMessageBox.critical(self, '错误', message)
    
    def display_grades(self, grades_data: dict):
        """显示成绩数据"""
        if not grades_data or 'grades' not in grades_data:
            return
            
        grades = grades_data['grades']
        self.grades_table.setRowCount(len(grades))
        
        for row, grade in enumerate(grades):
            # 课程名称
            course_name_item = QTableWidgetItem(grade.get('course_name', ''))
            self.grades_table.setItem(row, 0, course_name_item)
            
            # 学分
            credit_item = QTableWidgetItem(str(grade.get('credit', '')))
            credit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grades_table.setItem(row, 1, credit_item)
            
            # 成绩
            score_item = QTableWidgetItem(grade.get('score', ''))
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grades_table.setItem(row, 2, score_item)
            
            # 绩点
            grade_point_item = QTableWidgetItem(str(grade.get('grade_point', '')))
            grade_point_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grades_table.setItem(row, 3, grade_point_item)
            
            # 学期
            semester_item = QTableWidgetItem(grade.get('semester', ''))
            self.grades_table.setItem(row, 4, semester_item)
            
            # 考试类型
            exam_type_item = QTableWidgetItem(grade.get('exam_type', ''))
            self.grades_table.setItem(row, 5, exam_type_item)
            
            # 备注
            remarks_item = QTableWidgetItem(grade.get('remarks', ''))
            self.grades_table.setItem(row, 6, remarks_item)
    
    def export_grades(self):
        """导出成绩"""
        if not self.grades_data:
            QMessageBox.warning(self, '警告', '没有可导出的成绩数据')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出成绩', '', 'CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*)'
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                # 导出为CSV
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['course_name', 'credit', 'score', 'grade_point', 'semester', 'exam_type', 'remarks']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for grade in self.grades_data.get('grades', []):
                        writer.writerow({
                            'course_name': grade.get('course_name', ''),
                            'credit': grade.get('credit', ''),
                            'score': grade.get('score', ''),
                            'grade_point': grade.get('grade_point', ''),
                            'semester': grade.get('semester', ''),
                            'exam_type': grade.get('exam_type', ''),
                            'remarks': grade.get('remarks', '')
                        })
            elif file_path.endswith('.json'):
                # 导出为JSON
                with open(file_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(self.grades_data, jsonfile, ensure_ascii=False, indent=2)
            else:
                # 默认导出为JSON
                with open(file_path + '.json', 'w', encoding='utf-8') as jsonfile:
                    json.dump(self.grades_data, jsonfile, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, '成功', f'成绩已导出到: {file_path}')
        except Exception as e:
            logger.error(f"导出成绩失败: {e}", exc_info=True)
            QMessageBox.critical(self, '错误', f'导出成绩失败: {str(e)}')
    
    def push_grades(self):
        """推送成绩"""
        if not self.grades_data:
            QMessageBox.warning(self, '警告', '没有可推送的成绩数据')
            return
            
        try:
            push_manager = PushManager()
            success = push_manager.push_grades(self.grades_data, 'email')  # 默认使用邮件推送
            
            if success:
                QMessageBox.information(self, '成功', '成绩推送成功')
            else:
                QMessageBox.critical(self, '错误', '成绩推送失败')
        except Exception as e:
            logger.error(f"推送成绩失败: {e}", exc_info=True)
            QMessageBox.critical(self, '错误', f'推送成绩失败: {str(e)}')