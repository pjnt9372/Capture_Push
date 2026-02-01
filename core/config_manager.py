# -*- coding: utf-8 -*-
import configparser
import io
import os
import logging
from pathlib import Path
from core.log import get_config_path
from core.utils import dpapi


class ConfigDecodingError(Exception):
    """配置文件解码错误"""
    pass


def load_config():
    """读取并自动解密配置文件"""
    config_path = get_config_path()  # 保持原始Path对象类型
    cfg = configparser.ConfigParser()
    
    # 检查配置文件是否存在
    if not config_path.exists():
        # 配置文件不存在，创建一个默认配置并加密保存
        create_default_config()
        return cfg

    try:
        # 读取二进制内容
        with open(config_path, 'rb') as f:
            raw_data = f.read()
        
        # 尝试解密
        try:
            content = dpapi.decrypt(raw_data)
            cfg.read_string(content)
        except Exception:
            # 如果解密失败，说明是明文或损坏，尝试以 utf-8 读取
            try:
                content = raw_data.decode('utf-8')
                cfg.read_string(content)
                
                # 如果是明文配置文件，立即加密保存
                logger = logging.getLogger(__name__)
                logger.info(f"检测到明文配置文件，正在加密: {config_path}")
                save_config(cfg)  # 这会将明文配置加密保存
                logger.info(f"配置文件已加密保存: {config_path}")
            except UnicodeDecodeError:
                # 如果UTF-8解码也失败，说明文件编码有问题
                raise ConfigDecodingError(f"配置文件编码错误，无法解码: {config_path}")
    except ConfigDecodingError:
        # 重新抛出配置解码错误
        raise
    except Exception as e:
        # 兜底：直接使用 configparser 读取（可能还是会失败，但这是最后尝试）
        try:
            cfg.read(str(config_path), encoding='utf-8')
        except Exception as final_error:
            # 如果所有方法都失败，抛出配置解码错误
            raise ConfigDecodingError(f"配置文件格式错误，无法解析: {str(final_error)}")

    return cfg


def create_default_config():
    """创建默认配置文件并加密保存"""
    logger = logging.getLogger(__name__)
    
    # 获取配置文件路径
    config_path = get_config_path()
    
    # 创建默认配置
    cfg = configparser.ConfigParser()
    
    # 添加默认配置段
    cfg['logging'] = {'level': 'INFO'}
    cfg['run_model'] = {'model': 'BUILD'}
    cfg['account'] = {'school_code': '10546', 'username': '', 'password': ''}
    cfg['semester'] = {'first_monday': '2026-02-24'}
    cfg['loop_getCourseGrades'] = {'enabled': 'False', 'time': '3600'}
    cfg['loop_getCourseSchedule'] = {'enabled': 'False', 'time': '3600'}
    cfg['push'] = {'method': 'none'}
    cfg['email'] = {
        'smtp': 'smtp.example.com',
        'port': '465',
        'sender': 'your_email@example.com',
        'receiver': 'target_email@example.com',
        'auth': 'your_email_password_or_auth_code'
    }
    cfg['feishu'] = {'webhook_url': 'https://open.feishu.cn/open-apis/bot/v2/hook/****', 'secret': ''}
    cfg['serverchan'] = {'sendkey': ''}
    
    # 确保目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存配置（会自动加密）
    save_config(cfg)
    
    logger.info(f"默认配置文件已创建并加密: {config_path}")

def save_config(cfg):
    """保存并加密配置文件"""
    config_path = str(get_config_path())
    
    # 将配置写入字符串流
    output = io.StringIO()
    cfg.write(output)
    content = output.getvalue()
    
    # 使用 DPAPI 加密
    encrypted_data = dpapi.encrypt(content)
    
    # 写入二进制文件
    with open(config_path, 'wb') as f:
        f.write(encrypted_data)


def get_plaintext_config_from_encrypted():
    """从加密的配置文件获取明文配置内容"""
    config_path = str(get_config_path())
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    # 读取二进制内容
    with open(config_path, 'rb') as f:
        raw_data = f.read()
    
    # 尝试解密
    try:
        content = dpapi.decrypt(raw_data)
        return content
    except Exception as e:
        # 如果解密失败，抛出异常
        raise Exception(f"解密配置文件失败: {str(e)}")
