#!/usr/bin/env python3
"""
详细调试节拍器提取
分析test.mp3前10秒的音频特征
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import librosa
import numpy as np
from pydub import AudioSegment
from scipy import signal
import soundfile as sf

def analyze_audio(audio_path, output_dir="/home/rui/RunningBPM"):
    """详细分析音频并提取多个候选节拍"""
    print("=" * 70)
    print("详细调试节拍器提取")
    print("=" * 70)
    print(f"输入文件: {audio_path}")
    print()
    
    # 加载音频（只分析前10秒）
    print("加载音频前10秒...")
    y, sr = librosa.load(audio_path, sr=44100, duration=10.0)
    duration = len(y) / sr
    print(f"采样率: {sr} Hz")
    print(f"时长: {duration:.2f} 秒")
    print(f"样本数: {len(y)}")
    print()
    
    # 计算STFT和能量
    print("计算频谱特征...")
    hop_length = 512
    n_fft = 2048
    stft = librosa.stft(y, hop_length=hop_length, n_fft=n_fft)
    magnitude = np.abs(stft)
    freq_hz = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    
    # 计算不同频段的能量
    bubble_low_idx = np.argmin(np.abs(freq_hz - 200))
    bubble_high_idx = np.argmin(np.abs(freq_hz - 800))
    bubble_energy = np.sum(magnitude[bubble_low_idx:bubble_high_idx, :], axis=0)
    
    mid_low_idx = np.argmin(np.abs(freq_hz - 300))
    mid_high_idx = np.argmin(np.abs(freq_hz - 2000))
    mid_energy = np.sum(magnitude[mid_low_idx:mid_high_idx, :], axis=0)
    
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
    
    print(f"气泡频段能量 (200-800Hz): 平均 {np.mean(bubble_energy):.2f}, 最大 {np.max(bubble_energy):.2f}")
    print(f"中频能量 (300-2000Hz): 平均 {np.mean(mid_energy):.2f}, 最大 {np.max(mid_energy):.2f}")
    print(f"RMS能量: 平均 {np.mean(rms):.4f}, 最大 {np.max(rms):.4f}")
    print()
    
    # 使用onset检测找到所有节拍点
    print("检测所有节拍点...")
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, units='frames', hop_length=hop_length,
        backtrack=True, delta=0.1, wait=8
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
    
    print(f"检测到 {len(onset_frames)} 个节拍点")
    if len(onset_frames) > 0:
        print(f"前10个节拍点的时间位置（秒）:")
        for i, t in enumerate(onset_times[:10]):
            frame_idx = onset_frames[i]
            bubble_val = bubble_energy[frame_idx] if frame_idx < len(bubble_energy) else 0
            mid_val = mid_energy[frame_idx] if frame_idx < len(mid_energy) else 0
            rms_val = rms[frame_idx] if frame_idx < len(rms) else 0
            print(f"  {i+1:2d}. {t:6.3f}s - 气泡能量:{bubble_val:8.1f}, 中频:{mid_val:8.1f}, RMS:{rms_val:.4f}")
    print()
    
    # 提取前5个节拍点附近的音频片段
    print("提取前5个节拍点附近的音频片段（各提取3种版本）...")
    print("-" * 70)
    
    for i in range(min(5, len(onset_frames))):
        onset_frame = onset_frames[i]
        onset_sample = int(onset_frame * hop_length)
        onset_time = onset_times[i]
        
        print(f"\n节拍点 {i+1}: {onset_time:.3f}秒 (样本 {onset_sample})")
        
        # 提取300ms的音频片段
        duration_samples = int(sr * 0.3)
        start_sample = max(0, onset_sample - int(sr * 0.05))  # 向前50ms
        end_sample = min(len(y), start_sample + duration_samples)
        
        segment = y[start_sample:end_sample]
        
        if len(segment) == 0:
            print("  跳过（片段为空）")
            continue
        
        # 版本1: 原始音频（无滤波）
        segment_orig = segment.copy()
        max_amp = np.max(np.abs(segment_orig))
        if max_amp > 0:
            segment_orig = segment_orig / max_amp * 0.8
        
        # 重复10次，方便听清楚
        segment_orig_repeated = np.tile(segment_orig, 10)
        
        wav_path_orig = f"{output_dir}/beat_{i+1}_original.wav"
        sf.write(wav_path_orig, segment_orig_repeated, sr)
        duration_sec = len(segment_orig_repeated) / sr
        print(f"  ✓ 原始版本（重复10次，{duration_sec:.1f}秒）: {wav_path_orig}")
        
        # 版本2: 气泡频段滤波 (200-800Hz)
        nyquist = sr / 2
        low = 200 / nyquist
        high = 800 / nyquist
        b, a = signal.butter(4, [low, high], btype='band')
        segment_bubble = signal.filtfilt(b, a, segment)
        max_amp = np.max(np.abs(segment_bubble))
        if max_amp > 0:
            segment_bubble = segment_bubble / max_amp * 0.8
        
        # 重复10次
        segment_bubble_repeated = np.tile(segment_bubble, 10)
        
        wav_path_bubble = f"{output_dir}/beat_{i+1}_bubble_filtered.wav"
        sf.write(wav_path_bubble, segment_bubble_repeated, sr)
        print(f"  ✓ 气泡滤波版本（重复10次，{duration_sec:.1f}秒）: {wav_path_bubble}")
        
        # 版本3: 混合版本 (60%原始 + 40%滤波) - 当前算法使用的
        segment_mixed = segment * 0.6 + segment_bubble * 0.4
        max_amp = np.max(np.abs(segment_mixed))
        if max_amp > 0:
            segment_mixed = segment_mixed / max_amp * 0.8
        
        # 重复10次
        segment_mixed_repeated = np.tile(segment_mixed, 10)
        
        wav_path_mixed = f"{output_dir}/beat_{i+1}_mixed.wav"
        sf.write(wav_path_mixed, segment_mixed_repeated, sr)
        print(f"  ✓ 混合版本（重复10次，{duration_sec:.1f}秒）: {wav_path_mixed}")
    
    print()
    print("=" * 70)
    print("调试完成!")
    print("=" * 70)
    print()
    print("请播放生成的文件，找出哪个版本最接近'吐泡泡'音效：")
    print()
    for i in range(min(5, len(onset_frames))):
        print(f"节拍点 {i+1}:")
        print(f"  - beat_{i+1}_original.wav (原始)")
        print(f"  - beat_{i+1}_bubble_filtered.wav (气泡滤波)")
        print(f"  - beat_{i+1}_mixed.wav (混合)")
        print()
    print("然后告诉我：")
    print("1. 哪个节拍点位置正确？")
    print("2. 哪个版本的音效最好？")

if __name__ == "__main__":
    analyze_audio("/home/rui/RunningBPM/test.mp3")

