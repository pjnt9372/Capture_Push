# -*- coding: utf-8 -*-
"""
院校模块插件管理器
通过 GitHub API 管理院校模块插件的下载、验证、安装和加载
"""

import os
import sys
import urllib.request
import json
import tempfile
import hashlib
import zipfile
from pathlib import Path
import importlib.util
from typing import Optional, Dict, Any

PROXY_URL_PREFIX = "https://ghfast.top/"

# 延迟初始化logger
def _get_logger():
    from core.log import get_logger
    return get_logger()


class PluginManager:
    """院校模块插件管理器"""
    
    GITHUB_REPO_DEFAULT = "pjnt9372/Capture_Push_Plugin"  # 默认院校插件仓库
    API_URL_DEFAULT = f"https://api.github.com/repos/{GITHUB_REPO_DEFAULT}/releases/tags/plugin%2Flatest"  # 固定标签的插件API URL
    PLUGINS_INDEX_URL_DEFAULT = f"https://github.com/{GITHUB_REPO_DEFAULT}/releases/latest/download/plugins_index.json"  # 插件索引文件URL (从Release获取)
    
    def __init__(self):
        self.logger = _get_logger()  # 初始化logger
        self.plugins_dir = Path(__file__).parent.parent / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据下载目录
        self.data_dir = Path.home() / "AppData" / "Local" / "Capture_Push" / "data" / "downloads"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 插件索引文件本地存储路径
        self.plugins_index_file = self.data_dir / "plugins_index.json"
        
        # 当前版本文件
        self.version_file = self.plugins_dir / "current" / "version.txt"
        
        # 插件索引缓存
        self.plugins_index_cache = None
        
        # 从配置文件加载插件设置
        from core.config_manager import load_config
        config = load_config()
        
        # 获取插件仓库URL，如果没有配置则使用默认值
        if config.has_section('plugins'):
            self.repository_url = config.get('plugins', {}).get('repository_url', 
                'https://api.github.com/repos/pjnt9372/Capture_Push_Plugin/releases/tags/plugin%2Flatest')
        else:
            self.repository_url = 'https://api.github.com/repos/pjnt9372/Capture_Push_Plugin/releases/tags/plugin%2Flatest'
        
        # 获取插件索引文件URL，如果没有配置则使用默认值
        if config.has_section('plugins'):
            self.plugins_index_url = config.get('plugins', {}).get('plugins_index_url',
                'https://github.com/pjnt9372/Capture_Push_Plugin/releases/latest/download/plugins_index.json')
        else:
            self.plugins_index_url = 'https://github.com/pjnt9372/Capture_Push_Plugin/releases/download/plugin%2Flatest/plugins_index.json'
        
        self.logger.debug(f"PluginManager初始化完成，插件目录: {self.plugins_dir}, 数据目录: {self.data_dir}, 索引文件: {self.plugins_index_file}")
    
    def _get_local_plugin_version(self, school_code: str) -> str:
        """
        获取本地插件版本
        
        Args:
            school_code: 院校代码
            
        Returns:
            本地插件版本号，如果不存在则返回 '0.0.0'
        """
        self.logger.debug(f"获取本地插件版本: {school_code}")
        try:
            version_file = self.plugins_dir / school_code / "version.txt"
            if version_file.exists():
                version = version_file.read_text(encoding='utf-8').strip()
                self.logger.debug(f"插件 {school_code} 的本地版本: {version}")
                return version
            else:
                self.logger.debug(f"插件 {school_code} 未找到version.txt文件")
                # 尝试从插件模块中获取版本信息
                plugin_dir = self.plugins_dir / school_code
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    with open(init_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 查找 VERSION 常量
                        for line in content.split('\n'):
                            if line.strip().startswith('PLUGIN_VERSION') or line.strip().startswith('VERSION'):
                                parts = line.split('=')
                                if len(parts) > 1:
                                    version = parts[1].strip().strip('"\'')
                                    self.logger.debug(f"从__init__.py获取插件 {school_code} 版本: {version}")
                                    return version
        except Exception as e:
            self.logger.error(f"读取本地插件 {school_code} 版本失败: {e}")
        self.logger.debug(f"插件 {school_code} 返回默认版本: 0.0.0")
        return "0.0.0"
    
    def update_plugins_index(self) -> bool:
        """
        更新插件索引文件到本地
        
        Returns:
            是否成功更新
        """
        try:
            self.logger.info("开始更新插件索引文件...")
            self.logger.debug(f"尝试从URL获取插件索引: {self.plugins_index_url}")
            
            # 尝试从远程获取插件索引
            req = urllib.request.Request(
                self.plugins_index_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                self.logger.debug(f"HTTP响应状态码: {response.getcode()}")
                self.logger.debug(f"HTTP响应头部: {dict(response.headers)}")
                index_data = json.loads(response.read().decode('utf-8'))
                self.logger.debug(f"成功解析远程插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
            
            # 保存到本地文件
            with open(self.plugins_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self.plugins_index_cache = index_data
            self.logger.info(f"插件索引已更新并保存到: {self.plugins_index_file}")
            return True
            
        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP错误访问插件索引文件: {e.code} - {e.reason}")
            self.logger.error(f"响应内容: {e.read().decode('utf-8') if e.read() else 'No response body'}")
            return False
        except urllib.error.URLError as e:
            self.logger.warning(f"直接访问插件索引文件失败: {e}")
            
            # 尝试使用代理访问
            try:
                proxy_url = PROXY_URL_PREFIX + self.plugins_index_url
                self.logger.info(f"尝试使用代理访问插件索引: {proxy_url}")
                req_proxy = urllib.request.Request(
                    proxy_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    self.logger.debug(f"代理HTTP响应状态码: {response.getcode()}")
                    index_data = json.loads(response.read().decode('utf-8'))
                    self.logger.debug(f"通过代理成功解析插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                
                # 保存到本地文件
                with open(self.plugins_index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                
                # 更新缓存
                self.plugins_index_cache = index_data
                self.logger.info(f"插件索引已通过代理更新并保存到: {self.plugins_index_file}")
                return True
                
            except Exception as proxy_error:
                self.logger.error(f"通过代理访问插件索引也失败: {proxy_error}")
                return False
        except json.JSONDecodeError as e:
            self.logger.error(f"插件索引JSON解析失败: {e}")
            self.logger.error(f"接收到的原始数据: {e.doc[:200] if e.doc else 'Unknown'}")
            return False
        except Exception as e:
            self.logger.error(f"更新插件索引失败: {e}", exc_info=True)
            return False
    
    def get_local_plugins_index(self) -> Optional[Dict[str, Any]]:
        """
        获取本地存储的插件索引
        
        Returns:
            插件索引字典，如果文件不存在则返回 None
        """
        try:
            if self.plugins_index_file.exists():
                self.logger.debug(f"尝试从本地文件加载插件索引: {self.plugins_index_file}")
                with open(self.plugins_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                self.logger.debug(f"成功从本地加载插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                return index_data
            else:
                self.logger.warning(f"本地插件索引文件不存在: {self.plugins_index_file}")
                # 检查旧位置是否存在插件索引文件，如果存在则迁移
                old_index_file = self.plugins_dir / "plugins_index.json"
                if old_index_file.exists():
                    self.logger.info(f"在旧位置找到插件索引文件，正在迁移: {old_index_file} -> {self.plugins_index_file}")
                    import shutil
                    shutil.copy2(old_index_file, self.plugins_index_file)
                    self.logger.info(f"插件索引文件已迁移到新位置")
                    # 重新尝试加载
                    with open(self.plugins_index_file, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)
                    self.logger.debug(f"成功从迁移后的文件加载插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                    return index_data
                return None
        except json.JSONDecodeError as e:
            self.logger.error(f"本地插件索引JSON解析失败: {e}")
            self.logger.error(f"文件内容预览: {str(e)[:200]}")
            return None
        except Exception as e:
            self.logger.error(f"读取本地插件索引失败: {e}")
            return None
    
    def check_plugin_update(self, school_code: str) -> Optional[Dict[str, Any]]:
        """
        检查指定院校插件是否有更新
            
        Args:
            school_code: 院校代码
            
        Returns:
            插件更新信息字典，如果没有更新则返回 None
        """
        try:
            self.logger.info(f"正在检查插件更新: {school_code}")
                
            # 首先尝试从插件索引获取信息（备用方式）
            plugin_info = self.get_plugin_info_from_index(school_code)
                
            if plugin_info:
                self.logger.info(f"从插件索引获取到 {school_code} 的插件信息: {plugin_info}")
                    
                # 检查版本
                remote_version = plugin_info.get('plugin_version', '0.0.0')
                local_version = self._get_local_plugin_version(school_code)
                    
                self.logger.info(f"院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                    
                if self._compare_version(remote_version, local_version) > 0:
                    # 添加远程信息
                    plugin_info['remote_version'] = remote_version
                    plugin_info['local_version'] = local_version
                    self.logger.info(f"插件 {school_code} 有更新: {local_version} -> {remote_version}")
                    return plugin_info
                else:
                    self.logger.info(f"院校 {school_code} 插件已是最新版本")
                    return None
            else:
                self.logger.info(f"插件索引中未找到 {school_code} 的插件信息，尝试从固定标签 plugin/latest 获取")
                    
            # 从固定的 plugin/latest 标签获取插件信息
            req = urllib.request.Request(
                self.repository_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
                        
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                            
            # 解析发布说明中的插件信息
            body = data.get('body', '')
            plugin_info = self._parse_plugin_info(body, school_code)
                        
            # 如果解析到了插件信息，添加作者信息
            if plugin_info:
                # 优先使用JSON中提供的贡献者信息
                if 'contributor' not in plugin_info:
                    # 从发布数据中获取作者信息
                    author = data.get('author', {}).get('login', 'Unknown')
                    plugin_info['contributor'] = author
                        
            # 如果没从发布说明中找到插件信息，尝试从资产中推断
            if not plugin_info:
                plugin_info = self._infer_plugin_info_from_assets(data.get('assets', []), school_code, data)
                # 如果是从资产中推断的，也需要添加贡献者信息
                if plugin_info and 'contributor' not in plugin_info:
                    author = data.get('author', {}).get('login', 'Unknown')
                    plugin_info['contributor'] = author
                        
            if not plugin_info:
                self.logger.warning(f"在发布说明中未找到插件信息: {school_code}")
                return None
                    
            # 检查版本
            remote_version = plugin_info.get('plugin_version', '0.0.0')
            local_version = self._get_local_plugin_version(school_code)
                
            self.logger.info(f"院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                
            if self._compare_version(remote_version, local_version) > 0:
                # 添加下载URL信息
                plugin_info['download_url'] = self._get_download_url(data, school_code)
                plugin_info['remote_version'] = remote_version
                plugin_info['local_version'] = local_version
                self.logger.info(f"插件 {school_code} 有更新: {local_version} -> {remote_version}")
                return plugin_info
            else:
                self.logger.info(f"院校 {school_code} 插件已是最新版本")
                return None
                    
        except urllib.error.URLError as e:
            self.logger.warning(f"直接访问GitHub API失败: {e}")
                
            # 尝试使用代理访问API
            try:
                self.logger.info(f"尝试使用代理访问API: {PROXY_URL_PREFIX}{self.repository_url}")
                proxy_api_url = PROXY_URL_PREFIX + self.repository_url
                req_proxy = urllib.request.Request(
                    proxy_api_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                    
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    data = json.loads(response.read().decode('utf-8'))
                        
                # 尝试从插件索引获取（备用方式）
                plugin_info = self.get_plugin_info_from_index(school_code)
                    
                if plugin_info:
                    self.logger.info(f"从插件索引获取到 {school_code} 的插件信息")
                        
                    # 检查版本
                    remote_version = plugin_info.get('plugin_version', '0.0.0')
                    local_version = self._get_local_plugin_version(school_code)
                        
                    self.logger.info(f"通过代理检查院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                        
                    if self._compare_version(remote_version, local_version) > 0:
                        # 添加远程信息
                        plugin_info['remote_version'] = remote_version
                        plugin_info['local_version'] = local_version
                        self.logger.info(f"插件 {school_code} 有更新 (通过代理): {local_version} -> {remote_version}")
                        return plugin_info
                    else:
                        self.logger.info(f"院校 {school_code} 插件已是最新版本 (通过代理检查)")
                        return None
                    
                # 从固定的 plugin/latest 标签获取插件信息
                # 解析发布说明中的插件信息
                body = data.get('body', '')
                plugin_info = self._parse_plugin_info(body, school_code)
                                
                # 如果解析到了插件信息，添加作者信息
                if plugin_info:
                    # 优先使用JSON中提供的贡献者信息
                    if 'contributor' not in plugin_info:
                        # 从发布数据中获取作者信息
                        author = data.get('author', {}).get('login', 'Unknown')
                        plugin_info['contributor'] = author
                                
                # 如果没从发布说明中找到插件信息，尝试从资产中推断
                if not plugin_info:
                    plugin_info = self._infer_plugin_info_from_assets(data.get('assets', []), school_code, data)
                    # 如果是从资产中推断的，也需要添加贡献者信息
                    if plugin_info and 'contributor' not in plugin_info:
                        author = data.get('author', {}).get('login', 'Unknown')
                        plugin_info['contributor'] = author
                                
                if not plugin_info:
                    self.logger.warning(f"在发布说明中未找到插件信息: {school_code}")
                    return None
                        
                # 检查版本
                remote_version = plugin_info.get('plugin_version', '0.0.0')
                local_version = self._get_local_plugin_version(school_code)
                    
                self.logger.info(f"通过代理检查院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                    
                if self._compare_version(remote_version, local_version) > 0:
                    # 添加下载URL信息
                    plugin_info['download_url'] = self._get_download_url(data, school_code)
                    plugin_info['remote_version'] = remote_version
                    plugin_info['local_version'] = local_version
                    self.logger.info(f"插件 {school_code} 有更新 (通过代理): {local_version} -> {remote_version}")
                    return plugin_info
                else:
                    self.logger.info(f"院校 {school_code} 插件已是最新版本 (通过代理检查)")
                    return None
                        
            except Exception as proxy_error:
                self.logger.error(f"通过代理检查插件更新失败: {proxy_error}")
                return None
        except Exception as e:
            self.logger.error(f"检查插件 {school_code} 更新失败: {e}", exc_info=True)
            return None
    
    def _parse_plugin_info(self, body: str, school_code: str) -> Optional[Dict[str, Any]]:
        """
        从发布说明中解析插件信息
            
        Args:
            body: 发布说明文本
            school_code: 院校代码
            
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        try:
            self.logger.debug(f"尝试从发布说明中解析插件 {school_code} 的信息")
            # 尝试解析JSON格式的插件信息
            lines = body.split('\n')
            for i, line in enumerate(lines):
                if f'"school_code": "{school_code}"' in line or f"'school_code': '{school_code}'" in line:
                    # 向前查找JSON开始
                    start_idx = i
                    while start_idx >= 0:
                        if '{' in lines[start_idx]:
                            break
                        start_idx -= 1
                    # 向后查找JSON结束
                    end_idx = i
                    brace_count = 0
                    for j in range(start_idx, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count <= 0 and '}' in lines[j]:
                            end_idx = j
                            break
                    
                    # 组合JSON字符串
                    json_str = '\n'.join(lines[start_idx:end_idx+1])
                    # 清理可能的非JSON内容
                    json_str = self._extract_json_object(json_str)
                        
                    if json_str:
                        plugin_info = json.loads(json_str)
                        if plugin_info.get('school_code') == school_code:
                            self.logger.debug(f"成功解析插件 {school_code} 的信息: {plugin_info}")
                            return plugin_info
                                
            # 如果上面的方法失败，尝试查找特定格式
            import re
            # 查找包含学校代码和版本信息的格式
            pattern = rf'{school_code}.*?(plugin_version|version)["\']?\s*:\s*["\']([^"\']+)["\']?.*?sha256["\']?\s*:\s*["\']([^"\']+)["\']?', re.DOTALL
            match = re.search(pattern, body.replace('\n', ' '))
            if match:
                result = {
                    'school_code': school_code,
                    'plugin_version': match.group(2),
                    'sha256': match.group(3)
                }
                self.logger.debug(f"通过正则表达式解析插件 {school_code} 的信息: {result}")
                return result
                    
            # 更宽松的匹配模式
            version_patterns = [
                rf'{school_code}.*?v(\d+\.\d+\.\d+).*?([a-fA-F0-9]{{64}})',  # school_code v1.0.0 sha256
                rf'{school_code}.*?(\d+\.\d+\.\d+).*?([a-fA-F0-9]{{64}})',   # school_code 1.0.0 sha256
            ]
                
            for pat in version_patterns:
                match = re.search(pat, body.replace('\n', ' '))
                if match:
                    result = {
                        'school_code': school_code,
                        'plugin_version': match.group(1),
                        'sha256': match.group(2)
                    }
                    self.logger.debug(f"通过宽松模式解析插件 {school_code} 的信息: {result}")
                    return result
                    
        except Exception as e:
            self.logger.error(f"解析插件信息失败: {e}")
        self.logger.debug(f"未能从发布说明中解析插件 {school_code} 的信息")
        return None
    
    def _infer_plugin_info_from_assets(self, assets: list, school_code: str, release_data: dict) -> Optional[Dict[str, Any]]:
        """
        从发布资产中推断插件信息
            
        Args:
            assets: 发布资产列表
            school_code: 院校代码
            release_data: 发布数据
            
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        try:
            self.logger.debug(f"尝试从发布资产中推断插件 {school_code} 的信息")
            # 查找与学校代码匹配的ZIP文件
            for asset in assets:
                asset_name = asset.get('name', '')
                expected_name = f"school_{school_code}_plugin.zip"
                if asset_name == expected_name:
                    self.logger.debug(f"找到匹配的资产文件: {asset_name}")
                    # 从发布说明中查找版本信息
                    tag_name = release_data.get('tag_name', 'v1.0.0')
                    version = tag_name.lstrip('v')
                        
                    # 如果发布说明中有时间戳版本，优先使用
                    body_text = release_data.get('body', '')
                    if '"plugin_version":' in body_text:
                        import re
                        # 查找 "plugin_version": "timestamp" 格式
                        version_match = re.search(r'"plugin_version":\s*"([^\"]+)"', body_text)
                        if version_match:
                            version = version_match.group(1)
                        
                    # 从资产中获取校验和（如果有提供）
                    sha256 = None
                    if 'body' in release_data:
                        body_text = release_data['body']
                        if school_code in body_text:
                            import re
                            # 查找SHA256校验和
                            checksum_matches = re.findall(r'[a-fA-F0-9]{64}', body_text)
                            for match in checksum_matches:
                                # 简单检查是否与当前资产相关
                                if len(checksum_matches) == 1:
                                    sha256 = match
                                    break
                                elif school_code in body_text:
                                    # 如果有多个校验和，需要更精确的匹配
                                    # 这里简化处理，使用第一个匹配的
                                    sha256 = match
                                    break
                        
                    # 如果没找到校验和，使用资产的校验和（如果API提供）
                    if not sha256 and 'sha256' in asset:
                        sha256 = asset['sha256']
                        
                    # 使用资产中的下载URL，但确保它是正确的仓库
                    download_url = asset.get('browser_download_url', '')
                        
                    result = {
                        'school_code': school_code,
                        'plugin_version': version,
                        'sha256': sha256 or '',
                        'download_url': download_url,
                        'contributor': release_data.get('author', {}).get('login', 'Unknown')
                    }
                    self.logger.debug(f"从资产中推断插件 {school_code} 的信息: {result}")
                    return result
                
            # 如果没有找到特定学校的资产，使用第一个ZIP文件
            for asset in assets:
                asset_name = asset.get('name', '')
                if asset_name.endswith('.zip'):
                    self.logger.debug(f"使用第一个ZIP文件作为插件 {school_code} 的资产: {asset_name}")
                    tag_name = release_data.get('tag_name', 'v1.0.0')
                    version = tag_name.lstrip('v')
                        
                    # 使用资产中的下载URL，但确保它是正确的仓库
                    download_url = asset.get('browser_download_url', '')
                        
                    result = {
                        'school_code': school_code,
                        'plugin_version': version,
                        'sha256': '',
                        'download_url': download_url,
                        'contributor': release_data.get('author', {}).get('login', 'Unknown')
                    }
                    self.logger.debug(f"从任意ZIP资产中推断插件 {school_code} 的信息: {result}")
                    return result
                        
        except Exception as e:
            self.logger.error(f"从资产中推断插件 {school_code} 信息失败: {e}")
        self.logger.debug(f"未能从发布资产中推断插件 {school_code} 的信息")
        return None
    
    def _fetch_plugins_index(self) -> Optional[Dict[str, Any]]:
        """
        从远程获取插件索引文件
        
        Returns:
            插件索引字典，如果获取失败则返回 None
        """
        try:
            self.logger.debug("开始获取插件索引")
            self.logger.debug(f"尝试使用的URL: {self.plugins_index_url}")
            # 首先检查缓存
            if self.plugins_index_cache:
                self.logger.debug("使用缓存的插件索引")
                return self.plugins_index_cache
            
            # 首先尝试从本地文件加载
            self.logger.debug(f"尝试从本地文件加载插件索引: {self.plugins_index_file}")
            local_index = self.get_local_plugins_index()
            if local_index:
                # 更新缓存
                self.plugins_index_cache = local_index
                self.logger.debug("成功从本地文件加载插件索引并更新缓存")
                return local_index
            
            self.logger.debug("本地插件索引文件不存在或加载失败，尝试从远程获取")
            
            # 本地文件不存在，从远程获取
            self.logger.debug(f"准备发送网络请求到: {self.plugins_index_url}")
            req = urllib.request.Request(
                self.plugins_index_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            
            self.logger.debug(f"发送GET请求到: {self.plugins_index_url}")
            with urllib.request.urlopen(req, timeout=10) as response:
                self.logger.debug(f"远程插件索引HTTP响应状态码: {response.getcode()}")
                self.logger.debug(f"远程插件索引HTTP响应头部: {dict(response.headers)}")
                response_content = response.read().decode('utf-8')
                self.logger.debug(f"接收到的响应内容长度: {len(response_content)} 字符")
                self.logger.debug(f"响应内容预览 (前200字符): {response_content[:200] if len(response_content) > 0 else 'Empty response'}")
                
                try:
                    index_data = json.loads(response_content)
                    self.logger.debug(f"成功从远程解析插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"JSON解析失败: {json_err}")
                    self.logger.error(f"响应内容: {response_content}")
                    raise json_err
            
            # 保存到本地文件
            self.logger.debug(f"准备保存插件索引到本地文件: {self.plugins_index_file}")
            with open(self.plugins_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"插件索引已保存到本地文件: {self.plugins_index_file}")
            
            # 更新缓存
            self.plugins_index_cache = index_data
            self.logger.debug("成功从远程获取插件索引并保存到本地文件")
            return index_data
            
        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP错误访问插件索引文件: {e.code} - {e.reason}")
            try:
                error_content = e.read().decode('utf-8')
                self.logger.error(f"HTTP错误响应内容: {error_content}")
            except Exception as read_err:
                self.logger.error(f"读取HTTP错误响应失败: {read_err}")
            
            # 尝试使用代理访问
            try:
                proxy_url = PROXY_URL_PREFIX + self.plugins_index_url
                self.logger.info(f"尝试使用代理访问插件索引: {proxy_url}")
                req_proxy = urllib.request.Request(
                    proxy_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                
                self.logger.debug(f"发送代理GET请求到: {proxy_url}")
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    self.logger.debug(f"代理插件索引HTTP响应状态码: {response.getcode()}")
                    self.logger.debug(f"代理插件索引HTTP响应头部: {dict(response.headers)}")
                    response_content = response.read().decode('utf-8')
                    self.logger.debug(f"代理响应内容长度: {len(response_content)} 字符")
                    self.logger.debug(f"代理响应内容预览 (前200字符): {response_content[:200] if len(response_content) > 0 else 'Empty response'}")
                    
                    try:
                        index_data = json.loads(response_content)
                        self.logger.debug(f"通过代理成功解析插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                    except json.JSONDecodeError as json_err:
                        self.logger.error(f"代理响应JSON解析失败: {json_err}")
                        self.logger.error(f"代理响应内容: {response_content}")
                        raise json_err
                
                # 保存到本地文件
                self.logger.debug(f"准备保存代理获取的插件索引到本地文件: {self.plugins_index_file}")
                with open(self.plugins_index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                    self.logger.debug(f"代理获取的插件索引已保存到本地文件: {self.plugins_index_file}")
                
                # 更新缓存
                self.plugins_index_cache = index_data
                self.logger.info("通过代理成功获取插件索引并保存到本地文件")
                return index_data
                
            except Exception as proxy_error:
                self.logger.error(f"通过代理访问插件索引也失败: {proxy_error}")
                self.logger.error("无法获取插件索引，将尝试使用本地已有的索引文件")
                # 再次尝试从本地文件加载
                local_index = self.get_local_plugins_index()
                if local_index:
                    self.logger.info("虽然远程获取失败，但仍可使用本地插件索引")
                    self.plugins_index_cache = local_index
                    return local_index
                else:
                    self.logger.error("无法获取插件索引，本地也没有可用的索引文件")
                    return None
        except urllib.error.URLError as e:
            self.logger.warning(f"直接访问插件索引文件失败: {e}")
            self.logger.error(f"URLError详细信息: {type(e).__name__}: {str(e)}")
            
            # 尝试使用代理访问
            try:
                proxy_url = PROXY_URL_PREFIX + self.plugins_index_url
                self.logger.info(f"尝试使用代理访问插件索引: {proxy_url}")
                req_proxy = urllib.request.Request(
                    proxy_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                
                self.logger.debug(f"发送代理GET请求到: {proxy_url}")
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    self.logger.debug(f"代理插件索引HTTP响应状态码: {response.getcode()}")
                    self.logger.debug(f"代理插件索引HTTP响应头部: {dict(response.headers)}")
                    response_content = response.read().decode('utf-8')
                    self.logger.debug(f"代理响应内容长度: {len(response_content)} 字符")
                    self.logger.debug(f"代理响应内容预览 (前200字符): {response_content[:200] if len(response_content) > 0 else 'Empty response'}")
                    
                    try:
                        index_data = json.loads(response_content)
                        self.logger.debug(f"通过代理成功解析插件索引，包含 {len(index_data) if isinstance(index_data, dict) else len(index_data) if isinstance(index_data, list) else 'unknown'} 个项目")
                    except json.JSONDecodeError as json_err:
                        self.logger.error(f"代理响应JSON解析失败: {json_err}")
                        self.logger.error(f"代理响应内容: {response_content}")
                        raise json_err
                
                # 保存到本地文件
                self.logger.debug(f"准备保存代理获取的插件索引到本地文件: {self.plugins_index_file}")
                with open(self.plugins_index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                    self.logger.debug(f"代理获取的插件索引已保存到本地文件: {self.plugins_index_file}")
                
                # 更新缓存
                self.plugins_index_cache = index_data
                self.logger.info("通过代理成功获取插件索引并保存到本地文件")
                return index_data
                
            except Exception as proxy_error:
                self.logger.error(f"通过代理访问插件索引也失败: {proxy_error}")
                self.logger.error("无法获取插件索引，将尝试使用本地已有的索引文件")
                # 再次尝试从本地文件加载
                local_index = self.get_local_plugins_index()
                if local_index:
                    self.logger.info("虽然远程获取失败，但仍可使用本地插件索引")
                    self.plugins_index_cache = local_index
                    return local_index
                else:
                    self.logger.error("无法获取插件索引，本地也没有可用的索引文件")
                    return None
        except json.JSONDecodeError as e:
            self.logger.error(f"插件索引JSON解析失败: {e}")
            self.logger.error(f"JSON解析错误行号: {e.lineno}, 列号: {e.colno}")
            self.logger.error(f"接收到的原始数据预览: {e.doc[:500] if e.doc else 'Unknown'}")  # 增加预览长度
            self.logger.error("将尝试使用本地已有的索引文件")
            # 尝试从本地文件加载
            local_index = self.get_local_plugins_index()
            if local_index:
                self.logger.info("虽然远程JSON解析失败，但仍可使用本地插件索引")
                self.plugins_index_cache = local_index
                return local_index
            else:
                self.logger.error("无法获取插件索引，本地也没有可用的索引文件")
                return None
        except Exception as e:
            self.logger.error(f"获取插件索引失败: {e}", exc_info=True)
            self.logger.error("将尝试使用本地已有的索引文件")
            # 尝试从本地文件加载
            local_index = self.get_local_plugins_index()
            if local_index:
                self.logger.info("虽然远程获取失败，但仍可使用本地插件索引")
                self.plugins_index_cache = local_index
                return local_index
            else:
                self.logger.error("无法获取插件索引，本地也没有可用的索引文件")
                return None

    def clear_plugins_index_cache(self):
        """
        清除插件索引缓存，强制下次获取时重新从网络加载
        """
        self.plugins_index_cache = None
        
    def force_refresh_plugins_index(self) -> bool:
        """
        强制刷新插件索引文件，删除本地缓存并重新从远程获取
        
        Returns:
            是否成功刷新
        """
        try:
            self.logger.info("开始强制刷新插件索引文件...")
            
            # 清除内存缓存
            self.clear_plugins_index_cache()
            
            # 删除本地索引文件，强制重新下载
            if self.plugins_index_file.exists():
                self.plugins_index_file.unlink()  # 删除文件
                self.logger.info(f"已删除本地插件索引文件: {self.plugins_index_file}")
            
            # 尝试重新获取插件索引
            plugins_index = self._fetch_plugins_index()
            if plugins_index:
                self.logger.info("插件索引已成功强制刷新")
                return True
            else:
                self.logger.error("强制刷新插件索引失败")
                return False
                
        except Exception as e:
            self.logger.error(f"强制刷新插件索引时发生错误: {e}")
            return False

    def get_available_plugins(self) -> Dict[str, str]:
        """
        获取所有可用的插件列表
        
        Returns:
            院校代码到院校名称的映射
        """
        self.logger.debug("开始获取已安装插件列表")
        plugins = {}
        
        # 从插件目录获取
        if self.plugins_dir.exists():
            self.logger.debug(f"检查插件目录: {self.plugins_dir}")
            for item in self.plugins_dir.iterdir():
                # 检查是否为学校代码目录（数字组成的目录名）
                if (item.is_dir() and 
                    not item.name.startswith('backup_') and 
                    not item.name.startswith('v') and 
                    item.name != 'current' and
                    item.name != 'plugins_index.json' and  # 排除索引文件
                    item.name.isdigit()):  # 学校代码通常为数字
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        try:
                            # 为了支持相对导入，需要将插件目录添加到 sys.path
                            import sys
                            plugin_dir_str = str(item)
                            if plugin_dir_str not in sys.path:
                                sys.path.insert(0, plugin_dir_str)
                            
                            spec = importlib.util.spec_from_file_location(
                                f"plugins_school_{item.name}", 
                                str(init_file)
                            )
                            module = importlib.util.module_from_spec(spec)
                            # 设置模块的 __package__ 属性以支持相对导入
                            module.__package__ = f"plugins_school_{item.name}"
                            spec.loader.exec_module(module)
                            
                            # 移除临时添加的路径
                            if plugin_dir_str in sys.path:
                                sys.path.remove(plugin_dir_str)
                            
                            school_name = getattr(module, "SCHOOL_NAME", item.name)
                            plugins[item.name] = school_name
                            self.logger.debug(f"找到已安装插件: {item.name} - {school_name}")
                        except Exception as e:
                            self.logger.error(f"加载插件信息失败 {item.name}: {e}")
                            continue
        else:
            self.logger.warning(f"插件目录不存在: {self.plugins_dir}")
        
        # 同时检查内置插件目录（保持向后兼容）
        builtin_dir = Path(__file__).parent / "school"
        if builtin_dir.exists():
            self.logger.debug(f"检查内置插件目录: {builtin_dir}")
            for item in builtin_dir.iterdir():
                if item.is_dir() and item.name not in plugins:  # 只添加尚未在插件目录中的插件
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        try:
                            # 为了支持相对导入，需要将插件目录添加到 sys.path
                            import sys
                            plugin_dir_str = str(item)
                            if plugin_dir_str not in sys.path:
                                sys.path.insert(0, plugin_dir_str)
                            
                            spec = importlib.util.spec_from_file_location(
                                f"builtin_school_{item.name}", 
                                str(init_file)
                            )
                            module = importlib.util.module_from_spec(spec)
                            # 设置模块的 __package__ 属性以支持相对导入
                            module.__package__ = f"builtin_school_{item.name}"
                            spec.loader.exec_module(module)
                            
                            # 移除临时添加的路径
                            if plugin_dir_str in sys.path:
                                sys.path.remove(plugin_dir_str)
                            
                            school_name = getattr(module, "SCHOOL_NAME", item.name)
                            plugins[item.name] = school_name
                            self.logger.debug(f"找到内置插件: {item.name} - {school_name}")
                        except Exception as e:
                            self.logger.error(f"加载内置插件信息失败 {item.name}: {e}")
                            continue
        else:
            self.logger.debug(f"内置插件目录不存在: {builtin_dir}")
        
        self.logger.info(f"共找到 {len(plugins)} 个已安装插件")
        return plugins

    def get_uninstalled_plugins(self) -> Dict[str, str]:
        """
        获取所有未安装的插件列表（存在于索引中但本地未安装）
        
        Returns:
            院校代码到院校名称的映射
        """
        self.logger.debug("开始获取未安装插件列表")
        
        # 获取本地已安装插件
        self.logger.debug("开始获取本地已安装插件")
        installed_plugins = self.get_available_plugins()
        self.logger.debug(f"已安装插件数量: {len(installed_plugins)}, 插件列表: {list(installed_plugins.keys())}")
        
        # 获取远程插件索引
        self.logger.debug("开始获取远程插件索引")
        remote_plugins = self._fetch_plugins_index()
        if not remote_plugins:
            self.logger.warning("无法获取远程插件索引")
            self.logger.debug("远程插件索引为空，返回空字典")
            return {}
        
        self.logger.debug(f"获取到远程插件索引类型: {type(remote_plugins)}, 大小: {len(remote_plugins) if isinstance(remote_plugins, (dict, list)) else 'N/A'}")
        
        uninstalled_plugins = {}
        
        # 解析远程插件列表
        if isinstance(remote_plugins, dict):
            # 检查索引格式，可能是直接的插件列表，也可能有专门的plugins键
            plugins_list = remote_plugins.get('plugins', [])
            if not plugins_list:  # 如果没有plugins键，尝试直接使用整个索引
                if isinstance(remote_plugins, list):
                    plugins_list = remote_plugins
            
            self.logger.debug(f"远程插件列表数量: {len(plugins_list)}")
            for i, plugin in enumerate(plugins_list):
                self.logger.debug(f"处理远程插件列表第 {i+1}/{len(plugins_list)} 项: {plugin}")
                school_code = plugin.get('school_code')
                school_name = plugin.get('school_name', plugin.get('name', school_code))
                
                if school_code and school_code not in installed_plugins:
                    uninstalled_plugins[school_code] = school_name
                    self.logger.debug(f"找到未安装插件: {school_code} - {school_name}")
                elif school_code and school_code in installed_plugins:
                    self.logger.debug(f"插件 {school_code} 已安装，跳过")
                elif not school_code:
                    self.logger.debug(f"插件列表项中没有school_code字段，跳过: {plugin}")
        else:
            self.logger.error(f"远程插件索引不是字典类型: {type(remote_plugins)}")
        
        self.logger.info(f"共找到 {len(uninstalled_plugins)} 个未安装插件")
        self.logger.debug(f"未安装插件列表: {list(uninstalled_plugins.keys())}")
        return uninstalled_plugins

    def get_all_available_plugins(self) -> Dict[str, str]:
        """
        获取所有可用的插件列表（包括已安装和未安装的）
        
        Returns:
            院校代码到院校名称的映射
        """
        self.logger.debug("开始获取所有可用插件列表")
        
        # 获取已安装插件
        self.logger.debug("开始获取已安装插件")
        installed_plugins = self.get_available_plugins()
        self.logger.debug(f"已安装插件数量: {len(installed_plugins)}, 插件列表: {list(installed_plugins.keys())}")
        
        # 获取未安装插件
        self.logger.debug("开始获取未安装插件")
        uninstalled_plugins = self.get_uninstalled_plugins()
        self.logger.debug(f"未安装插件数量: {len(uninstalled_plugins)}, 插件列表: {list(uninstalled_plugins.keys())}")
        
        # 合并两个字典
        all_plugins = {**installed_plugins, **uninstalled_plugins}
        
        self.logger.info(f"共找到 {len(all_plugins)} 个所有可用插件（包括已安装和未安装）")
        self.logger.debug(f"所有可用插件列表: {list(all_plugins.keys())}")
        return all_plugins

    def get_plugin_info_from_index(self, school_code: str) -> Optional[Dict[str, Any]]:
        """
        从插件索引中获取指定插件的信息
        
        Args:
            school_code: 院校代码
        
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        self.logger.debug(f"尝试从插件索引获取插件 {school_code} 的信息")
        self.logger.debug(f"当前插件索引缓存状态: {'已缓存' if self.plugins_index_cache else '未缓存'}")
        plugins_index = self._fetch_plugins_index()
        index_content_desc = f'复杂对象，长度{len(plugins_index) if isinstance(plugins_index, (dict, list)) else "N/A"}' if not isinstance(plugins_index, (str, type(None))) else plugins_index
        self.logger.debug(f"获取到的插件索引类型: {type(plugins_index)}, 内容: {index_content_desc}")
        
        if not plugins_index:
            self.logger.warning(f"无法获取插件索引，无法查找插件 {school_code}")
            return None
            
        if isinstance(plugins_index, dict):
            # 检查索引格式，可能是直接的插件列表，也可能有专门的plugins键
            plugins_list = plugins_index.get('plugins', [])
            if not plugins_list:  # 如果没有plugins键，尝试直接使用整个索引
                if isinstance(plugins_index, list):
                    plugins_list = plugins_index
            
            self.logger.debug(f"插件索引中插件列表大小: {len(plugins_list)}, 类型: {type(plugins_list)}")
            for i, plugin in enumerate(plugins_list):
                plugin_desc = f'复杂对象，keys: {list(plugin.keys()) if isinstance(plugin, dict) else "N/A"}' if not isinstance(plugin, str) else plugin
                self.logger.debug(f"检查插件列表第 {i+1}/{len(plugins_list)} 项: {type(plugin)} - {plugin_desc}")
                
                if isinstance(plugin, dict):
                    found_code = plugin.get('school_code')
                    self.logger.debug(f"检查插件列表第 {i+1} 项: school_code={found_code}")
                    if found_code == school_code:
                        self.logger.info(f"在插件索引中找到插件 {school_code} 的信息: {plugin}")
                        return plugin
                else:
                    self.logger.debug(f"插件列表第 {i+1} 项不是字典类型: {type(plugin)}")
        else:
            self.logger.error(f"插件索引不是字典类型: {type(plugins_index)}")
        
        self.logger.debug(f"在插件索引中未找到插件 {school_code}")
        return None
    
    def _extract_json_object(self, text: str) -> Optional[str]:
        """
        从文本中提取JSON对象
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            JSON字符串，如果未找到则返回 None
        """
        try:
            # 查找第一个 { 的位置
            start = text.find('{')
            if start == -1:
                return None
                
            # 从头开始计数括号
            brace_count = 0
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start:i+1]
        except Exception:
            pass
        return None
    
    def _get_download_url(self, release_data: dict, school_code: str) -> Optional[str]:
        """
        从发布数据中获取指定院校插件的下载URL
            
        Args:
            release_data: GitHub Release 数据
            school_code: 院校代码
            
        Returns:
            下载URL，如果未找到则返回 None
        """
        try:
            assets = release_data.get('assets', [])
            self.logger.debug(f"发布资产列表大小: {len(assets)}")
            for asset in assets:
                # 查找特定院校的ZIP文件，格式为 school_[code]_plugin.zip
                expected_name = f"school_{school_code}_plugin.zip"
                asset_name = asset.get('name', '')
                if asset_name == expected_name:
                    download_url = asset.get('browser_download_url', '')
                    self.logger.debug(f"找到插件 {school_code} 的下载URL: {download_url}")
                    return download_url
            # 如果没找到特定院校的ZIP，返回第一个匹配的ZIP
            for asset in assets:
                asset_name = asset.get('name', '')
                if f"school_{school_code}_plugin.zip" in asset_name:
                    download_url = asset.get('browser_download_url', '')
                    self.logger.debug(f"找到插件 {school_code} 的备选下载URL: {download_url}")
                    return download_url
        except Exception as e:
            self.logger.error(f"获取插件 {school_code} 下载URL失败: {e}")
        self.logger.debug(f"未找到插件 {school_code} 的下载URL")
        return None
    
    def _compare_version(self, v1: str, v2: str) -> int:
        """
        比较版本号
        
        Args:
            v1: 远程版本
            v2: 本地版本
            
        Returns:
            1 if v1 > v2 (有更新)
            0 if v1 == v2 (无更新)
            -1 if v1 < v2 (当前版本更高)
        """
        self.logger.debug(f"版本比较: 远程 {v1} vs 本地 {v2}")
        try:
            # 处理版本号格式 (x.x.x)
            parts1 = [int(x) for x in v1.replace('-', '.').replace('_', '.').split('.') if x.isdigit()]
            parts2 = [int(x) for x in v2.replace('-', '.').replace('_', '.').split('.') if x.isdigit()]
            
            # 补齐长度
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            # 比较每个版本段
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    self.logger.debug(f"版本比较结果: 远程版本更高 ({v1} > {v2})")
                    return 1
                elif p1 < p2:
                    self.logger.debug(f"版本比较结果: 本地版本更高 ({v1} < {v2})")
                    return -1
            self.logger.debug(f"版本比较结果: 版本相同 ({v1} == {v2})")
            return 0
        except Exception as e:
            self.logger.error(f"版本号比较失败: {e}")
            return 0
    
    def download_and_install_plugin(self, school_code: str, plugin_info: Dict[str, Any]) -> bool:
        """
        下载并安装插件
            
        Args:
            school_code: 院校代码
            plugin_info: 插件信息字典
            
        Returns:
            是否成功安装
        """
        self.logger.info(f"开始下载并安装插件: {school_code}")
        try:
            download_url = plugin_info.get('download_url')
            expected_sha256 = plugin_info.get('sha256')
                
            if not download_url:
                self.logger.error(f"插件 {school_code} 缺少下载URL")
                return False
                    
            self.logger.info(f"正在下载插件包: {download_url}")
                
            # 下载插件到数据目录
            downloads_dir = self.data_dir / "plugins"
            downloads_dir.mkdir(exist_ok=True)
            zip_path = downloads_dir / f"school_{school_code}_plugin.zip"
                
            # 使用更新模块中的通用下载功能
            from core.updater import download_file
            success = download_file(
                url=download_url,
                destination=str(zip_path),
                expected_checksum=expected_sha256,
                progress_callback=None
            )
            
            if not success:
                self.logger.error(f"插件 {school_code} 下载失败")
                return False
            
            self.logger.debug(f"插件 {school_code} 下载完成: {zip_path}")
                
            # 创建时间戳目录
            import time
            timestamp = str(int(time.time()))
            final_plugin_dir = self.plugins_dir / school_code
                
            # 备份当前插件（如果存在）
            if final_plugin_dir.exists():
                backup_dir = self.plugins_dir / f"backup_{school_code}_{int(time.time())}"
                import shutil
                shutil.move(str(final_plugin_dir), str(backup_dir))
                self.logger.info(f"已备份原插件到: {backup_dir}")
                
            # 解压插件到目标目录
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(str(final_plugin_dir))
                self.logger.debug(f"插件 {school_code} 解压完成")
                
            # 写入版本信息
            version_file = final_plugin_dir / "version.txt"
            version_file.write_text(plugin_info.get('plugin_version', 'unknown'), encoding='utf-8')
            self.logger.info(f"版本信息已写入: {plugin_info.get('plugin_version', 'unknown')}")
                
            self.logger.info(f"插件 {school_code} 安装成功")
            return True
                
        except Exception as e:
            self.logger.error(f"下载并安装插件 {school_code} 失败: {e}", exc_info=True)
            return False
    
    
    
    def load_plugin(self, school_code: str):
        """
        动态加载指定院校的插件
            
        Args:
            school_code: 院校代码
            
        Returns:
            插件模块，如果加载失败则返回 None
        """
        try:
            # 首先尝试从插件目录加载
            plugin_dir = self.plugins_dir / school_code
            plugin_init_file = plugin_dir / "__init__.py"
                
            if plugin_init_file.exists():
                self.logger.debug(f"尝试从插件目录加载插件: {school_code}")
                # 为了支持相对导入，需要将插件目录添加到 sys.path
                import sys
                plugin_dir_str = str(plugin_dir)
                if plugin_dir_str not in sys.path:
                    sys.path.insert(0, plugin_dir_str)
                spec = importlib.util.spec_from_file_location(
                    f"plugins_school_{school_code}", 
                    str(plugin_init_file)
                )
                module = importlib.util.module_from_spec(spec)
                # 设置模块的 __package__ 属性以支持相对导入
                module.__package__ = f"plugins_school_{school_code}"
                spec.loader.exec_module(module)
                # 移除临时添加的路径
                if plugin_dir_str in sys.path:
                    sys.path.remove(plugin_dir_str)
                self.logger.debug(f"插件 {school_code} 加载成功")
                return module
            else:
                self.logger.debug(f"插件 {school_code} 不存在于插件目录中")
                
            # 如果插件目录中没有找到，不再尝试从core.school加载（移除历史兼容性）
            self.logger.warning(f"插件 {school_code} 不存在于插件目录中")
                    
        except Exception as e:
            self.logger.error(f"加载插件 {school_code} 失败: {e}")
        return None


# 全局插件管理器实例（延迟初始化）
_plugin_manager_instance = None

def get_plugin_manager():
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance

plugin_manager = get_plugin_manager()