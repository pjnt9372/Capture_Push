# -*- coding: utf-8 -*-
"""
简化版局域网传输服务模块
只提供一个统一的JSON数据展示端点
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, Any, Optional
import socket

# 导入日志模块
try:
    from log import get_logger
except ImportError:
    from core.log import get_logger

# 导入数据导出器
try:
    from core.data_exporter import export_full_data
except ImportError:
    # 备用导入
    try:
        from data_exporter import export_full_data
    except ImportError:
        # 如果都失败，创建模拟函数
        def export_full_data():
            return {"error": "data_exporter not available", "message": "数据导出模块不可用"}

logger = get_logger('simple_network_server')

# 默认配置
DEFAULT_HOST = "0.0.0.0"  # 监听所有接口
DEFAULT_PORT = 8080
SERVER_INSTANCE = None
SERVER_THREAD = None


class SimpleDataHandler(BaseHTTPRequestHandler):
    """简化版数据HTTP请求处理器"""
    
    def log_message(self, format, *args):
        """重写日志方法，使用项目日志系统"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            if path == "/" or path == "/data":
                self._handle_data()
            elif path == "/status":
                self._handle_status()
            else:
                self._handle_not_found()
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            self._handle_error(str(e))
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')  # 允许跨域
        self.end_headers()
        
        response_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_html_response(self, html_content: str, status_code: int = 200):
        """发送HTML响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _handle_data(self):
        """处理数据请求 - 返回完整JSON数据"""
        logger.info("收到数据请求")
        try:
            # 获取完整数据
            data = export_full_data()
            
            if isinstance(data, dict) and data.get("status") == "error":
                self._send_json_response({"error": data["message"]}, 500)
            else:
                # 直接返回原始数据，不做额外包装
                self._send_json_response(data)
        except Exception as e:
            self._handle_error(f"获取数据失败: {str(e)}")
    
    def _handle_status(self):
        """处理状态查询"""
        response = {
            "status": "online",
            "service": "Capture_Push Simple Data Server",
            "version": "1.0",
            "timestamp": time.time(),
            "host": self.server.server_address[0],
            "port": self.server.server_address[1]
        }
        self._send_json_response(response)
    
    def _handle_not_found(self):
        """处理404错误"""
        # 提供友好的HTML页面
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Capture_Push 数据服务</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        h1 { color: #333; }
        code { background: #eee; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Capture_Push 数据传输服务</h1>
        <p>欢迎使用Capture_Push数据传输服务。以下是可用的端点：</p>
        
        <div class="endpoint">
            <strong>主数据端点:</strong><br>
            <code>GET /data</code> 或 <code>GET /</code><br>
            返回完整的课表和配置数据
        </div>
        
        <div class="endpoint">
            <strong>状态端点:</strong><br>
            <code>GET /status</code><br>
            返回服务器运行状态
        </div>
        
        <p><em>服务由Capture_Push提供</em></p>
    </div>
</body>
</html>
        """
        self._send_html_response(html_content, 404)
    
    def _handle_error(self, error_message: str):
        """处理服务器内部错误"""
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "error": error_message,
            "timestamp": time.time()
        }
        self.wfile.write(json.dumps(response).encode())


class SimpleDataServer:
    """简化版数据服务器类"""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.httpd = None
        self.is_running = False
        self.start_time = None
        
    def get_local_ip(self) -> Optional[str]:
        """获取本机局域网IP地址"""
        try:
            # 创建UDP socket来获取本地IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.error(f"获取本地IP失败: {e}")
            return None
    
    def start(self) -> bool:
        """启动服务器"""
        if self.is_running:
            logger.warning("服务器已在运行中")
            return True
        
        try:
            # 尝试启动服务器
            self.httpd = HTTPServer((self.host, self.port), SimpleDataHandler)
            self.is_running = True
            self.start_time = time.time()
            
            local_ip = self.get_local_ip()
            if local_ip:
                logger.info(f"简化数据服务器已启动")
                logger.info(f"主数据端点: http://{local_ip}:{self.port}/data")
                logger.info(f"状态端点: http://{local_ip}:{self.port}/status")
                logger.info(f"本地访问: http://localhost:{self.port}")
            else:
                logger.info(f"简化数据服务器已启动，端口: {self.port}")
            
            # 在新线程中运行服务器
            server_thread = threading.Thread(target=self._run_server, daemon=True)
            server_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            return False
    
    def _run_server(self):
        """运行服务器主循环"""
        try:
            self.httpd.serve_forever()
        except Exception as e:
            logger.error(f"服务器运行出错: {e}")
        finally:
            self.is_running = False
    
    def stop(self):
        """停止服务器"""
        if not self.is_running:
            logger.warning("服务器未在运行")
            return
        
        try:
            if self.httpd:
                self.httpd.shutdown()
                self.httpd.server_close()
            
            self.is_running = False
            logger.info("简化数据服务器已停止")
        except Exception as e:
            logger.error(f"停止服务器失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        local_ip = self.get_local_ip()
        base_url = f"http://{local_ip}:{self.port}" if local_ip else f"http://localhost:{self.port}"
        
        return {
            "running": self.is_running,
            "host": self.host,
            "port": self.port,
            "local_ip": local_ip,
            "start_time": self.start_time,
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "endpoints": {
                "main_data": f"{base_url}/data",
                "root": f"{base_url}/",
                "status": f"{base_url}/status"
            }
        }


def start_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """启动全局服务器实例"""
    global SERVER_INSTANCE, SERVER_THREAD
    
    if SERVER_INSTANCE and SERVER_INSTANCE.is_running:
        logger.warning("服务器已在运行中")
        return True
    
    try:
        SERVER_INSTANCE = SimpleDataServer(host, port)
        success = SERVER_INSTANCE.start()
        
        if success:
            SERVER_THREAD = threading.current_thread()
            return True
        else:
            SERVER_INSTANCE = None
            return False
            
    except Exception as e:
        logger.error(f"启动服务器实例失败: {e}")
        return False


def stop_server():
    """停止全局服务器实例"""
    global SERVER_INSTANCE
    
    if SERVER_INSTANCE:
        SERVER_INSTANCE.stop()
        SERVER_INSTANCE = None


def get_server_status() -> Dict[str, Any]:
    """获取服务器状态"""
    if SERVER_INSTANCE:
        return SERVER_INSTANCE.get_status()
    else:
        return {"running": False, "message": "服务器未启动"}


# 命令行接口
if __name__ == "__main__":
    import argparse
    import signal
    import sys
    
    parser = argparse.ArgumentParser(description="Capture_Push 简化数据传输服务")
    parser.add_argument("--host", default=DEFAULT_HOST, help="绑定主机地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="绑定端口号")
    parser.add_argument("--status", action="store_true", help="显示服务器状态")
    
    args = parser.parse_args()
    
    if args.status:
        status = get_server_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        # 启动服务器
        print(f"正在启动简化数据传输服务...")
        print(f"绑定地址: {args.host}:{args.port}")
        
        if start_server(args.host, args.port):
            print("服务启动成功!")
            print("主数据端点: /data")
            print("状态端点: /status")
            print("按 Ctrl+C 停止服务")
            
            def signal_handler(sig, frame):
                print("\n正在停止服务...")
                stop_server()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            
            # 保持主线程运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                signal_handler(None, None)
        else:
            print("服务启动失败!")
            sys.exit(1)