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
        
        # 添加监听器，当用户选择院校时记录选择
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
        # 连接文本改变信号，用于处理用户输入新密码的情况
        self.password_input.textChanged.connect(self._on_password_text_changed)
        school_account_layout.addRow("密码:", self.password_input)
        
        # 存储实际密码值，用于保存时使用
        self._actual_password = ""
        
        # 提示标签
        self.plugin_hint_label = QLabel("提示: 显示已安装的院校模块。如未显示新安装的插件，可点击刷新按钮更新列表")
        self.plugin_hint_label.setWordWrap(True)
        self.plugin_hint_label.setStyleSheet("color: #0066cc; font-style: italic;")
        school_account_layout.addRow(self.plugin_hint_label)
        
        # 主布局
        layout.addWidget(school_account_group)
        
        # 先加载配置获取院校代码
        self.load_config()
        # 然后刷新院校列表并设置默认选择
        self.refresh_available_plugins()
    
    def _on_password_text_changed(self, text):
        """处理密码输入框文本变化"""
        # 当用户开始输入新密码时，清除占位符（如果有的话）
        if text:  # 如果有输入内容
            self.password_input.setPlaceholderText("")
        elif not self._actual_password:  # 如果没有输入内容，且没有保存的密码
            self.password_input.setPlaceholderText("请输入密码")  # 恢复原始占位符
        else:  # 如果没有输入内容，但有保存的密码
            self.password_input.setPlaceholderText("••••••••")  # 显示隐藏密码占位符
    
    def on_school_selected(self, text):
        """当用户选择院校时调用此方法"""
        # 如果正在刷新，则不执行任何操作，避免无限循环
        if self.refresh_in_progress:
            return
        # 记录用户当前选择
        self._current_selection = self.school_selector_combo.currentData()
        logger.info(f"用户选择了院校: {text}, 代码: {self._current_selection}")
    
    def manual_refresh_plugins(self):
        """手动刷新已安装的插件列表"""
        logger.info("用户手动刷新已安装插件列表")
        try:
            # 清除插件索引缓存
            logger.debug("清除插件索引缓存")
            self.plugin_manager.clear_plugins_index_cache()
            
            # 刷新已安装插件列表
            self.refresh_available_plugins()
            
            QMessageBox.information(self, "提示", "已安装院校列表刷新成功")
        except Exception as e:
            logger.error(f"手动刷新插件列表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"刷新已安装院校列表失败: {str(e)}")
    
    def refresh_available_plugins(self):
        """刷新可用插件列表并设置默认选择"""
        try:
            # 设置刷新标志，防止在此期间触发选择变化事件
            self.refresh_in_progress = True
            
            # 强制刷新插件索引，确保获取最新数据
            self.plugin_manager.clear_plugins_index_cache()
            
            # 只获取已安装的插件
            available_plugins = self.plugin_manager.get_available_plugins()
            
            self.school_selector_combo.clear()
            
            # 如果没有可用插件，至少添加一个占位选项
            if not available_plugins:
                self.school_selector_combo.addItem("暂无可用院校插件，请前往插件管理页面下载", "")
                logger.warning("未找到任何可用插件")
            else:
                for code, name in available_plugins.items():
                    self.school_selector_combo.addItem(f"{code} - {name}", code)
                logger.info(f"刷新可用插件列表，共找到 {len(available_plugins)} 个插件")
                
                # 设置配置文件中保存的默认选择
                if hasattr(self, '_saved_school_code') and self._saved_school_code:
                    index = self.school_selector_combo.findData(self._saved_school_code)
                    if index >= 0:
                        self.school_selector_combo.setCurrentIndex(index)
                        logger.info(f"设置默认院校选择: {self._saved_school_code}")
                    else:
                        logger.warning(f"配置文件中的院校代码 {self._saved_school_code} 在插件列表中未找到")
                
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
                    self._actual_password = password  # 保存实际密码值
                    # 如果密码存在，则显示占位符（如星号）而不是实际密码
                    if password:
                        self.password_input.setPlaceholderText("••••••••")  # 显示隐藏密码的占位符
                        # 设置文本为空，只显示占位符
                        self.password_input.setText("")
                    # 不在UI中显示实际密码
                except:
                    pass
                
                # 加载学校代码（暂存，稍后在refresh_available_plugins中设置）
                try:
                    self._saved_school_code = config.get('account', 'school_code', fallback='')
                    if self._saved_school_code:
                        logger.info(f"读取到配置文件中的院校代码: {self._saved_school_code}")
                except Exception as e:
                    logger.error(f"读取学校代码配置失败: {e}")
                    self._saved_school_code = ''
            else:
                # 如果是字典类型的配置
                config = self.config_manager if isinstance(self.config_manager, dict) else {}
                
                # 加载学号
                student_id = config.get('account', {}).get('username', '')
                self.student_id_input.setText(student_id)
                
                # 加载密码
                password = config.get('account', {}).get('password', '')
                self._actual_password = password  # 保存实际密码值
                # 如果密码存在，则显示占位符（如星号）而不是实际密码
                if password:
                    self.password_input.setPlaceholderText("••••••••")  # 显示隐藏密码的占位符
                    # 设置文本为空，只显示占位符
                    self.password_input.setText("")
                # 不在UI中显示实际密码
                
                # 加载学校代码（暂存，稍后在refresh_available_plugins中设置）
                self._saved_school_code = config.get('account', {}).get('school_code', '')
                if self._saved_school_code:
                    logger.info(f"读取到配置文件中的院校代码: {self._saved_school_code}")
            
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
                # 如果密码输入框为空，则使用之前保存的密码值，否则使用当前输入的值
                current_password = self.password_input.text()
                if not current_password:  # 如果当前输入为空，则使用原密码
                    current_password = self._actual_password
                else:  # 否则更新实际密码值
                    self._actual_password = current_password
                config.set('account', 'password', current_password)
                
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
                # 如果密码输入框为空，则使用之前保存的密码值，否则使用当前输入的值
                current_password = self.password_input.text()
                if not current_password:  # 如果当前输入为空，则使用原密码
                    current_password = self._actual_password
                else:  # 否则更新实际密码值
                    self._actual_password = current_password
                self.config_manager['account']['password'] = current_password
                
                # 保存学校代码
                school_code = self.school_selector_combo.currentData()
                if school_code:
                    self.config_manager['account']['school_code'] = school_code
                
                logger.info("基本配置已保存")