import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 添加父目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入主配置窗口
try:
    from config_window import ConfigWindow
except ImportError:
    from gui.config_window import ConfigWindow

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = BASE_DIR / "resources" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    w = ConfigWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
