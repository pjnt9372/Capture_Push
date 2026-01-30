#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件构建脚本
用于构建插件ZIP包并更新插件索引文件
"""

import os
import sys
import json
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime


def calculate_sha256(file_path):
    """计算文件的SHA256校验和"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # 分块读取文件，避免大文件占用过多内存
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_plugin(school_code, output_dir=".", plugin_dir=None):
    """
    构建插件ZIP包
    
    Args:
        school_code: 学校代码
        output_dir: 输出目录
        plugin_dir: 插件源目录，默认为 core/school/[school_code]
    
    Returns:
        ZIP文件路径和SHA256校验和
    """
    if plugin_dir is None:
        plugin_dir = Path("core") / "school" / school_code
    
    plugin_dir = Path(plugin_dir)
    
    # 检查插件目录是否存在
    if not plugin_dir.exists():
        raise FileNotFoundError(f"插件目录不存在: {plugin_dir}")
    
    # 检查必要文件
    required_files = ["__init__.py", "getCourseGrades.py", "getCourseSchedule.py"]
    for file in required_files:
        if not (plugin_dir / file).exists():
            raise FileNotFoundError(f"缺少必要文件: {plugin_dir / file}")
    
    # 创建ZIP文件名
    zip_filename = f"school_{school_code}_plugin.zip"
    zip_path = Path(output_dir) / zip_filename
    
    # 创建ZIP文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(plugin_dir):
            for file in files:
                file_path = Path(root) / file
                # 将文件添加到ZIP中，不包含目录结构
                arcname = file_path.relative_to(plugin_dir)
                zipf.write(file_path, arcname)
    
    # 计算SHA256
    sha256 = calculate_sha256(zip_path)
    
    print(f"插件构建成功: {zip_path}")
    print(f"SHA256: {sha256}")
    
    return str(zip_path), sha256


def update_plugins_index(school_code, school_name, sha256, download_url, contributor, 
                       plugins_index_path="plugins_index.json"):
    """
    更新插件索引文件
    
    Args:
        school_code: 学校代码
        school_name: 学校名称
        sha256: 插件ZIP文件的SHA256校验和
        download_url: 下载URL
        contributor: 贡献者
        plugins_index_path: 插件索引文件路径
    """
    # 读取现有索引文件，如果不存在则创建空的
    plugins_index_path = Path(plugins_index_path)
    if plugins_index_path.exists():
        with open(plugins_index_path, 'r', encoding='utf-8') as f:
            try:
                index_data = json.load(f)
            except json.JSONDecodeError:
                print(f"警告: {plugins_index_path} 不是有效的JSON文件，将创建新的索引文件")
                index_data = {"plugins": []}
    else:
        index_data = {"plugins": []}
    
    # 确保plugins是列表
    if "plugins" not in index_data:
        index_data["plugins"] = []
    
    # 生成时间戳版本号
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建或更新插件信息
    plugin_info = {
        "school_code": school_code,
        "school_name": school_name,
        "plugin_version": timestamp,
        "sha256": sha256,
        "download_url": download_url,
        "contributor": contributor,
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }
    
    # 检查插件是否已存在，如果存在则更新，否则添加
    plugin_exists = False
    for i, plugin in enumerate(index_data["plugins"]):
        if plugin.get("school_code") == school_code:
            index_data["plugins"][i] = plugin_info
            plugin_exists = True
            break
    
    if not plugin_exists:
        index_data["plugins"].append(plugin_info)
    
    # 写入更新后的索引文件
    with open(plugins_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"插件索引文件已更新: {plugins_index_path}")


def main():
    print("=== 插件构建工具 ===")
    school_code = input("请输入学校代码 (如: 10546): ").strip()
    school_name = input("请输入学校名称 (如: 某某大学): ").strip()
    contributor = input("请输入贡献者用户名: ").strip()
    
    plugin_dir_input = input("请输入插件源目录 (直接回车使用默认: core/school/[学校代码]): ").strip()
    plugin_dir = plugin_dir_input if plugin_dir_input else None
    
    try:
        # 构建插件
        zip_path, sha256 = build_plugin(school_code, plugin_dir=plugin_dir)
        
        # 生成下载URL（这是一个示例URL，实际使用时需要替换为真实URL）
        download_url = f"https://github.com/pjnt9372/Capture_Push_School_Plugins/releases/download/plugin%2Flatest/school_{school_code}_plugin.zip"
        
        # 更新插件索引
        update_plugins_index(school_code, school_name, sha256, download_url, contributor)
        
        print(f"\n构建完成!")
        print(f"ZIP文件: {zip_path}")
        print(f"SHA256: {sha256}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()