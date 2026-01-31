# -*- coding: utf-8 -*-
"""
插件管理标签页
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal
import logging
from core.plugins.plugin_manager import get_plugin_manager

logger = logging.getLogger(__name__)


class PluginManagementTab(QWidget):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.plugin_manager = get_plugin_manager()
        logger.info("PluginManagementTab 初始化")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 创建表格
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)  # 院校代码、院校名称、当前版本、最新版本、贡献者
        self.plugin_table.setHorizontalHeaderLabels(['院校代码', '院校名称', '当前版本', '最新版本', '贡献者'])
        header = self.plugin_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # 设置表格上下文菜单策略
        self.plugin_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.plugin_table.customContextMenuRequested.connect(self.show_context_menu)

        # 创建按钮布局
        btn_layout = QHBoxLayout()

        self.refresh_btn = QPushButton('刷新插件列表')
        self.check_update_btn = QPushButton('检查更新')

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.check_update_btn)
        btn_layout.addStretch()

        layout.addWidget(self.plugin_table)
        layout.addLayout(btn_layout)

        # 连接信号
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        self.check_update_btn.clicked.connect(self.check_updates)
        
        logger.info("PluginManagementTab UI 初始化完成")

    def show_context_menu(self, position):
        """显示右键菜单"""
        logger.debug(f"右键菜单被触发，位置: {position}")
        item = self.plugin_table.currentItem()
        if item is None:
            logger.warning("右键菜单：未选中任何项目")
            return
        
        row = item.row()
        code_item = self.plugin_table.item(row, 0)
        if code_item is None:
            logger.warning(f"右键菜单：无法获取第 {row} 行的院校代码")
            return
        
        school_code = code_item.text()
        logger.info(f"右键菜单：选中院校代码 {school_code}")
        
        menu = QMenu()
        
        # 获取当前版本信息
        current_version_item = self.plugin_table.item(row, 2)
        current_version = current_version_item.text() if current_version_item else ""
        
        logger.debug(f"院校 {school_code} 当前版本: {current_version}")
        
        # 根据当前状态显示不同的菜单项
        if current_version == "未安装":
            logger.debug(f"为未安装的插件 {school_code} 添加安装选项")
            install_action = menu.addAction('安装插件')
            install_action.triggered.connect(lambda: self.install_plugin(school_code))
        else:
            logger.debug(f"为已安装的插件 {school_code} 添加卸载选项")
            uninstall_action = menu.addAction('卸载插件')
            uninstall_action.triggered.connect(lambda: self.uninstall_plugin(school_code))
            
            # 检查更新选项
            logger.debug(f"为插件 {school_code} 添加检查更新选项")
            update_action = menu.addAction('检查此插件更新')
            update_action.triggered.connect(lambda: self.check_single_plugin_update(school_code))

        menu.exec_(self.plugin_table.viewport().mapToGlobal(position))
        logger.debug("右键菜单执行完毕")

    def install_plugin(self, school_code):
        """安装插件"""
        logger.info(f"开始安装插件 {school_code}")
        try:
            # 检查是否有更新
            update_info = self.plugin_manager.check_plugin_update(school_code)
            if update_info:
                logger.info(f"找到 {school_code} 的更新信息，开始下载安装")
                success = self.plugin_manager.download_and_install_plugin(school_code, update_info)
                if success:
                    logger.info(f"院校 {school_code} 插件安装成功")
                    QMessageBox.information(self, '成功', f'院校 {school_code} 插件安装成功')
                    # 刷新当前行的版本信息
                    self.refresh_single_row(school_code)
                else:
                    logger.error(f"院校 {school_code} 插件安装失败")
                    QMessageBox.critical(self, '错误', f'院校 {school_code} 插件安装失败')
            else:
                logger.info(f"未找到 {school_code} 的更新信息，尝试直接从索引安装")
                # 如果没有更新信息，尝试直接安装
                plugin_info = self.plugin_manager.get_plugin_info_from_index(school_code)
                if plugin_info:
                    success = self.plugin_manager.download_and_install_plugin(school_code, plugin_info)
                    if success:
                        logger.info(f"院校 {school_code} 插件安装成功")
                        QMessageBox.information(self, '成功', f'院校 {school_code} 插件安装成功')
                        self.refresh_single_row(school_code)
                    else:
                        logger.error(f"院校 {school_code} 插件安装失败")
                        QMessageBox.critical(self, '错误', f'院校 {school_code} 插件安装失败')
                else:
                    logger.warning(f"未找到院校 {school_code} 的插件信息")
                    QMessageBox.warning(self, '警告', f'未找到院校 {school_code} 的插件信息')
        except Exception as e:
            logger.error(f"安装插件 {school_code} 时发生错误: {str(e)}", exc_info=True)
            QMessageBox.critical(self, '错误', f'安装插件时发生错误: {str(e)}')

    def uninstall_plugin(self, school_code):
        """卸载插件"""
        logger.info(f"开始卸载插件 {school_code}")
        reply = QMessageBox.question(self, '确认', f'确定要卸载院校 {school_code} 的插件吗？', 
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            logger.info(f"用户确认卸载插件 {school_code}")
            try:
                import shutil
                from pathlib import Path
                plugin_dir = self.plugin_manager.plugins_dir / school_code
                if plugin_dir.exists():
                    logger.info(f"删除插件目录: {plugin_dir}")
                    shutil.rmtree(plugin_dir)
                    logger.info(f"院校 {school_code} 插件卸载成功")
                    QMessageBox.information(self, '成功', f'院校 {school_code} 插件卸载成功')
                    # 刷新当前行的版本信息
                    self.refresh_single_row(school_code)
                else:
                    logger.warning(f"院校 {school_code} 插件目录不存在: {plugin_dir}")
                    QMessageBox.warning(self, '警告', f'院校 {school_code} 插件不存在')
            except Exception as e:
                logger.error(f"卸载插件 {school_code} 时发生错误: {str(e)}", exc_info=True)
                QMessageBox.critical(self, '错误', f'卸载插件时发生错误: {str(e)}')
        else:
            logger.info(f"用户取消卸载插件 {school_code}")

    def check_single_plugin_update(self, school_code):
        """检查单个插件更新"""
        logger.info(f"检查单个插件 {school_code} 更新")
        try:
            update_info = self.plugin_manager.check_plugin_update(school_code)
            if update_info:
                remote_version = update_info.get('remote_version', '-')
                current_version = self.plugin_manager._get_local_plugin_version(school_code)
                
                logger.info(f"院校 {school_code}: 当前版本 {current_version}, 最新版本 {remote_version}")
                
                if self.plugin_manager._compare_version(remote_version, current_version) > 0:
                    logger.info(f"院校 {school_code} 有新版本可用")
                    reply = QMessageBox.question(self, '更新可用', 
                                               f'院校 {school_code} 有新版本可用\n'
                                               f'当前版本: {current_version}\n'
                                               f'最新版本: {remote_version}\n'
                                               '是否更新？',
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                    if reply == QMessageBox.Yes:
                        logger.info(f"用户同意更新插件 {school_code}")
                        success = self.plugin_manager.download_and_install_plugin(school_code, update_info)
                        if success:
                            logger.info(f"院校 {school_code} 插件更新成功")
                            QMessageBox.information(self, '成功', f'院校 {school_code} 插件更新成功')
                            self.refresh_single_row(school_code)
                        else:
                            logger.error(f"院校 {school_code} 插件更新失败")
                            QMessageBox.critical(self, '错误', f'院校 {school_code} 插件更新失败')
                    else:
                        logger.info(f"用户拒绝更新插件 {school_code}")
                else:
                    logger.info(f"院校 {school_code} 插件已是最新版本")
                    QMessageBox.information(self, '提示', f'院校 {school_code} 插件已是最新版本')
            else:
                logger.warning(f"未找到院校 {school_code} 的更新信息")
                QMessageBox.information(self, '提示', f'未找到院校 {school_code} 的更新信息')
        except Exception as e:
            logger.error(f"检查插件 {school_code} 更新时发生错误: {str(e)}", exc_info=True)
            QMessageBox.critical(self, '错误', f'检查更新时发生错误: {str(e)}')

    def refresh_single_row(self, school_code):
        """刷新单行数据"""
        logger.debug(f"刷新单行数据: {school_code}")
        for row in range(self.plugin_table.rowCount()):
            code_item = self.plugin_table.item(row, 0)
            if code_item and code_item.text() == school_code:
                # 更新当前版本
                current_version = self.plugin_manager._get_local_plugin_version(school_code)
                current_ver_item = QTableWidgetItem(current_version if current_version != "0.0.0" else "未安装")
                current_ver_item.setFlags(current_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 2, current_ver_item)
                logger.debug(f"已更新 {school_code} 的版本信息为: {current_version if current_version != '0.0.0' else '未安装'}")
                break

    def refresh_plugins(self):
        """刷新插件列表"""
        logger.info("开始刷新插件列表")
        try:
            # 清除插件索引缓存，强制重新获取最新数据
            logger.debug("清除插件索引缓存")
            self.plugin_manager.clear_plugins_index_cache()
            
            # 获取所有可用插件（从索引文件）
            all_plugins = {}
            plugins_index = self.plugin_manager._fetch_plugins_index()
            if plugins_index and isinstance(plugins_index, dict):
                plugins_list = plugins_index.get('plugins', [])
                logger.info(f"从插件索引获取到 {len(plugins_list)} 个插件")
                for plugin in plugins_list:
                    school_code = plugin.get('school_code')
                    school_name = plugin.get('school_name', school_code)
                    if school_code:
                        all_plugins[school_code] = school_name
                        logger.debug(f"插件索引中找到: {school_code} - {school_name}")
            else:
                logger.warning("无法获取插件索引或插件索引为空")
            
            # 同时获取已安装的插件
            installed_plugins = self.plugin_manager.get_available_plugins()
            logger.info(f"已安装插件数量: {len(installed_plugins)}")
            for code, name in installed_plugins.items():
                logger.debug(f"已安装插件: {code} - {name}")
            
            # 合并插件列表，确保所有索引中的插件都显示（即使未安装）
            combined_plugins = dict(all_plugins)
            combined_plugins.update(installed_plugins)  # 已安装的插件可能会提供更准确的名称
            
            logger.info(f"合并后插件总数: {len(combined_plugins)}")
            
            self.plugin_table.setRowCount(len(combined_plugins))
            
            for row, (code, name) in enumerate(combined_plugins.items()):
                logger.debug(f"填充第 {row} 行: {code} - {name}")
                # 院校代码
                code_item = QTableWidgetItem(code)
                code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 0, code_item)
                
                # 院校名称
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 1, name_item)
                
                # 当前版本 - 检查是否已安装
                current_version = self.plugin_manager._get_local_plugin_version(code)
                version_display = current_version if current_version != "0.0.0" else "未安装"
                logger.debug(f"插件 {code} 当前版本: {version_display}")
                current_ver_item = QTableWidgetItem(version_display)
                current_ver_item.setFlags(current_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 2, current_ver_item)
                
                # 最新版本（暂时显示为未知，需要检查更新后才能知道）
                latest_ver_item = QTableWidgetItem('-')
                latest_ver_item.setFlags(latest_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 3, latest_ver_item)
                
                # 贡献者（暂时显示为未知，需要检查更新后才能知道）
                contributor_item = QTableWidgetItem('-')
                contributor_item.setFlags(contributor_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 4, contributor_item)
                
            logger.info("插件列表刷新完成")
        except Exception as e:
            logger.error(f"刷新插件列表失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, '错误', f'刷新插件列表失败: {str(e)}')

    def check_updates(self):
        """检查插件更新"""
        logger.info("开始检查所有插件更新")
        try:
            for row in range(self.plugin_table.rowCount()):
                code_item = self.plugin_table.item(row, 0)
                if code_item:
                    school_code = code_item.text()
                    logger.debug(f"检查第 {row} 行插件 {school_code} 的更新")
                    
                    # 检查更新
                    update_info = self.plugin_manager.check_plugin_update(school_code)
                    if update_info:
                        latest_version = update_info.get('remote_version', '-')
                        contributor = update_info.get('contributor', 'Unknown')
                        logger.info(f"插件 {school_code} 有更新: {latest_version}")
                    else:
                        # 如果没有更新，使用当前版本作为最新版本显示
                        latest_version = self.plugin_manager._get_local_plugin_version(school_code)
                        latest_version = latest_version if latest_version != "0.0.0" else "未安装"
                        contributor = 'Unknown'
                        logger.info(f"插件 {school_code} 无更新或获取更新信息失败")
                    
                    # 更新最新版本列
                    latest_ver_item = QTableWidgetItem(latest_version)
                    latest_ver_item.setFlags(latest_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.plugin_table.setItem(row, 3, latest_ver_item)
                    
                    # 更新贡献者列
                    contributor_item = QTableWidgetItem(contributor)
                    contributor_item.setFlags(contributor_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.plugin_table.setItem(row, 4, contributor_item)
                    
            logger.info("插件更新检查完成")
        except Exception as e:
            logger.error(f"检查更新失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, '错误', f'检查更新失败: {str(e)}')


class PluginUpdateWorker(QThread):
    """插件更新工作线程"""
    finished = Signal(bool, str)  # 成功标志和消息
    
    def __init__(self, plugin_manager, school_code):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.school_code = school_code
        logger.debug(f"创建插件更新工作线程: {school_code}")
    
    def run(self):
        logger.info(f"开始执行插件更新任务: {self.school_code}")
        try:
            # 检查更新
            update_info = self.plugin_manager.check_plugin_update(self.school_code)
            if update_info:
                logger.info(f"找到插件 {self.school_code} 的更新信息，开始下载安装")
                # 下载并安装更新
                success = self.plugin_manager.download_and_install_plugin(self.school_code, update_info)
                if success:
                    logger.info(f"插件 {self.school_code} 更新成功")
                    self.finished.emit(True, f'院校 {self.school_code} 插件更新成功')
                else:
                    logger.error(f"插件 {self.school_code} 更新失败")
                    self.finished.emit(False, f'院校 {self.school_code} 插件更新失败')
            else:
                logger.info(f"插件 {self.school_code} 已是最新版本")
                self.finished.emit(True, f'院校 {self.school_code} 插件已是最新版本')
        except Exception as e:
            logger.error(f"更新插件 {self.school_code} 时发生错误: {str(e)}", exc_info=True)
            self.finished.emit(False, f'更新过程中发生错误: {str(e)}')