import sys
import json
import subprocess
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QHBoxLayout, QPushButton, QMessageBox, 
    QApplication, QLabel, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# 定义项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 导入日志模块和配置管理
try:
    from log import get_config_path, get_log_file_path, get_logger
    from config_manager import load_config
    logger = get_logger('schedule_window')
except ImportError:
    from core.log import get_config_path, get_log_file_path, get_logger
    from core.config_manager import load_config
    logger = get_logger('schedule_window')

# 使用插件管理器获取学校模块
try:
    from core.plugins.plugin_manager import PluginManager
    plugin_manager = PluginManager()
except ImportError:
    plugin_manager = None

# 导入自定义组件和对话框
try:
    from custom_widgets import CourseBlock
    from dialogs import CourseEditDialog
except ImportError:
    from gui.custom_widgets import CourseBlock
    from gui.dialogs import CourseEditDialog

# 导入线性化模块
try:
    from core.schedule_linearizer import load_linear_schedule
    LINEARIZER_AVAILABLE = True
except ImportError:
    LINEARIZER_AVAILABLE = False
    load_linear_schedule = None

CONFIG_FILE = str(get_config_path())
APPDATA_DIR = get_log_file_path('gui').parent
MANUAL_SCHEDULE_FILE = APPDATA_DIR / "manual_schedule.json"
# 修正线性化JSON文件路径
LINEAR_SCHEDULE_FILE = Path.home() / "AppData" / "Local" / "Capture_Push" / "linear_schedule.json"

def get_current_school_code():
    """从配置文件中获取当前院校代码"""
    cfg = load_config()
    return cfg.get("account", "school_code", fallback="10546")

def get_school_module(school_code):
    """通过插件管理器获取学校模块"""
    if plugin_manager:
        return plugin_manager.load_plugin(school_code)
    return None

class ScheduleViewerWindow(QWidget):
    """独立窗口：查看课表（色块展示版，支持周次切换）"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 课表查看")
        self.resize(1100, 850)
        
        # 预设更柔和的浅色列表，适合黑色文字
        self.colors = [
            "#FFD1D1", "#FFDFD1", "#FFF0D1", "#E6FAD1", 
            "#D1FAE5", "#D1F2FA", "#D1D5FA", "#E9D1FA",
            "#FAD1F5", "#FAD1D1", "#F5F5F5", "#EEEEEE"
        ]
        self.course_colors = {}
        
        # 加载配置
        self.cfg = load_config()
        self.first_monday_str = self.cfg.get("semester", "first_monday", fallback="")
        
        # 加载学校时间设置
        self.morning_count = self.cfg.getint("school_time", "morning_count", fallback=4)
        self.afternoon_count = self.cfg.getint("school_time", "afternoon_count", fallback=4)
        self.evening_count = self.cfg.getint("school_time", "evening_count", fallback=2)
        self.total_classes = self.morning_count + self.afternoon_count + self.evening_count
        
        class_times_str = self.cfg.get("school_time", "class_times", fallback="")
        self.class_times = []
        if class_times_str:
            self.class_times = [t.strip() for t in class_times_str.split(",")]
        # 补齐
        while len(self.class_times) < self.total_classes:
            self.class_times.append("")
        
        self.current_week = self.calculate_current_week()
        self.selected_week = self.current_week
        
        self.init_ui()

    def calculate_current_week(self):
        """根据第一周周一反推当前是第几周"""
        if not self.first_monday_str:
            return 1
        try:
            import datetime
            first_monday = datetime.datetime.strptime(self.first_monday_str, "%Y-%m-%d").date()
            today = datetime.date.today()
            delta = (today - first_monday).days
            if delta < 0: return 1
            week = (delta // 7) + 1
            return min(max(week, 1), 20) # 限制在 1-20 周
        except:
            return 1

    def get_color(self, course_name):
        """为课程名分配固定颜色"""
        if course_name not in self.course_colors:
            color_idx = len(self.course_colors) % len(self.colors)
            self.course_colors[course_name] = self.colors[color_idx]
        return self.course_colors[course_name]

    def adjust_color_brightness(self, hex_color, factor):
        """调整颜色亮度，factor为正数变亮，负数变暗"""
        # 移除 # 符号
        hex_color = hex_color.lstrip('#')
        # 解析RGB值
        try:
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # 调整每个颜色通道
            adjusted_rgb = []
            for val in rgb:
                new_val = val + factor
                # 确保值在0-255范围内
                new_val = max(0, min(255, new_val))
                adjusted_rgb.append(new_val)
            
            # 转换回十六进制
            return '#{0:02x}{1:02x}{2:02x}'.format(*adjusted_rgb)
        except:
            # 如果转换失败，返回原始颜色
            return hex_color

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部控制栏
        top_ctrl = QHBoxLayout()
        
        # 周次切换
        top_ctrl.addWidget(QLabel("当前显示："))
        self.week_combo = QSpinBox()
        self.week_combo.setRange(0, 25) # 包含第0周
        self.week_combo.setSpecialValueText("第 0 周 (全部)")
        self.week_combo.setValue(self.selected_week)
        self.week_combo.setPrefix("第 ")
        self.week_combo.setSuffix(" 周")
        self.week_combo.valueChanged.connect(self.on_week_changed)
        top_ctrl.addWidget(self.week_combo)
        
        self.this_week_label = QLabel("")
        self.this_week_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        top_ctrl.addWidget(self.this_week_label)
        self.update_this_week_label()
            
        top_ctrl.addStretch()
        self.tip_label = QLabel("提示：双击单元格进行手动编辑")
        top_ctrl.addWidget(self.tip_label)
        layout.addLayout(top_ctrl)

        self.table = QTableWidget()
        self.table.setColumnCount(8) # 1列节次 + 7列星期
        self.table.setRowCount(self.total_classes)
        
        days = ["时间/节次", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.table.setHorizontalHeaderLabels(days)
        
        # 设置表头样式
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100) # 加宽时间列
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False) # 隐藏网格线
        
        # 绑定双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        # 初始化节次列 (现在包含时间)
        self.update_time_column()

        layout.addWidget(self.table)
        
        # 底部按钮区（添加刷新和清除）
        bottom_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新课表 (从网络获取)")
        refresh_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        refresh_btn.clicked.connect(self.refresh_data)
        
        clear_btn = QPushButton("清除课表数据 (含手动修改)")
        clear_btn.setStyleSheet("color: #d83b01; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_schedule_cache)
        
        bottom_layout.addWidget(refresh_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(clear_btn)
        layout.addLayout(bottom_layout)

        self.load_data()

    def on_week_changed(self, value):
        self.selected_week = value
        self.update_this_week_label()
        
        # 更新提示信息
        if value == 0:
            self.tip_label.setText("提示：第0周展示本学期所有课程，相同时间段的课程将聚合显示")
            self.tip_label.setStyleSheet("color: #d83b01; font-weight: bold;")
        else:
            self.tip_label.setText("提示：双击单元格进行手动编辑")
            self.tip_label.setStyleSheet("")
            
        self.load_data()

    def update_this_week_label(self):
        """更新本周标识标签"""
        if self.selected_week == 0:
            self.this_week_label.setText(f"(本周是第 {self.current_week} 周)")
            return

        if self.selected_week == self.current_week:
            self.this_week_label.setText("(本周)")
        else:
            self.this_week_label.setText(f"(本周是第 {self.current_week} 周)")

    def update_time_column(self):
        for i in range(self.total_classes):
            time_str = self.class_times[i] if i < len(self.class_times) else ""
            text = f"{time_str}\n(第 {i+1} 节)"
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#f8f9fa"))
            self.table.setItem(i, 0, item)
            self.table.setRowHeight(i, 75)

    def on_cell_double_clicked(self, row, col):
        """双击单元格打开编辑对话框"""
        if col == 0:
            # 编辑时间
            from PySide6.QtWidgets import QInputDialog
            current_time = self.class_times[row] if row < len(self.class_times) else ""
            new_time, ok = QInputDialog.getText(self, "修改时间", f"请输入第 {row+1} 节课的开始时间:", text=current_time)
            if ok:
                if row < len(self.class_times):
                    self.class_times[row] = new_time
                else:
                    while len(self.class_times) <= row:
                        self.class_times.append("")
                    self.class_times[row] = new_time
                
                # 保存到配置
                if "school_time" not in self.cfg: self.cfg["school_time"] = {}
                self.cfg["school_time"]["class_times"] = ",".join(self.class_times)
                try:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        self.cfg.write(f)
                except:
                    pass
                
                self.update_time_column()
            return
        
        # 尝试获取当前格子已有的数据
        existing_data = {}
        # 检查是否是手动修改过的格子
        manual_key = f"{col}-{row+1}"
        manual_data = self.load_manual_schedule()
        if manual_key in manual_data:
            existing_data = manual_data[manual_key]
        else:
            # 如果没有手动修改过，现在只使用线性化JSON数据
            # 不再从HTML文件中查找自动解析的课程数据
            existing_data = {}
        
        self.current_editing_pos = (row, col)
        self.edit_dialog = CourseEditDialog(self, existing_data)
        self.edit_dialog.show()
        
    def format_weeks_list(self, weeks_list):
        """将周次列表格式化为字符串"""
        if not weeks_list or "全学期" in weeks_list:
            return "1-20"
        
        if not weeks_list:
            return "1-20"
            
        # 尝试将连续数字合并为范围，如 [1,2,3,5,7,8,9] -> "1-3,5,7-9"
        if len(weeks_list) == 1:
            return str(weeks_list[0])
        
        # 排序
        weeks_list = sorted(set(weeks_list))
        
        result = []
        i = 0
        while i < len(weeks_list):
            start = weeks_list[i]
            end = start
            
            # 查找连续序列
            while i + 1 < len(weeks_list) and weeks_list[i + 1] == end + 1:
                end = weeks_list[i + 1]
                i += 1
            
            if start == end:
                result.append(str(start))
            else:
                result.append(f"{start}-{end}")
            
            i += 1
        
        return ','.join(result)

    def on_dialog_finished(self, result):
        """对话框保存后的回调"""
        row, col = self.current_editing_pos
        manual_key = f"{col}-{row+1}" # 星期-开始小节
        
        manual_data = self.load_manual_schedule()
        if not result.get("课程名称"):
            # 如果名称为空，视为删除该位置的手动修改
            if manual_key in manual_data:
                del manual_data[manual_key]
        else:
            manual_data[manual_key] = result
            
        self.save_manual_schedule(manual_data)
        self.load_data() # 重新渲染

    def load_manual_schedule(self):
        """加载手动修改的课表数据"""
        if not MANUAL_SCHEDULE_FILE.exists():
            return {}
        try:
            with open(MANUAL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_manual_schedule(self, data):
        """保存手动修改的课表数据"""
        try:
            with open(MANUAL_SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存手动修改：{e}")

    def clear_schedule_cache(self):
        """清除课表缓存"""
        reply = QMessageBox.question(self, "确认清除", "确定要清除所有课表缓存（包括手动修改的数据）吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 只清除线性化JSON文件和手动修改数据
                if LINEAR_SCHEDULE_FILE.exists(): LINEAR_SCHEDULE_FILE.unlink()
                if MANUAL_SCHEDULE_FILE.exists(): MANUAL_SCHEDULE_FILE.unlink()
                QMessageBox.information(self, "成功", "课表数据已清除。")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "失败", f"清除失败：{e}")

    def refresh_data(self):
        """手动触发网络刷新"""
        # 禁用按钮防止重复点击
        sender = self.sender()
        if sender: sender.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "pythonw.exe").exists():
                py_exe = str(exe_dir / "pythonw.exe")
            else:
                py_exe = sys.executable
                
            go_script = str(BASE_DIR / "core" / "go.py")
            
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([py_exe, go_script, "--fetch-schedule", "--force"], 
                            creationflags=CREATE_NO_WINDOW).wait()
            
            # 刷新完成后重新加载数据（包括线性化JSON）
            self.load_data()
            QMessageBox.information(self, "刷新完成", "课表数据已从网络同步并更新线性化JSON文件。")
        except Exception as e:
            QMessageBox.critical(self, "刷新失败", f"无法执行刷新脚本：{e}")
        finally:
            QApplication.restoreOverrideCursor()
            if sender: sender.setEnabled(True)

    def merge_consecutive_courses(self, schedule):
        """智能合并同一课程的连续时段
        
        Args:
            schedule: 解析出来的课表数据列表
            
        Returns:
            合并后的课表数据列表
        
        注意：
        1. 按完整课程标识分组（星期+课程名称+教师+教室+周次列表）
        2. 只对同一周次内的连续课程进行合并
        3. 不同周次的课程保持独立，避免错误合并
        """
        if not schedule:
            return schedule
            
        # 按完整标识分组（包含周次信息）
        course_groups = {}
        
        for course in schedule:
            # 创建完整分组键：星期+课程名称+教师+教室+周次列表
            weeks_list = sorted(course.get("周次列表", []))
            weeks_key = str(weeks_list) if weeks_list else "[]"
            
            key = (
                course.get("星期", 0),
                course.get("课程名称", ""),
                course.get("教师", ""),
                course.get("教室", ""),
                weeks_key  # 关键：包含周次信息防止跨周次合并
            )
            
            if key not in course_groups:
                course_groups[key] = []
            course_groups[key].append(course)
        
        # 对每个分组内的课程进行连续合并
        merged_schedule = []
        
        for group_key, courses in course_groups.items():
            # 按开始节次排序
            courses.sort(key=lambda x: x.get("开始小节", 0))
            
            # 连续合并算法
            i = 0
            while i < len(courses):
                current_course = courses[i]
                start_period = current_course.get("开始小节", 0)
                end_period = current_course.get("结束小节", 0)
                
                # 查找可以合并的连续课程
                j = i + 1
                while j < len(courses):
                    next_course = courses[j]
                    # 如果下一课程紧接当前课程（开始节次 = 当前结束节次 + 1）
                    if next_course.get("开始小节", 0) == end_period + 1:
                        end_period = next_course.get("结束小节", 0)
                        j += 1
                    else:
                        break
                
                # 创建合并后的课程记录
                merged_course = {
                    "星期": current_course.get("星期", 0),
                    "开始小节": start_period,
                    "结束小节": end_period,
                    "课程名称": current_course.get("课程名称", ""),
                    "教师": current_course.get("教师", ""),
                    "教室": current_course.get("教室", ""),
                    "周次列表": current_course.get("周次列表", [])
                }
                merged_schedule.append(merged_course)
                
                # 跳过已合并的课程
                i = j
        
        return merged_schedule
    

    
    def force_parse_schedule(self):
        """强制解析课表并生成线性化JSON文件"""
        try:
            logger.info("开始强制解析课表...")
            
            # 获取账户信息
            cfg = load_config()
            username = cfg.get("account", "username", fallback="")
            password = cfg.get("account", "password", fallback="")
            
            if not username or not password:
                QMessageBox.warning(self, "警告", "请先在基本设置中配置学号和密码！")
                return False
            
            # 获取学校模块
            school_code = get_current_school_code()
            school_mod = get_school_module(school_code)
            
            if not school_mod:
                QMessageBox.warning(self, "警告", f"找不到院校模块: {school_code}")
                return False
            
            # 检查是否有所需的方法
            if not hasattr(school_mod, 'fetch_course_schedule'):
                QMessageBox.warning(self, "警告", f"院校模块 {school_code} 缺少 fetch_course_schedule 方法")
                return False
            
            # 调用插件获取课表数据
            schedule_data = school_mod.fetch_course_schedule(username, password, force_update=True)
            
            if not schedule_data:
                QMessageBox.warning(self, "警告", "未能获取到课表数据，请检查网络连接和账号信息！")
                return False
            
            logger.info(f"成功获取课表数据，共 {len(schedule_data)} 条记录")
            
            # 线性化处理
            from core.schedule_linearizer import linearize_schedule, save_linear_schedule
            
            # 获取学期开始日期（可选）
            first_monday = cfg.get("semester", "first_monday", fallback=None)
            if first_monday:
                linear_data = linearize_schedule(schedule_data, first_monday)
            else:
                linear_data = linearize_schedule(schedule_data)
            
            # 保存线性化数据
            save_path = save_linear_schedule(linear_data, "linear_schedule.json")
            logger.info(f"线性化课表已保存到: {save_path}")
            
            QMessageBox.information(self, "成功", f"课表解析完成！\n共处理 {len(schedule_data)} 条课程记录\n线性化数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"强制解析课表失败: {e}")
            QMessageBox.critical(self, "错误", f"课表解析失败：{str(e)}")
            return False
    
    def render_schedule(self, schedule_data, manual_data):
        """渲染课表数据"""
        # 准备合并：记录已占用的单元格，手动修改优先
        occupied = set()

        # 先处理手动修改
        for key, data in manual_data.items():
            col, start = map(int, key.split("-"))
            row = start - 1
            row_span = data.get("row_span", 1)
            
            # 检查周次是否包含在内
            weeks_list = data.get("周次列表", [])
            if self.selected_week != 0 and weeks_list and self.selected_week not in weeks_list:
                continue

            name = data.get("课程名称", "")
            room = data.get("教室", "")
            teacher = data.get("教师", "")
            
            if 0 < col <= 7 and 0 < row < self.total_classes:
                color = self.get_color(name)
                # 标记手动修改，使用不同颜色区分
                modified_color = self.adjust_color_brightness(color, -20)  # 稍微加深颜色表示手动修改
                block = CourseBlock(name, room, teacher, modified_color, is_manual=True)
                
                actual_span = min(row_span, self.total_classes - row)
                # 确保span是正整数且大于1
                if isinstance(actual_span, int) and actual_span > 1:
                    self.table.setSpan(row, col, actual_span, 1)
                self.table.setCellWidget(row, col, block)
                
                for r in range(row, row + actual_span):
                    occupied.add((r, col))

        # 处理课表数据（可能是线性化的或传统的）
        
        # 第0周特殊处理：按（星期，开始小节）分组进行合并显示
        if self.selected_week == 0:
            # 使用字典按 (星期, 开始小节) 聚合课程
            merged_cells = {}
            
            for s in schedule_data:
                day_idx = s.get("星期", 0)
                start = s.get("开始小节", 0)
                end = s.get("结束小节", 0)
                
                if 0 < day_idx <= 7 and 0 < start <= self.total_classes:
                    key = (day_idx, start)
                    if key not in merged_cells:
                        merged_cells[key] = []
                    merged_cells[key].append(s)

            # 遍历聚合后的课程组进行渲染
            for (day_idx, start), courses in merged_cells.items():
                row = start - 1
                col = day_idx
                
                # 计算该时间段所有课程的最大结束节次，作为合并行数
                max_end = start
                for s in courses:
                    max_end = max(max_end, s.get("结束小节", start))
                
                effective_end = min(max_end, self.total_classes)
                row_span = effective_end - start + 1
                
                # 构建单元格显示文本
                # 格式：[周次] 课程名 @教室 教师
                display_texts = []
                first_course_name = courses[0].get("课程名称", "")
                
                for s in courses:
                    name = s.get("课程名称", "")
                    room = s.get("教室", "")
                    teacher = s.get("教师", "")
                    weeks_list = s.get("周次列表", [])
                    weeks_str = self.format_weeks_list(weeks_list)
                    
                    # 组合单门课程信息
                    course_info = f"[{weeks_str}周] {name}"
                    details = []
                    if room: details.append(f"@{room}")
                    if teacher: details.append(f"{teacher}")
                    if details:
                        course_info += "\n" + " ".join(details)
                    
                    display_texts.append(course_info)
                
                # 多门课程之间用空行分隔
                final_text = "\n\n".join(display_texts)
                
                # 检查是否被手动修改占用（手动修改优先级最高）
                if (row, col) in occupied:
                    continue
                
                # 检查合并区域是否被占用
                can_place = True
                for r in range(row, row + row_span):
                    if (r, col) in occupied:
                        can_place = False
                        break
                
                if can_place:
                    # 使用第一门课的颜色作为背景色
                    color = self.get_color(first_course_name)
                    
                    # 将合并后的文本直接作为 name 传入，其他字段置空
                    # CourseBlock 会自动处理换行
                    block = CourseBlock(final_text, "", "", color, is_manual=False, is_week_zero=True)
                    
                    # 设置合并单元格
                    if isinstance(row_span, int) and row_span > 1:
                        self.table.setSpan(row, col, row_span, 1)
                        
                    self.table.setCellWidget(row, col, block)
                    
                    # 标记占用
                    for r in range(row, row + row_span):
                        occupied.add((r, col))
            
            return # 第0周渲染结束，跳过后续常规渲染逻辑

        for i, s in enumerate(schedule_data):
            # 验证每个课表条目必须是字典
            if not isinstance(s, dict):
                logger.warning(f"课表列表中第{i+1}项应为字典，实际类型: {type(s).__name__}")
                continue
                
            day_idx = s.get("星期", 0)
            start = s.get("开始小节", 0)
            end = s.get("结束小节", 0)
            
            # 对于线性化数据，所有课程都应该显示在当前周次
            # 对于传统数据，需要检查周次
            weeks_list = s.get("周次列表", [])
            if self.selected_week != 0 and weeks_list and "全学期" not in weeks_list and self.selected_week not in weeks_list:
                continue
            
            if 0 < day_idx <= 7 and 0 < start <= self.total_classes:
                row = start - 1
                col = day_idx
                
                # 🔍 调试日志：追踪特定课程的渲染
                if day_idx == 3 and start == 3 and end == 4:  # 周三3-4节
                    logger.info(f"🔍 调试图标课程渲染:")
                    logger.info(f"   课程名称: {s.get('课程名称', '未知')}")
                    logger.info(f"   原始数据: 星期={day_idx}, 开始小节={start}, 结束小节={end}")
                    logger.info(f"   计算结果: row={row}, col={col}")
                    logger.info(f"   self.total_classes={self.total_classes}")
                    logger.info(f"   表格当前行数: {self.table.rowCount()}")
                
                if (row, col) in occupied:
                    continue # 手动修改已占用
                    
                name = s.get("课程名称", "")
                room = s.get("教室", "")
                teacher = s.get("教师", "")
                
                effective_end = min(end, self.total_classes)
                row_span = effective_end - start + 1
                
                # 🔍 继续调试日志
                if day_idx == 3 and start == 3 and end == 4:
                    logger.info(f"   effective_end={effective_end}, row_span={row_span}")
                    logger.info(f"   setSpan调用: setSpan({row}, {col}, {row_span}, 1)")
                
                # 检查跨度内是否被占用
                can_place = True
                for r in range(row, row + row_span):
                    if (r, col) in occupied:
                        can_place = False
                        break
                
                if can_place:
                    color = self.get_color(name)
                    
                    # 第0周强制显示周次范围
                    if self.selected_week == 0:
                        weeks_list = s.get("周次列表", [])
                        weeks_str = self.format_weeks_list(weeks_list)
                        if weeks_str:
                            name = f"{name}\n[第{weeks_str}周]"
                    
                    # 自动解析的课程保持原色，手动添加的课程使用加深的颜色和虚线边框
                    block = CourseBlock(name, room, teacher, color, is_manual=False)
                    # 确保span是正整数且大于1
                    if isinstance(row_span, int) and row_span > 1:
                        # 🔍 添加额外的调试信息
                        if day_idx == 3 and start == 3 and end == 4:
                            logger.info(f"   🔍 即将调用setSpan前的状态:")
                            logger.info(f"      occupied集合大小: {len(occupied)}")
                            logger.info(f"      检查占用情况:")
                            for r in range(row, row + row_span):
                                is_occupied = (r, col) in occupied
                                logger.info(f"         行{r}, 列{col}: {'已占用' if is_occupied else '未占用'}")
                        
                        self.table.setSpan(row, col, row_span, 1)
                        
                        # 🔍 检查setSpan后的状态
                        if day_idx == 3 and start == 3 and end == 4:
                            logger.info(f"   ✅ setSpan执行成功: ({row}, {col}, {row_span}, 1)")
                            # 验证是否真的设置了合并
                            try:
                                actual_row_span = self.table.rowSpan(row, col)
                                actual_col_span = self.table.columnSpan(row, col)
                                logger.info(f"   📊 实际合并状态: rowSpan={actual_row_span}, columnSpan={actual_col_span}")
                            except Exception as e:
                                logger.error(f"   ❌ 检查合并状态时出错: {e}")
                    self.table.setCellWidget(row, col, block)
                    for r in range(row, row + row_span):
                        occupied.add((r, col))
                        # 🔍 调试occupied集合更新
                        if day_idx == 3 and start == 3 and end == 4:
                            logger.info(f"   ➕ 添加占用记录: ({r}, {col})")
    
    def aggregate_all_courses(self, linear_data):
        """聚合所有周次的课程数据，确保周次完整性"""
        import copy
        all_courses = {}
        if not linear_data or "data" not in linear_data:
            return []
            
        for week_key, week_data in linear_data["data"].items():
            courses = week_data.get("课程列表", [])
            for course in courses:
                # 生成唯一键：星期+开始+结束+名称+教师+教室
                # 这样相同的课程在不同周次出现时会被去重
                key = (
                    course.get("星期", 0),
                    course.get("开始小节", 0),
                    course.get("结束小节", 0),
                    course.get("课程名称", ""),
                    course.get("教师", ""),
                    course.get("教室", "")
                )
                
                if key not in all_courses:
                    # 使用深拷贝避免修改原始数据
                    all_courses[key] = copy.deepcopy(course)
                else:
                    # 合并周次列表，确保数据完整性
                    existing_weeks = set(all_courses[key].get("周次列表", []))
                    new_weeks = set(course.get("周次列表", []))
                    if new_weeks - existing_weeks:
                        combined = sorted(list(existing_weeks | new_weeks))
                        all_courses[key]["周次列表"] = combined
        
        return list(all_courses.values())

    def fetch_raw_schedule_from_plugin(self):
        """直接调用插件获取原始课表数据（非线性化）"""
        try:
            cfg = load_config()
            username = cfg.get("account", "username", fallback="")
            password = cfg.get("account", "password", fallback="")
            
            if not username or not password:
                return None
            
            school_code = get_current_school_code()
            school_mod = get_school_module(school_code)
            
            if not school_mod or not hasattr(school_mod, 'fetch_course_schedule'):
                return None
                
            # 调用插件，默认不强制更新，利用插件自身的缓存机制（如果有）
            logger.info("尝试直接从插件获取原始课表数据...")
            return school_mod.fetch_course_schedule(username, password, force_update=False)
        except Exception as e:
            logger.error(f"直接调用插件获取课表失败: {e}")
            return None

    def load_data(self):
        try:
            # 重新加载配置以获取最新的时间设置
            self.cfg = load_config()
            self.morning_count = self.cfg.getint("school_time", "morning_count", fallback=4)
            self.afternoon_count = self.cfg.getint("school_time", "afternoon_count", fallback=4)
            self.evening_count = self.cfg.getint("school_time", "evening_count", fallback=2)
            self.total_classes = self.morning_count + self.afternoon_count + self.evening_count
            
            class_times_str = self.cfg.get("school_time", "class_times", fallback="")
            self.class_times = []
            if class_times_str:
                self.class_times = [t.strip() for t in class_times_str.split(",")]
            while len(self.class_times) < self.total_classes:
                self.class_times.append("")
            
            # 更新行数和时间列
            self.table.setRowCount(self.total_classes)
            self.update_time_column()

            # 检查线性化JSON文件是否存在
            linear_schedule_data = None
            
            # 第0周特殊处理：优先直接调用插件获取原始数据
            if self.selected_week == 0:
                logger.info("第0周模式：尝试直接调用插件获取原始课表数据...")
                raw_data = self.fetch_raw_schedule_from_plugin()
                if raw_data:
                    # 原始数据通常是列表，直接使用
                    linear_schedule_data = raw_data
                    logger.info(f"成功从插件获取原始数据，共{len(linear_schedule_data)}条")
                else:
                    logger.warning("从插件获取数据失败，将尝试降级使用线性化数据")

            # 如果没有通过插件获取到数据（非第0周，或获取失败），则走原有逻辑
            if linear_schedule_data is None:
                if LINEARIZER_AVAILABLE and LINEAR_SCHEDULE_FILE.exists():
                    try:
                        linear_data = load_linear_schedule("linear_schedule.json")
                        if linear_data and "data" in linear_data:
                            if self.selected_week == 0:
                                # 聚合模式：加载所有周次的课程
                                linear_schedule_data = self.aggregate_all_courses(linear_data)
                                logger.info(f"成功加载聚合课表数据，共{len(linear_schedule_data)}节课")
                            else:
                                # 获取当前周次的数据
                                current_week_key = f"第{self.selected_week}周"
                                if current_week_key in linear_data["data"]:
                                    week_data = linear_data["data"][current_week_key]
                                    linear_schedule_data = week_data.get("课程列表", [])
                                    logger.info(f"成功加载线性课表数据，第{self.selected_week}周共有{len(linear_schedule_data)}节课")
                                else:
                                    linear_schedule_data = []
                                    logger.info(f"第{self.selected_week}周无课程数据，显示为空")
                    except Exception as e:
                        logger.warning(f"加载线性课表数据失败: {e}")
                else:
                    # 如果没有线性化JSON文件，强制要求解析
                    logger.info("未找到线性化课表文件，强制解析课表...")
                    self.force_parse_schedule()
                    # 重新尝试加载
                    if LINEAR_SCHEDULE_FILE.exists():
                        try:
                            linear_data = load_linear_schedule("linear_schedule.json")
                            if linear_data and "data" in linear_data:
                                if self.selected_week == 0:
                                    linear_schedule_data = self.aggregate_all_courses(linear_data)
                                    logger.info(f"强制解析后加载聚合课表数据，共{len(linear_schedule_data)}节课")
                                else:
                                    current_week_key = f"第{self.selected_week}周"
                                    if current_week_key in linear_data["data"]:
                                        week_data = linear_data["data"][current_week_key]
                                        linear_schedule_data = week_data.get("课程列表", [])
                                        logger.info(f"强制解析后加载线性课表数据，第{self.selected_week}周共有{len(linear_schedule_data)}节课")
                                    else:
                                        linear_schedule_data = []
                                        logger.info(f"第{self.selected_week}周无课程数据，显示为空")
                        except Exception as e:
                            logger.error(f"强制解析后加载仍失败: {e}")
                        
            # 仅使用线性化数据，删除旧的HTML解析方案
            if linear_schedule_data is None:
                # 即使没有数据也不弹窗，而是显示为空
                logger.warning("未获取到课表数据或加载失败，显示空白")
                schedule_data = []
                # 仍然尝试加载手动数据
                manual_data = self.load_manual_schedule()
            else:
                # 使用线性化数据
                schedule_data = linear_schedule_data
                manual_data = self.load_manual_schedule()
            
            # 清除之前的色块和合并单元格
            for r in range(self.total_classes):
                for c in range(1, 8):
                    self.table.setCellWidget(r, c, None)
                    # 🔍 彻底重置合并状态
                    try:
                        self.table.setSpan(r, c, 1, 1)
                    except:
                        pass
                    # 不再重置span，因为默认就是(1,1)，避免警告

            # 渲染课表数据
            self.render_schedule(schedule_data, manual_data)
                    
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"渲染课表失败：{e}")