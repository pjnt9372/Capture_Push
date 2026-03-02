# -*- coding: utf-8 -*-
"""
数据传输标签页
集成文件导出、网络传输、二维码生成功能到GUI界面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QTextEdit, QFileDialog,
    QMessageBox, QProgressBar, QTabWidget, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QPixmap
import base64
import json
from pathlib import Path

# 导入日志模块
try:
    from log import get_logger
except ImportError:
    from core.log import get_logger

logger = get_logger('data_transfer_tab')

# 导入数据传输模块
try:
    from core.data_exporter import export_full_data, export_schedule_only, get_export_summary
    from core.export_methods.file_exporter import export_to_file, get_recent_exports, get_export_directory
    from core.export_methods.network_server import start_server, stop_server, get_server_status
    from core.export_methods.qrcode_generator import (
        generate_network_qr_code, generate_direct_data_qr_code, 
        save_qr_image, QR_CODE_AVAILABLE
    )
except ImportError as e:
    logger.error(f"导入数据传输模块失败: {e}")


class NetworkServerThread(QThread):
    """网络服务器线程"""
    status_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        
    def run(self):
        """运行服务器"""
        self.running = True
        try:
            # 启动服务器
            success = start_server("0.0.0.0", 8080)
            if success:
                # 定期发送状态更新
                while self.running:
                    status = get_server_status()
                    self.status_changed.emit(status)
                    self.msleep(1000)  # 每秒更新一次
        except Exception as e:
            logger.error(f"服务器线程运行出错: {e}")
            
    def stop(self):
        """停止服务器"""
        self.running = False
        stop_server()


class DataTransferTab(QWidget):
    """数据传输标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_thread = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 创建主标签页控件
        main_tab_widget = QTabWidget()
        
        # 文件传输标签页
        file_tab = self.create_file_transfer_tab()
        main_tab_widget.addTab(file_tab, "📁 文件传输")
        
        # 网络传输标签页
        network_tab = self.create_network_transfer_tab()
        main_tab_widget.addTab(network_tab, "🌐 网络传输")
        
        # 数据摘要标签页
        summary_tab = self.create_summary_tab()
        main_tab_widget.addTab(summary_tab, "📊 数据摘要")
        
        main_layout.addWidget(main_tab_widget)
        
    def create_file_transfer_tab(self):
        """创建文件传输标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 导出选项组
        export_group = QGroupBox("数据导出选项")
        export_layout = QVBoxLayout(export_group)
        
        # 导出说明
        info_label = QLabel("导出完整的课表数据（包含课程时间配置）")
        info_label.setWordWrap(True)
        export_layout.addWidget(info_label)
        
        # 导出按钮
        export_buttons_layout = QHBoxLayout()
        
        self.export_button = QPushButton("导出完整数据到文件")
        self.export_button.clicked.connect(self.handle_export)
        export_buttons_layout.addWidget(self.export_button)
        
        self.export_browse_button = QPushButton("选择导出目录")
        self.export_browse_button.clicked.connect(self.browse_export_directory)
        export_buttons_layout.addWidget(self.export_browse_button)
        
        export_layout.addLayout(export_buttons_layout)
        
        layout.addWidget(export_group)
        
        # 最近导出文件组
        recent_group = QGroupBox("最近导出的文件")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_files_text = QTextEdit()
        self.recent_files_text.setReadOnly(True)
        self.recent_files_text.setMaximumHeight(150)
        recent_layout.addWidget(self.recent_files_text)
        
        refresh_recent_button = QPushButton("刷新最近文件列表")
        refresh_recent_button.clicked.connect(self.refresh_recent_files)
        recent_layout.addWidget(refresh_recent_button)
        
        layout.addWidget(recent_group)
        
        # 状态显示
        self.file_status_label = QLabel("就绪")
        self.file_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_status_label)
        
        # 初始化显示最近文件
        self.refresh_recent_files()
        
        return widget
        
    def create_network_transfer_tab(self):
        """创建网络传输标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 二维码生成区域（放在最顶部）
        qr_group = QGroupBox("📱 二维码传输")
        qr_layout = QVBoxLayout(qr_group)
        
        # 生成二维码按钮
        self.generate_network_qr_button = QPushButton("生成网络传输二维码")
        self.generate_network_qr_button.clicked.connect(self.generate_network_qr)
        qr_layout.addWidget(self.generate_network_qr_button)
        
        # 二维码显示区域
        self.network_qr_label = QLabel()
        self.network_qr_label.setAlignment(Qt.AlignCenter)
        self.network_qr_label.setMinimumHeight(200)
        self.network_qr_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        qr_layout.addWidget(self.network_qr_label)
        
        layout.addWidget(qr_group)
        
        # 服务器控制组
        server_group = QGroupBox("服务器控制")
        server_layout = QFormLayout(server_group)
        
        # 服务器状态显示
        self.server_status_label = QLabel("服务器状态: 未启动")
        server_layout.addRow(self.server_status_label)
        
        # 服务器地址显示
        self.server_address_label = QLabel("访问地址: ")
        server_layout.addRow(self.server_address_label)
        
        # 控制按钮
        server_buttons_layout = QHBoxLayout()
        
        self.start_server_button = QPushButton("启动服务器")
        self.start_server_button.clicked.connect(self.start_network_server)
        server_buttons_layout.addWidget(self.start_server_button)
        
        self.stop_server_button = QPushButton("停止服务器")
        self.stop_server_button.clicked.connect(self.stop_network_server)
        self.stop_server_button.setEnabled(False)
        server_buttons_layout.addWidget(self.stop_server_button)
        
        server_layout.addRow(server_buttons_layout)
        
        layout.addWidget(server_group)
        
        # API端点信息
        api_group = QGroupBox("API端点信息")
        api_layout = QVBoxLayout(api_group)
        
        self.api_info_text = QTextEdit()
        self.api_info_text.setReadOnly(True)
        self.api_info_text.setMaximumHeight(120)
        api_layout.addWidget(self.api_info_text)
        
        layout.addWidget(api_group)
        
        # 状态显示
        self.network_status_label = QLabel("就绪")
        self.network_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.network_status_label)
        
        return widget
        
    def create_summary_tab(self):
        """创建数据摘要标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据摘要显示
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        layout.addWidget(self.summary_text)
        
        # 刷新按钮
        refresh_summary_button = QPushButton("刷新数据摘要")
        refresh_summary_button.clicked.connect(self.refresh_summary)
        layout.addWidget(refresh_summary_button)
        
        # 状态显示
        self.summary_status_label = QLabel("就绪")
        self.summary_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.summary_status_label)
        
        # 初始化显示摘要
        self.refresh_summary()
        
        return widget
        
    def handle_export(self):
        """处理文件导出（仅完整数据）"""
        try:
            # 固定导出完整数据
            export_type = "full"
            
            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存完整数据文件",
                f"capture_push_complete_{Path.cwd().name}.json",
                "JSON文件 (*.json)"
            )
            
            if file_path:
                self.file_status_label.setText("正在导出...")
                self.export_button.setEnabled(False)
                
                # 执行导出
                # 直接调用export_full_data以使用用户选择的文件路径
                result = export_full_data(file_path)
                
                if result.get("status") == "success":
                    QMessageBox.information(
                        self,
                        "导出成功",
                        f"数据已成功导出到:\n{result.get('file_path')}"
                    )
                    self.file_status_label.setText("导出完成")
                    self.refresh_recent_files()
                else:
                    QMessageBox.critical(
                        self,
                        "导出失败",
                        f"导出失败: {result.get('message', '未知错误')}"
                    )
                    self.file_status_label.setText("导出失败")
                
                self.export_button.setEnabled(True)
                
        except Exception as e:
            logger.error(f"文件导出出错: {e}")
            QMessageBox.critical(self, "错误", f"导出过程中发生错误: {str(e)}")
            self.file_status_label.setText("导出出错")
            self.export_button.setEnabled(True)
            
    def browse_export_directory(self):
        """浏览导出目录"""
        try:
            directory = get_export_directory()
            QFileDialog.getExistingDirectory(self, "选择导出目录", directory)
        except Exception as e:
            logger.error(f"打开目录选择对话框失败: {e}")
            
    def refresh_recent_files(self):
        """刷新最近导出文件列表"""
        try:
            recent_files = get_recent_exports(10)
            if recent_files:
                text = "最近导出的文件:\n\n"
                for file_info in recent_files:
                    text += f"• {file_info.get('filename', 'Unknown')}\n"
                    text += f"  修改时间: {file_info.get('modified_time', 'Unknown')}\n"
                    text += f"  文件大小: {file_info.get('size', 0)} 字节\n\n"
            else:
                text = "暂无导出文件记录"
                
            self.recent_files_text.setText(text)
        except Exception as e:
            logger.error(f"刷新最近文件列表失败: {e}")
            self.recent_files_text.setText("加载文件列表失败")
            
    def start_network_server(self):
        """启动网络服务器"""
        try:
            self.network_status_label.setText("正在启动服务器...")
            self.start_server_button.setEnabled(False)
            
            # 启动服务器线程
            self.server_thread = NetworkServerThread()
            self.server_thread.status_changed.connect(self.update_server_status)
            self.server_thread.start()
            
            # 更新UI状态
            self.stop_server_button.setEnabled(True)
            self.network_status_label.setText("服务器启动中...")
            
        except Exception as e:
            logger.error(f"启动网络服务器失败: {e}")
            QMessageBox.critical(self, "错误", f"启动服务器失败: {str(e)}")
            self.start_server_button.setEnabled(True)
            self.network_status_label.setText("启动失败")
            
    def stop_network_server(self):
        """停止网络服务器"""
        try:
            if self.server_thread and self.server_thread.isRunning():
                self.server_thread.stop()
                self.server_thread.wait()
                self.server_thread = None
                
            # 更新UI状态
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(False)
            self.server_status_label.setText("服务器状态: 未启动")
            self.server_address_label.setText("访问地址: ")
            self.api_info_text.clear()
            self.network_qr_label.clear()
            self.network_status_label.setText("服务器已停止")
            
        except Exception as e:
            logger.error(f"停止网络服务器失败: {e}")
            
    def update_server_status(self, status):
        """更新服务器状态显示"""
        try:
            if status.get("running", False):
                self.server_status_label.setText("服务器状态: 运行中")
                local_ip = status.get("local_ip", "localhost")
                port = status.get("port", 8080)
                self.server_address_label.setText(f"访问地址: http://{local_ip}:{port}")
                
                # 显示API端点
                api_text = "可用的API端点:\n\n"
                for endpoint in status.get("api_endpoints", []):
                    api_text += f"• {endpoint}\n"
                self.api_info_text.setText(api_text)
            else:
                self.server_status_label.setText("服务器状态: 已停止")
                self.server_address_label.setText("访问地址: ")
                self.api_info_text.clear()
                
        except Exception as e:
            logger.error(f"更新服务器状态显示失败: {e}")
            
    def generate_network_qr(self):
        """生成网络传输二维码"""
        try:
            if not QR_CODE_AVAILABLE:
                QMessageBox.warning(self, "警告", "二维码功能需要安装qrcode库\n请运行: pip install qrcode[pil]")
                return
                
            self.network_status_label.setText("正在生成二维码...")
            
            # 生成二维码并自动启动服务器
            result = generate_network_qr_code(auto_start_server=True)
            
            if result.get("status") == "success":
                # 显示二维码
                qr_image_data = base64.b64decode(result["qr_image"])
                pixmap = QPixmap()
                pixmap.loadFromData(qr_image_data)
                
                # 缩放图片以适应显示区域
                scaled_pixmap = pixmap.scaled(
                    self.network_qr_label.width() - 20,
                    self.network_qr_label.height() - 20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                self.network_qr_label.setPixmap(scaled_pixmap)
                self.network_status_label.setText("二维码生成完成")
            else:
                QMessageBox.critical(
                    self,
                    "生成失败",
                    f"生成二维码失败: {result.get('message', '未知错误')}"
                )
                self.network_status_label.setText("二维码生成失败")
                
        except Exception as e:
            logger.error(f"生成网络二维码失败: {e}")
            QMessageBox.critical(self, "错误", f"生成二维码时发生错误: {str(e)}")
            self.network_status_label.setText("生成出错")
            
# 直接数据二维码功能已移除（根据用户要求）
            
    def refresh_summary(self):
        """刷新数据摘要"""
        try:
            self.summary_status_label.setText("正在加载数据摘要...")
            
            summary = get_export_summary()
            
            if "error" in summary:
                self.summary_text.setText(f"加载失败: {summary['error']}")
                self.summary_status_label.setText("加载失败")
            else:
                # 格式化显示摘要信息
                text = "数据摘要信息:\n\n"
                text += f"院校代码: {summary.get('school_code', 'Unknown')}\n"
                text += f"课表课程数: {summary.get('schedule_courses', 0)}\n"
                text += f"课表周数: {summary.get('schedule_weeks', 0)}\n"
                text += f"最后导出时间: {summary.get('last_export', 'Unknown')}\n"
                
                self.summary_text.setText(text)
                self.summary_status_label.setText("数据加载完成")
                
        except Exception as e:
            logger.error(f"刷新数据摘要失败: {e}")
            self.summary_text.setText("加载数据摘要失败")
            self.summary_status_label.setText("加载失败")
            
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止服务器线程
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            self.server_thread.wait()
        event.accept()