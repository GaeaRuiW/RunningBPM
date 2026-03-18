#!/usr/bin/env python3
"""
单独测试指定文件的提取质量
"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.audio_service import AudioService

def progress_callback(progress, message):
    print(f"[{progress:3d}%] {message}")

def main():
    test_file = "/home/rui/RunningBPM/test-bpm/数学王希伟 - 喜欢你.mp3"
    output_path = "/home/rui/RunningBPM/extracted_xihuan_ni.wav"
    
    print("="*60)
    print("测试文件: 数学王希伟 - 喜欢你.mp3")
    print("="*60)
    print()
    
    # 创建服务
    audio_service = AudioService()
    
    # 提取节拍
    print("开始提取节拍...")
    print("-"*60)
    beat = audio_service._extract_single_beat(test_file, progress_callback)
    
    # 保存
    print()
    print(f"保存到: {output_path}")
    beat.export(output_path, format="wav")
    print("✓ 完成")
    
    print()
    print("="*60)
    print("请使用以下命令分析质量:")
    print(f"  python compare_source_and_extracted.py")
    print("或播放文件确认:")
    print(f"  {output_path}")
    print("="*60)

if __name__ == "__main__":
    main()
