#!/usr/bin/env python3
"""
测试新的音频开始特征检测功能
比较带节拍器的音频和纯音乐的检测结果
"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.audio_service import AudioService
import librosa

def test_audio_pattern(audio_path, description):
    """测试单个音频文件的模式检测"""
    print(f"\n{'='*60}")
    print(f"测试文件: {description}")
    print(f"路径: {audio_path}")
    print(f"{'='*60}")
    
    # 创建服务实例
    service = AudioService()
    
    # 加载音频
    y, sr = librosa.load(audio_path, sr=service.sample_rate, duration=30)
    
    # 分析音频模式
    pattern = service._analyze_initial_energy_pattern(y, sr)
    
    # 显示结果
    print(f"\n检测结果:")
    print(f"  模式类型: {pattern['pattern_type']}")
    print(f"  开始时间: {pattern['start_time']:.3f} 秒")
    print(f"  立即开始: {'是' if pattern['has_immediate_sound'] else '否'}")
    print(f"  周期性: {'是' if pattern['is_periodic'] else '否'}")
    print(f"  周期性强度: {pattern['periodicity_score']:.1%}")
    print(f"  节拍器可能性: {pattern['metronome_likelihood']:.1%}")
    print(f"  能量趋势: {pattern['energy_trend']:.4f}")
    print(f"  检测置信度: {pattern['start_confidence']:.1%}")
    
    # 判断
    if pattern['pattern_type'] == 'metronome':
        print(f"\n✓ 判断: 这很可能是带节拍器的音频")
    elif pattern['pattern_type'] == 'music':
        print(f"\n✗ 判断: 这更像是纯音乐（没有节拍器）")
    elif pattern['pattern_type'] == 'silence':
        print(f"\n⚠ 判断: 音频开始有较长的静音期")
    else:
        print(f"\n? 判断: 无法明确判断类型")

def main():
    print("="*60)
    print("音频开始特征检测测试")
    print("="*60)
    
    # 测试文件列表
    test_files = [
        # 带节拍器的音频
        ("/home/rui/RunningBPM/test-bpm/曾经的你.mp3", "带节拍器的音频 - 曾经的你"),
        
        # 纯音乐
        ("/home/rui/RunningBPM/Energy.flac", "纯音乐 - Energy"),
        
        # 如果有已生成的节拍器测试文件
        ("/home/rui/RunningBPM/test_metronome_only.mp3", "生成的纯节拍器音轨"),
    ]
    
    for audio_path, description in test_files:
        if os.path.exists(audio_path):
            test_audio_pattern(audio_path, description)
        else:
            print(f"\n⚠ 跳过: {description} (文件不存在)")
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()
