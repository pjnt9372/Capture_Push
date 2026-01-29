#!/usr/bin/env python3
"""
生成Capture_Push应用的图标
"""
import sys
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # 创建一个256x256的图像
    img_size = 256
    img = Image.new('RGBA', (img_size, img_size), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制背景圆
    margin = 20
    draw.ellipse([margin, margin, img_size-margin, img_size-margin], fill=(66, 133, 244, 255))
    
    # 绘制字母"C"
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", 150)
    except:
        try:
            # 在Windows上
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 150)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
            print("警告: 使用默认字体，图标文字可能不够美观")
    
    # 计算文字位置使其居中
    text = "C"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (img_size - text_width) // 2
    y = (img_size - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # 保存PNG格式
    img.save("resources/capture_push_logo.png")
    
    # 创建ICO格式
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    ico_img.putalpha(0)
    
    # 生成多尺寸的图标
    ico_sizes = []
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        ico_sizes.append(resized)
    
    # 保存为ICO格式
    ico_img.save("resources/capture_push.ico", format="ICO", append_images=ico_sizes[1:], sizes=[size for size in sizes])
    
    print("图标已生成: resources/capture_push.ico 和 resources/capture_push.png")

if __name__ == "__main__":
    # 检查是否安装了PIL
    try:
        import PIL
    except ImportError:
        print("错误: 需要安装Pillow库来生成图标")
        print("请运行: pip install Pillow")
        sys.exit(1)
    
    # 确保resources目录存在
    os.makedirs("resources", exist_ok=True)
    
    create_icon()