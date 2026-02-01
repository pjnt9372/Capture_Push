# -*- coding: utf-8 -*-
"""
基础设置标签页
包含基本配置选项
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, 
    QLineEdit, QCheckBox, QPushButton, QLabel, 
    QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
import os
from core.log import get_logger
from core.plugins.plugin_manager import get_plugin_manager

logger = get_logger()


class BasicTab(QWidget):
    """基础设置标签页类"""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.plugin_manager = get_plugin_manager()
        # 防止刷新时触发选择变化事件的标志
        self.refresh_in_progress = False
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 院校和账户设置组
        school_account_group = QGroupBox("院校与账户设置")
        school_account_layout = QFormLayout(school_account_group)
        
        # 院校选择
        self.school_selector_label = QLabel("选择院校:")
        self.school_selector_combo = QComboBox()
        self.school_selector_combo.setMinimumWidth(200)
        
        
        # 院校选择布局
        school_hbox = QHBoxLayout()
        school_hbox.addWidget(self.school_selector_combo)
        
        # 添加刷新插件按钮
        self.refresh_plugins_btn = QPushButton("刷新")
        self.refresh_plugins_btn.clicked.connect(self.manual_refresh_plugins)
        school_hbox.addWidget(self.refresh_plugins_btn)
        
        school_hbox.addStretch()
        
        # 添加监听器，当用户选择院校时自动刷新
        self.school_selector_combo.currentTextChanged.connect(self.on_school_selected)
        
        school_account_layout.addRow(self.school_selector_label, school_hbox)
        
        # 学号输入
        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("请输入学号")
        school_account_layout.addRow("学号:", self.student_id_input)
        
        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        school_account_layout.addRow("密码:", self.password_input)
        
        # 提示标签
        self.plugin_hint_label = QLabel("提示: 如果列表中没有您需要的院校，请前往插件管理页面下载相应插件。如果安装了此处未显示可点击刷新")
        self.plugin_hint_label.setWordWrap(True)
        self.plugin_hint_label.setStyleSheet("color: #0066cc; font-style: italic;")
        school_account_layout.addRow(self.plugin_hint_label)
        
        
        # 主布局
        layout.addWidget(school_account_group)
        
        
        # 加载初始配置
        self.load_config()
        # 刷新院校列表
        self.refresh_available_plugins()
    
    def on_school_selected(self, text):
        """当用户选择院校时调用此方法"""
        # 如果正在刷新，则不执行任何操作，避免无限循环
        if self.refresh_in_progress:
            return
        # 刷新院校列表以更新可选项
        self.refresh_available_plugins()
        logger.info(f"用户选择了院校: {text}")
    
    def manual_refresh_plugins(self):
        """手动刷新插件列表，清除缓存并强制重新获取最新数据"""
        logger.info("用户手动刷新插件列表")
        try:
            # 清除插件索引缓存，强制重新获取最新数据
            logger.debug("清除插件索引缓存")
            self.plugin_manager.clear_plugins_index_cache()
            
            # 强制刷新插件列表
            self.refresh_available_plugins()
            
            QMessageBox.information(self, "提示", "院校列表刷新成功")
        except Exception as e:
            logger.error(f"手动刷新插件列表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"手动刷新院校列表失败: {str(e)}")
    
    def refresh_available_plugins(self):
        """刷新可用插件列表"""
        try:
            # 设置刷新标志，防止在此期间触发选择变化事件
            self.refresh_in_progress = True
            
            available_plugins = self.plugin_manager.get_available_plugins()
            
            # 保存当前选择
            current_text = self.school_selector_combo.currentText()
            # 提取当前选择的学校代码（假设格式为 'code - name'）
            current_code = None
            if ' - ' in current_text:
                current_code = current_text.split(' - ')[0]
            
            self.school_selector_combo.clear()
            for code, name in available_plugins.items():
                self.school_selector_combo.addItem(f"{code} - {name}", code)
            
            # 尝試恢復之前的選項
            if current_code:
                index = self.school_selector_combo.findData(current_code)
                if index >= 0:
                    self.school_selector_combo.setCurrentIndex(index)
            
            logger.info(f"刷新可用插件列表，共找到 {len(available_plugins)} 个插件")
        except Exception as e:
            logger.error(f"刷新可用插件列表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"刷新可用插件列表失败: {str(e)}")
        finally:
            # 重置刷新标志
            self.refresh_in_progress = False
    
    def load_config(self):
        """加载配置"""
        if self.config_manager:
            # 检查是否是ConfigParser实例
            if hasattr(self.config_manager, 'get'):
                config = self.config_manager
                # 加载学号
                try:
                    student_id = config.get('account', 'username', fallback='')
                    self.student_id_input.setText(student_id)
                except:
                    pass
                
                # 加载密码
                try:
                    password = config.get('account', 'password', fallback='')
                    self.password_input.setText(password)
                except:
                    pass
                
                # 加载学校代码
                try:
                    school_code = config.get('account', 'school_code', fallback='')
                    if school_code:
                        # 先刷新插件列表以确保学校代码在下拉框中
                        self.refresh_available_plugins()
                        # 等待刷新完成后再设置当前选择
                        index = self.school_selector_combo.findData(school_code)
                        if index >= 0:
                            self.school_selector_combo.setCurrentIndex(index)
                except:
                    pass
            else:
                # 如果是字典类型的配置
                config = self.config_manager if isinstance(self.config_manager, dict) else {}
                
                # 加载学号
                student_id = config.get('account', {}).get('username', '')
                self.student_id_input.setText(student_id)
                
                # 加载密码
                password = config.get('account', {}).get('password', '')
                self.password_input.setText(password)
                
                # 加载学校代码
                school_code = config.get('account', {}).get('school_code', '')
                if school_code:
                    # 先刷新插件列表以确保学校代码在下拉框中
                    self.refresh_available_plugins()
                    # 等待刷新完成后再设置当前选择
                    index = self.school_selector_combo.findData(school_code)
                    if index >= 0:
                        self.school_selector_combo.setCurrentIndex(index)
            
            logger.info("配置加载完成")
    
    def save_config(self):
        """保存基本配置到配置管理器"""
        if self.config_manager:
            # 检查是否是ConfigParser实例
            if hasattr(self.config_manager, 'set'):
                config = self.config_manager
                # 确保存在所需的section
                if not config.has_section('account'):
                    config.add_section('account')
                
                # 保存学号
                config.set('account', 'username', self.student_id_input.text())
                
                # 保存密码
                config.set('account', 'password', self.password_input.text())
                
                # 保存学校代码
                school_code = self.school_selector_combo.currentData()
                if school_code:
                    config.set('account', 'school_code', school_code)
                
                logger.info("基本配置已保存")
            else:
                # 如果是字典类型的配置
                if 'account' not in self.config_manager:
                    self.config_manager['account'] = {}
                
                # 保存学号
                self.config_manager['account']['username'] = self.student_id_input.text()
                
                # 保存密码
                self.config_manager['account']['password'] = self.password_input.text()
                
                # 保存学校代码
                school_code = self.school_selector_combo.currentData()
                if school_code:
                    self.config_manager['account']['school_code'] = school_code
                
                logger.info("基本配置已保存")