from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CourseBlock(QFrame):
    """自定义课表色块"""
    def __init__(self, name, room, teacher, color_hex, is_manual=False, is_week_zero=False):
        super().__init__()
        # 如果是手动添加的课程，使用稍微不同的样式
        if is_manual:
            # 手动添加的课程使用更深的颜色但无边框，仅通过颜色区分
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {color_hex};
                    border-radius: 6px;
                    margin: 1px;
                }}
                QLabel {{
                    color: black;
                    background: transparent;
                    font-family: "Microsoft YaHei";
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {color_hex};
                    border-radius: 6px;
                    margin: 1px;
                }}
                QLabel {{
                    color: black;
                    background: transparent;
                    font-family: "Microsoft YaHei";
                }}
            """)
        
        # 第0周使用更小的字体
        name_font_size = "11px" if is_week_zero else "13px"
        info_font_size = "9px" if is_week_zero else "11px"
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)  # 确保布局内容居中
        layout.setContentsMargins(4, 6, 4, 6)  # 增加边距以改善视觉效果
        layout.setSpacing(2)  # 增加间距
        
        name_label = QLabel(name)
        name_label.setStyleSheet(f"font-weight: bold; font-size: {name_font_size};")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setContentsMargins(0, 0, 0, 0)  # 确保标签内部没有额外边距
        
        info_text = ""
        if room: info_text += f"@{room}\n"
        if teacher: info_text += f"{teacher}"
        
        info_label = QLabel(info_text.strip())
        info_label.setStyleSheet(f"font-size: {info_font_size};")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setContentsMargins(0, 0, 0, 0)  # 确保标签内部没有额外边距
        
        layout.addWidget(name_label)
        layout.addWidget(info_label)
        layout.addStretch()