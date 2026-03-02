# -*- coding: utf-8 -*-
"""
二维码生成模块
负责生成包含数据传输信息的二维码
"""

import json
import base64
import io
from typing import Dict, Any, Optional
from datetime import datetime

# 导入日志模块
try:
    from log import get_logger
except ImportError:
    from core.log import get_logger

logger = get_logger('qrcode_generator')

# 尝试导入二维码库
try:
    import qrcode
    from qrcode.image.pil import PilImage
    QR_CODE_AVAILABLE = True
except ImportError:
    QR_CODE_AVAILABLE = False
    logger.warning("qrcode库未安装，二维码功能不可用")

# 导入数据导出器
try:
    from core.data_exporter import export_full_data, export_schedule_only, get_export_summary
    from core.export_methods.network_server import get_server_status
except ImportError:
    # 备用导入
    try:
        from data_exporter import export_full_data, export_schedule_only, get_export_summary
        from network_server import get_server_status
    except:
        pass


def compress_data(data: Dict[str, Any]) -> str:
    """
    压缩数据为Base64字符串
    
    Args:
        data: 要压缩的数据字典
        
    Returns:
        压缩后的Base64字符串
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        compressed_bytes = json_str.encode('utf-8')
        base64_str = base64.b64encode(compressed_bytes).decode('ascii')
        return base64_str
    except Exception as e:
        logger.error(f"数据压缩失败: {e}")
        return ""


def decompress_data(base64_str: str) -> Dict[str, Any]:
    """
    解压Base64字符串为数据字典
    
    Args:
        base64_str: Base64编码的字符串
        
    Returns:
        解压后的数据字典
    """
    try:
        compressed_bytes = base64.b64decode(base64_str.encode('ascii'))
        json_str = compressed_bytes.decode('utf-8')
        data = json.loads(json_str)
        return data
    except Exception as e:
        logger.error(f"数据解压失败: {e}")
        return {}


def generate_network_qr_code(auto_start_server: bool = True) -> Dict[str, Any]:
    """
    生成网络传输二维码
    
    Args:
        auto_start_server: 是否自动启动服务器
        
    Returns:
        包含二维码信息的字典
    """
    if not QR_CODE_AVAILABLE:
        return {"status": "error", "message": "二维码库未安装"}
    
    try:
        # 获取服务器状态
        server_status = get_server_status()
        
        # 如果服务器未运行且需要自动启动
        if not server_status.get("running", False) and auto_start_server:
            # 尝试启动服务器
            from core.export_methods.network_server import start_server
            if start_server("0.0.0.0", 8080):
                # 等待服务器启动
                import time
                time.sleep(1)
                # 重新获取状态
                server_status = get_server_status()
            else:
                return {"status": "error", "message": "服务器启动失败"}
        
        if not server_status.get("running", False):
            return {"status": "error", "message": "服务器未启动"}
        
        # 构建传输信息
        transfer_info = {
            "type": "network",
            "protocol": "http",
            "host": server_status.get("local_ip", "localhost"),
            "port": server_status.get("port", 8080),
            "endpoints": {
                "full": "/api/full",
                "schedule": "/api/schedule", 
                "grades": "/api/grades",
                "summary": "/api/summary"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 生成二维码
        qr_data = json.dumps(transfer_info, ensure_ascii=False)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # 创建图像
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存到内存缓冲区
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # 转换为Base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        
        return {
            "status": "success",
            "type": "network",
            "data": transfer_info,
            "qr_image": img_base64,
            "qr_size": img.size,
            "instructions": "扫描此二维码可在局域网内访问数据传输服务"
        }
        
    except Exception as e:
        logger.error(f"生成网络二维码失败: {e}")
        return {"status": "error", "message": str(e)}


def generate_direct_data_qr_code(data_type: str = "summary") -> Dict[str, Any]:
    """
    生成直接数据二维码（包含实际数据）
    
    Args:
        data_type: 数据类型 (full/schedule/summary)
        
    Returns:
        包含二维码信息的字典
    """
    if not QR_CODE_AVAILABLE:
        return {"status": "error", "message": "二维码库未安装"}
    
    try:
        # 根据数据类型获取数据
        if data_type == "full":
            data = export_full_data()
        elif data_type == "schedule":
            data = export_schedule_only()
        elif data_type == "summary":
            data = get_export_summary()
        else:
            return {"status": "error", "message": f"不支持的数据类型: {data_type}"}
        
        # 构建传输信息
        transfer_info = {
            "type": "direct_data",
            "data_type": data_type,
            "data": data,
            "compressed": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # 压缩数据
        compressed_data = compress_data(transfer_info)
        
        # 检查数据大小（二维码有容量限制）
        if len(compressed_data) > 2953:  # QR Code Version 40的最大容量
            return {"status": "error", "message": "数据过大，无法生成二维码"}
        
        # 生成二维码
        qr = qrcode.QRCode(
            version=None,  # 自动选择版本
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(compressed_data)
        qr.make(fit=True)
        
        # 创建图像
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存到内存缓冲区
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # 转换为Base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        
        return {
            "status": "success",
            "type": "direct_data",
            "data_type": data_type,
            "original_size": len(json.dumps(transfer_info, ensure_ascii=False)),
            "compressed_size": len(compressed_data),
            "compression_ratio": f"{(1 - len(compressed_data)/len(json.dumps(transfer_info, ensure_ascii=False)))*100:.1f}%",
            "qr_image": img_base64,
            "qr_size": img.size,
            "instructions": f"扫描此二维码可直接获取{data_type}数据"
        }
        
    except Exception as e:
        logger.error(f"生成直接数据二维码失败: {e}")
        return {"status": "error", "message": str(e)}


def generate_file_transfer_qr_code(file_path: str) -> Dict[str, Any]:
    """
    生成文件传输二维码
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含二维码信息的字典
    """
    if not QR_CODE_AVAILABLE:
        return {"status": "error", "message": "二维码库未安装"}
    
    try:
        import os
        from pathlib import Path
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {"status": "error", "message": "文件不存在"}
        
        # 构建文件信息
        file_info = {
            "type": "file_transfer",
            "file_path": str(file_path_obj.absolute()),
            "file_name": file_path_obj.name,
            "file_size": file_path_obj.stat().st_size,
            "timestamp": datetime.now().isoformat()
        }
        
        # 生成二维码
        qr_data = json.dumps(file_info, ensure_ascii=False)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # 创建图像
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存到内存缓冲区
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # 转换为Base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        
        return {
            "status": "success",
            "type": "file_transfer",
            "file_info": file_info,
            "qr_image": img_base64,
            "qr_size": img.size,
            "instructions": f"扫描此二维码可获取文件: {file_path_obj.name}"
        }
        
    except Exception as e:
        logger.error(f"生成文件传输二维码失败: {e}")
        return {"status": "error", "message": str(e)}


def save_qr_image(qr_result: Dict[str, Any], output_path: str) -> bool:
    """
    保存二维码图像到文件
    
    Args:
        qr_result: 二维码生成结果
        output_path: 输出文件路径
        
    Returns:
        保存是否成功
    """
    try:
        if qr_result.get("status") != "success":
            return False
        
        if "qr_image" not in qr_result:
            return False
        
        # 解码Base64图像数据
        img_data = base64.b64decode(qr_result["qr_image"].encode('ascii'))
        
        # 保存到文件
        with open(output_path, 'wb') as f:
            f.write(img_data)
        
        logger.info(f"二维码图像已保存到: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"保存二维码图像失败: {e}")
        return False


# 备用的数据导出函数（如果导入失败）
def export_schedule_only():
    """备用课表导出函数"""
    try:
        from core.data_exporter import export_schedule_only as real_export
        return real_export()
    except:
        return {"status": "error", "message": "课表导出功能不可用"}

def export_grades_only():
    """备用成绩导出函数"""
    try:
        from core.data_exporter import export_grades_only as real_export
        return real_export()
    except:
        return {"status": "error", "message": "成绩导出功能不可用"}


# 命令行接口
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Capture_Push 二维码生成工具")
    parser.add_argument("--network", action="store_true", help="生成网络传输二维码")
    parser.add_argument("--direct", choices=["full", "schedule", "summary"], 
                       help="生成直接数据二维码")
    parser.add_argument("--file", help="生成文件传输二维码")
    parser.add_argument("--save", help="保存二维码图像到指定文件")
    parser.add_argument("--info", action="store_true", help="显示二维码库信息")
    
    args = parser.parse_args()
    
    if args.info:
        print(f"二维码功能可用: {QR_CODE_AVAILABLE}")
        if QR_CODE_AVAILABLE:
            print("qrcode库版本:", getattr(qrcode, '__version__', 'Unknown'))
        else:
            print("请安装qrcode库: pip install qrcode[pil]")
        sys.exit(0)
    
    if not QR_CODE_AVAILABLE:
        print("错误: 二维码库未安装")
        print("请运行: pip install qrcode[pil]")
        sys.exit(1)
    
    result = None
    
    if args.network:
        result = generate_network_qr_code()
    elif args.direct:
        result = generate_direct_data_qr_code(args.direct)
    elif args.file:
        result = generate_file_transfer_qr_code(args.file)
    else:
        parser.print_help()
        sys.exit(1)
    
    if result:
        if result.get("status") == "success":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 如果指定了保存路径，保存图像
            if args.save and "qr_image" in result:
                if save_qr_image(result, args.save):
                    print(f"二维码图像已保存到: {args.save}")
                else:
                    print("保存二维码图像失败")
        else:
            print(f"生成失败: {result.get('message', '未知错误')}")
            sys.exit(1)