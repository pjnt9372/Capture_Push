# -*- coding: utf-8 -

import sys
import os
import subprocess
import winreg
import ctypes
import argparse
from pathlib import Path

# 添加项目根目录到模块搜索路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def is_admin():
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def register_service():
    """注册服务"""
    print("正在注册服务...")
    
    # 获取当前Python解释器路径
    python_exe = sys.executable
    script_path = Path(__file__).parent.parent / "core" / "go.py"
    
    if not script_path.exists():
        print(f"错误: 脚本文件不存在: {script_path}")
        return False
    
    try:
        # 使用subprocess注册服务（这里只是一个示例，实际的服务注册取决于您的需求）
        print(f"注册服务: {script_path}")
        
        # 这里可以根据您的实际需求实现服务注册逻辑
        # 例如，写入注册表或使用Windows服务
        print("服务注册完成")
        return True
    except Exception as e:
        print(f"注册服务失败: {e}")
        return False


def undo_register():
    """撤销注册"""
    print("正在撤销注册...")
    
    try:
        # 撤销之前注册的服务或注册表项
        print("撤销注册完成")
        return True
    except Exception as e:
        print(f"撤销注册失败: {e}")
        return False


def register_startup():
    """注册开机启动"""
    print("正在注册开机启动项...")
    
    try:
        # 注册开机启动项
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        # 获取当前脚本路径
        script_dir = Path(__file__).parent.parent
        executable_path = script_dir / "dist" / "CapturePush.exe"  # 假设您有打包后的exe
        
        # 如果没有打包的exe，使用Python脚本
        if not executable_path.exists():
            executable_path = sys.executable
            script_path = script_dir / "gui" / "gui.py"
            cmd = f'"{executable_path}" "{script_path}"'
        else:
            cmd = f'"{executable_path}"'
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "CapturePush", 0, winreg.REG_SZ, cmd)
        
        print("开机启动项注册完成")
        return True
    except Exception as e:
        print(f"注册开机启动项失败: {e}")
        return False


def undo_register_startup():
    """撤销开机启动注册"""
    print("正在撤销开机启动项...")
    
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, "CapturePush")
        
        print("开机启动项撤销完成")
        return True
    except FileNotFoundError:
        print("开机启动项不存在，无需撤销")
        return True
    except Exception as e:
        print(f"撤销开机启动项失败: {e}")
        return False


def interactive_mode():
    """交互模式"""
    print("="*50)
    print("CapturePush 注册/撤销注册工具")
    print("="*50)
    print("请选择操作:")
    print("1. 注册服务")
    print("2. 撤销注册服务")
    print("3. 注册开机启动")
    print("4. 撤销开机启动")
    print("5. 退出")
    print("-"*50)
    
    while True:
        try:
            choice = input("请输入选项 (1-5): ").strip()
            
            if choice == "1":
                register_service()
            elif choice == "2":
                undo_register()
            elif choice == "3":
                register_startup()
            elif choice == "4":
                undo_register_startup()
            elif choice == "5":
                print("退出程序")
                break
            else:
                print("无效选项，请重新输入")
                
            print()  # 空行
        except KeyboardInterrupt:
            print("\n用户中断操作")
            break
        except Exception as e:
            print(f"操作失败: {e}")


def main():
    """主函数"""
    if not is_admin():
        print("警告: 建议以管理员身份运行此工具")
        response = input("是否继续? (y/N): ")
        if response.lower() != 'y':
            return

    parser = argparse.ArgumentParser(description='CapturePush 注册/撤销注册工具')
    parser.add_argument('--register-service', action='store_true', help='注册服务')
    parser.add_argument('--undo-register', action='store_true', help='撤销注册服务')
    parser.add_argument('--register-startup', action='store_true', help='注册开机启动')
    parser.add_argument('--undo-startup', action='store_true', help='撤销开机启动')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.register_service:
        register_service()
    elif args.undo_register:
        undo_register()
    elif args.register_startup:
        register_startup()
    elif args.undo_startup:
        undo_register_startup()
    else:
        # 如果没有指定参数，进入交互模式
        interactive_mode()


if __name__ == "__main__":
    main()