#!/usr/bin/env python3
"""
提取多个候选节拍片段，让用户选择最好的
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import librosa
import numpy as np
from scipy import signal
import soundfile as sf

def extract_candidates(audio_path, output_dir="/home/rui/RunningBPM"):
    """提取多个候选节拍片段"""
    print("=" * 70)
    print("提取候选节拍片段")
    print("=" * 70)
    print(f"输入文件: {audio_path}")
    print()
    
    # 加载音频前10秒
    print("加载音频...")
    y, sr = librosa.load(audio_path, sr=44100, duration=10.0)
    print(f"采样率: {sr} Hz")
    print()
    
    # 检测所有节拍点
    print("检测节拍点...")
    hop_length = 512
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, units='frames', hop_length=hop_length,
        backtrack=True, delta=0.1, wait=8
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
    
    print(f"检测到 {len(onset_frames)} 个节拍点")
    print()
    
    # 提取前10个节拍点的原始音频（不滤波）
    print("提取前10个节拍点的音频片段...")
    print("-" * 70)
    
    candidates = []
    
    for i in range(min(10, len(onset_frames))):
        onset_frame = onset_frames[i]
        onset_sample = int(onset_frame * hop_length)
        onset_time = onset_times[i]
        
        # 提取150ms的原始音频
        beat_start = max(0, onset_sample - int(sr * 0.05))
        beat_end = min(len(y), beat_start + int(sr * 0.15))
        segment = y[beat_start:beat_end]
        
        if len(segment) < sr * 0.05:
            continue
        
        # 归一化
        max_amp = np.max(np.abs(segment))
        if max_amp > 0:
            segment = segment / max_amp * 0.8
        
        # 重复10次方便听清楚
        segment_repeated = np.tile(segment, 10)
        
        # 保存
        wav_path = f"{output_dir}/candidate_{i+1}_time_{onset_time:.2f}s.wav"
        sf.write(wav_path, segment_repeated, sr)
        
        duration_sec = len(segment_repeated) / sr
        print(f"候选 {i+1}: 时间位置 {onset_time:.3f}秒 -> {wav_path} ({duration_sec:.1f}秒)")
        
        candidates.append({
            'index': i+1,
            'time': onset_time,
            'path': wav_path
        })
    
    print()
    print("=" * 70)
    print("提取完成！")
    print("=" * 70)
    print()
    print("请播放以下文件，找出哪个是正确的'吐泡泡'音效：")
    print()
    for c in candidates:
        print(f"  候选 {c['index']}: {c['path']}")
    print()
    print("找到正确的候选后，告诉我是哪个编号（如：候选3）")
    print("我会根据你的选择调整算法的评分标准。")
    
    return candidates

if __name__ == "__main__":
    extract_candidates("/home/rui/RunningBPM/test.mp3")

