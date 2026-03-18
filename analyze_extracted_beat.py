#!/usr/bin/env python3
"""
诊断工具：分析提取的单个节拍音频
检查提取的节拍器音效是否正确
"""

import sys
import os
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pydub import AudioSegment

def analyze_beat(beat_path):
    """分析单个节拍音频"""
    print(f"\n{'='*60}")
    print(f"分析提取的节拍: {beat_path}")
    print(f"{'='*60}\n")
    
    # 加载音频
    y, sr = librosa.load(beat_path, sr=44100)
    duration = len(y) / sr
    
    print(f"基本信息:")
    print(f"  时长: {duration*1000:.1f}ms")
    print(f"  采样率: {sr}Hz")
    print(f"  样本数: {len(y)}")
    
    # 计算能量
    rms = np.sqrt(np.mean(y**2))
    db = 20 * np.log10(rms + 1e-10)
    print(f"\n能量分析:")
    print(f"  RMS: {rms:.6f}")
    print(f"  dB: {db:.2f}")
    print(f"  Max: {np.max(np.abs(y)):.6f}")
    
    # 频谱分析
    stft = librosa.stft(y, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    freq_hz = librosa.fft_frequencies(sr=sr, n_fft=2048)
    
    # 计算不同频段的能量占比
    avg_magnitude = np.mean(magnitude, axis=1)
    total_energy = np.sum(avg_magnitude)
    
    # 定义频段
    freq_bands = {
        "低频 (50-200Hz)": (50, 200),
        "气泡声 (200-800Hz)": (200, 800),
        "中频 (800-2kHz)": (800, 2000),
        "高频 (2k-8kHz)": (2000, 8000),
        "超高频 (8k-20kHz)": (8000, 20000),
    }
    
    print(f"\n频谱分析:")
    for band_name, (low, high) in freq_bands.items():
        low_idx = np.argmin(np.abs(freq_hz - low))
        high_idx = np.argmin(np.abs(freq_hz - high))
        band_energy = np.sum(avg_magnitude[low_idx:high_idx])
        percentage = (band_energy / total_energy) * 100 if total_energy > 0 else 0
        print(f"  {band_name}: {percentage:.1f}%")
    
    # 找出主要频率
    dominant_freq_idx = np.argmax(avg_magnitude)
    dominant_freq = freq_hz[dominant_freq_idx]
    print(f"\n主要频率: {dominant_freq:.1f}Hz")
    
    # 频谱质心
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    avg_centroid = np.mean(spectral_centroid)
    print(f"频谱质心: {avg_centroid:.1f}Hz")
    
    # 判断音效类型
    print(f"\n音效类型判断:")
    bubble_energy = 0
    high_energy = 0
    for band_name, (low, high) in freq_bands.items():
        low_idx = np.argmin(np.abs(freq_hz - low))
        high_idx = np.argmin(np.abs(freq_hz - high))
        band_energy = np.sum(avg_magnitude[low_idx:high_idx])
        percentage = (band_energy / total_energy) * 100 if total_energy > 0 else 0
        
        if "气泡" in band_name:
            bubble_energy = percentage
        elif "高频" in band_name or "超高频" in band_name:
            high_energy = percentage
    
    if bubble_energy > 40:
        print(f"  ✓ 很可能是气泡声/吐泡泡音效 (气泡频段能量: {bubble_energy:.1f}%)")
    elif high_energy > 40:
        print(f"  ✗ 很可能是'哒哒哒'声或其他高频音效 (高频能量: {high_energy:.1f}%)")
    elif avg_centroid < 1000:
        print(f"  ? 低频音效 (频谱质心: {avg_centroid:.1f}Hz)")
    else:
        print(f"  ? 未知类型音效")
    
    # 检查是否有明显的音调
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = []
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch = pitches[index, t]
        if pitch > 0:
            pitch_values.append(pitch)
    
    if len(pitch_values) > 0:
        avg_pitch = np.mean(pitch_values)
        print(f"\n音调信息:")
        print(f"  检测到的平均音高: {avg_pitch:.1f}Hz")
        if avg_pitch < 400:
            print(f"  → 低音调")
        elif avg_pitch < 1000:
            print(f"  → 中音调")
        else:
            print(f"  → 高音调")

def main():
    beat_path = "/home/rui/RunningBPM/extracted_single_beat.wav"
    
    if not os.path.exists(beat_path):
        print(f"错误: 文件不存在 {beat_path}")
        print(f"请先运行 test_metronome_extraction.py")
        return
    
    analyze_beat(beat_path)
    
    print(f"\n{'='*60}")
    print("建议:")
    print("  1. 播放 extracted_single_beat.wav 确认音效")
    print("  2. 如果不是'吐泡泡'音效，可能是提取算法选择了错误的频段")
    print("  3. 检查源文件中节拍器的实际音效特征")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
