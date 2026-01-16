# -*- coding: utf-8 -*-
import requests
import json
import configparser
from pathlib import Path

try:
    from log import init_logger, get_config_path
except ImportError:
    from core.log import init_logger, get_config_path

# 延迟初始化
_logger = None
_config_path = None

def _get_logger():
    global _logger, _config_path
    if _logger is None:
        _logger = init_logger('feishu_sender')
        _config_path = get_config_path()
    return _logger

def _get_config_path():
    global _config_path
    if _config_path is None:
        _get_logger()
    return _config_path

class FeishuSender:
    """飞书机器人推送实现"""
    
    def send(self, subject, content):
        logger = _get_logger()
        config_path = _get_config_path()
        
        cfg = configparser.ConfigParser()
        cfg.read(str(config_path), encoding='utf-8')
        
        try:
            webhook_url = cfg.get("feishu", "webhook_url", fallback="").strip()
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.error("配置文件中缺少 [feishu] 配置节或 webhook_url")
            return False

        if not webhook_url:
            logger.error("飞书 Webhook 地址为空")
            return False

        # 飞书消息格式
        # 考虑到 subject 和 content，我们合并为文本发送
        message_text = f"{subject}\n\n{content}"
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": message_text
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"正在向飞书发送消息: {subject}")
            response = requests.post(
                webhook_url, 
                data=json.dumps(payload), 
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书消息发送失败: {result.get('msg')}")
                return False
                
        except Exception as e:
            logger.error(f"调用飞书接口发生异常: {e}")
            return False
