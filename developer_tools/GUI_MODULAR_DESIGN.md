# GUI 模块化设计说明

## 设计理念

Capture_Push 采用现代化的模块化GUI架构，基于标签页的设计模式，提供清晰的功能组织和良好的用户体验。

### 模块划分原则
- **功能独立**：每个模块负责单一功能领域
- **职责分离**：UI 层、业务逻辑层、数据访问层分离
- **易于复用**：组件可在不同窗口间共享
- **标签页组织**：主要功能通过标签页进行组织管理
- **响应式设计**：界面适应不同屏幕尺寸和分辨率

### 模块结构

#### [gui/gui.py]
- **职责**：应用入口点
- **功能**：初始化 Qt 应用并启动主窗口
- **特点**：最轻量，只包含启动逻辑

#### [gui/config_window.py]
- **职责**：主配置窗口容器
- **功能**：作为标签页容器，管理各个功能标签页
- **特点**：协调各标签页间的数据传递和状态同步

#### [gui/tabs/] 目录
包含所有功能标签页模块：

##### [gui/tabs/home_tab.py]
- **职责**：主页标签页
- **功能**：显示系统状态、快捷操作按钮、最近活动
- **特点**：用户进入应用后的首个界面

##### [gui/tabs/basic_tab.py]
- **职责**：基础设置标签页
- **功能**：账户配置、基本参数设置
- **特点**：包含院校选择、登录凭证等核心配置

##### [gui/tabs/push_tab.py]
- **职责**：推送设置标签页
- **功能**：配置各种推送方式（邮件、飞书、Server酱等）
- **特点**：支持多种推送渠道的统一管理

##### [gui/tabs/school_time_tab.py]
- **职责**：学校时间设置标签页
- **功能**：配置学校作息时间、学期信息
- **特点**：支持个性化的时间安排设置

##### [gui/tabs/software_settings_tab.py]
- **职责**：软件设置标签页
- **功能**：高级配置、性能优化、日志设置
- **特点**：面向高级用户的系统级配置

##### [gui/tabs/plugin_management_tab.py]
- **职责**：插件管理标签页
- **功能**：插件的安装、更新、卸载和管理
- **特点**：集成的插件生态系统管理界面

##### [gui/tabs/about_tab.py]
- **职责**：关于标签页
- **功能**：版本信息、配置导出、系统信息
- **特点**：提供系统维护和诊断功能

**示例代码片段**：
```python
# 标签页基类示例
class BaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置UI布局，由子类实现"""
        raise NotImplementedError
    
    def load_config(self):
        """加载配置，由子类实现"""
        pass
    
    def save_config(self):
        """保存配置，由子类实现"""
        pass

# 具体标签页实现示例
class BasicSettingsTab(BaseTab):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 院校选择
        school_layout = QHBoxLayout()
        school_layout.addWidget(QLabel("选择院校:"))
        self.school_combo = QComboBox()
        self.school_combo.addItems(["请选择院校", "衡阳师范学院"])
        school_layout.addWidget(self.school_combo)
        layout.addLayout(school_layout)
        
        # 账户配置
        account_group = QGroupBox("账户配置")
        account_layout = QFormLayout(account_group)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        account_layout.addRow("用户名:", self.username_input)
        account_layout.addRow("密码:", self.password_input)
        layout.addWidget(account_group)
    
    def load_config(self):
        config = self.config_manager.load_config()
        self.username_input.setText(config.get("account", "username", fallback=""))
        self.password_input.setText(config.get("account", "password", fallback=""))
        
        # 设置院校选择
        school_code = config.get("account", "school_code", fallback="")
        index = self.school_combo.findData(school_code)
        if index >= 0:
            self.school_combo.setCurrentIndex(index)
    
    def save_config(self):
        config = self.config_manager.load_config()
        
        # 保存账户信息
        if "account" not in config:
            config["account"] = {}
        config["account"]["username"] = self.username_input.text()
        config["account"]["password"] = self.password_input.text()
        
        # 保存院校选择
        school_code = self.school_combo.currentData()
        if school_code:
            config["account"]["school_code"] = school_code
        
        self.config_manager.save_config(config)
```

#### [gui/grades_window.py]
- **职责**：成绩查看窗口
- **功能**：成绩表格展示、网络刷新、缓存清除
- **特点**：独立于其他窗口，专注于成绩数据

#### [gui/schedule_window.py]
- **职责**：课表查看窗口
- **功能**：课表色块渲染、周次切换、手动编辑
- **特点**：复杂交互逻辑，支持双击编辑

#### [gui/dialogs.py]
- **职责**：对话框组件
- **功能**：课程编辑对话框等弹窗
- **特点**：可被多个窗口复用

#### [gui/widgets.py]
- **职责**：自定义 UI 组件
- **功能**：课程色块等可视化元素
- **特点**：纯粹的 UI 组件，不含逻辑

## 维护指南

### 添加新功能

#### 1. 添加新的标签页
1. 在 `gui/tabs/` 目录下创建新的标签页模块
2. 继承 `BaseTab` 基类实现标准接口
3. 在 `config_window.py` 中注册新的标签页
4. 更新配置管理逻辑

#### 2. 添加新的对话框
1. 在 `gui/dialogs.py` 中添加新的对话框类
2. 或创建独立的对话框模块文件
3. 确保对话框支持配置的加载和保存

#### 3. 添加新的UI组件
1. 在 `gui/widgets/` 目录下创建自定义组件
2. 或添加到现有的 `custom_widgets.py` 文件
3. 确保组件具有良好的复用性和可配置性

#### 4. 添加新的配置项
1. 在相应的标签页模块中添加UI控件
2. 更新配置加载和保存逻辑
3. 在 `config.md` 中添加配置项说明

### 修改现有功能

#### UI变更
1. **局部修改**：在对应标签页模块中修改，不影响其他模块
2. **全局样式**：修改样式表或主题配置文件
3. **布局调整**：使用Qt的布局管理器确保响应式设计

#### 业务逻辑变更
1. **功能增强**：在对应模块中扩展功能逻辑
2. **性能优化**：优化数据处理和UI渲染逻辑
3. **错误处理**：完善异常处理和用户反馈机制

#### 跨模块交互
1. **信号槽机制**：使用Qt的信号槽进行模块间通信
2. **配置管理器**：通过统一的配置管理器共享数据
3. **事件总线**：对于复杂的跨模块通信，考虑实现事件总线模式

## 配置导出功能

### 导出明文配置
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **验证**：需要用户提供教务系统登录密码进行身份验证
- **实现**：使用 `core.config_manager.load_config()` 加载加密配置，然后保存为明文文件
- **安全**：导出的明文配置文件应有明确的安全提示


### 清除配置
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **确认**：需要二次确认以防止误操作
- **实现**：删除配置文件并提示用户重启程序

### 调整日志级别和运行模式
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **功能**：允许用户调整 [logging] 和 [run_model] 配置
- **实现**：通过对话框让用户选择新值并保存

**示例代码**：
```python
def adjust_logging_and_run_model(self):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
    
    dialog = QDialog(self)
    dialog.setWindowTitle("调整日志级别和运行模式")
    
    layout = QVBoxLayout(dialog)
    
    # 日志级别选择
    log_layout = QHBoxLayout()
    log_layout.addWidget(QLabel("日志级别:"))
    log_combo = QComboBox()
    log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    log_combo.setCurrentText(self.cfg.get("logging", "level", fallback="INFO"))
    log_layout.addWidget(log_combo)
    layout.addLayout(log_layout)
    
    # 运行模式选择
    run_layout = QHBoxLayout()
    run_layout.addWidget(QLabel("运行模式:"))
    run_combo = QComboBox()
    run_combo.addItems(["DEV", "BUILD"])
    run_combo.setCurrentText(self.cfg.get("run_model", "model", fallback="BUILD"))
    run_layout.addWidget(run_combo)
    layout.addLayout(run_layout)
    
    # 按钮
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    
    if dialog.exec() == QDialog.Accepted:
        # 更新配置
        self.cfg["logging"]["level"] = log_combo.currentText()
        self.cfg["run_model"]["model"] = run_combo.currentText()
        
        # 保存配置
        from core.config_manager import save_config
        save_config(self.cfg)
        QMessageBox.information(self, "修改成功", "配置已更新")
```
