#!/usr/bin/env python3
"""
对比分析：原始音频 vs 提取的节拍
帮助识别提取过程中丢失了什么
"""

import sys
import os
import numpy as np
import librosa
from scipy import signal

def analyze_source_metronome(source_path, duration=5.0):
    """分析源文件中的节拍器特征"""
    print(f"\n{'='*60}")
    print(f"分析源文件: {os.path.basename(source_path)}")
    print(f"{'='*60}\n")
    
    # 加载前几秒
    y, sr = librosa.load(source_path, sr=44100, duration=duration)
    
    # 计算STFT
    stft = librosa.stft(y, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    freq_hz = librosa.fft_frequencies(sr=sr, n_fft=2048)
    
    # 分析不同频段
    freq_bands = {
        "低频 (50-200Hz)": (50, 200),
        "气泡声 (200-800Hz)": (200, 800),
        "中频 (800-2kHz)": (800, 2000),
        "高频 (2k-8kHz)": (2000, 8000),
        "超高频 (8k-20kHz)": (8000, 20000),
    }
    
    print("整体频谱分布:")
    avg_magnitude = np.mean(magnitude, axis=1)
    total_energy = np.sum(avg_magnitude)
    
    for band_name, (low, high) in freq_bands.items():
        low_idx = np.argmin(np.abs(freq_hz - low))
        high_idx = np.argmin(np.abs(freq_hz - high))
        band_energy = np.sum(avg_magnitude[low_idx:high_idx])
        percentage = (band_energy / total_energy) * 100 if total_energy > 0 else 0
        bar = '█' * int(percentage / 2)
        print(f"  {band_name:25s}: {percentage:5.1f}% {bar}")
    
    # 检测节拍位置
    print(f"\n检测节拍位置...")
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='frames', hop_length=512)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
    
    if len(onset_times) > 1:
        intervals = np.diff(onset_times)
        avg_interval = np.mean(intervals)
        bpm = 60 / avg_interval if avg_interval > 0 else 0
        print(f"  检测到 {len(onset_times)} 个节拍")
        print(f"  平均间隔: {avg_interval:.3f}秒")
        print(f"  估计BPM: {bpm:.1f}")
    
    # 分析第一个节拍的频谱
    if len(onset_frames) > 0:
        first_onset = onset_frames[0]
        # 提取第一个节拍附近的频谱 (±10帧)
        start_frame = max(0, first_onset - 2)
        end_frame = min(magnitude.shape[1], first_onset + 10)
        beat_spectrum = np.mean(magnitude[:, start_frame:end_frame], axis=1)
        
        print(f"\n第一个节拍的频谱特征:")
        beat_total = np.sum(beat_spectrum)
        for band_name, (low, high) in freq_bands.items():
            low_idx = np.argmin(np.abs(freq_hz - low))
            high_idx = np.argmin(np.abs(freq_hz - high))
            band_energy = np.sum(beat_spectrum[low_idx:high_idx])
            percentage = (band_energy / beat_total) * 100 if beat_total > 0 else 0
            bar = '█' * int(percentage / 2)
            print(f"  {band_name:25s}: {percentage:5.1f}% {bar}")
        
        # 找出主要频率
        dominant_idx = np.argmax(beat_spectrum)
        dominant_freq = freq_hz[dominant_idx]
        print(f"\n  主要频率: {dominant_freq:.1f}Hz")
        
        # 判断音效类型
        bubble_pct = 0
        high_pct = 0
        for band_name, (low, high) in freq_bands.items():
            low_idx = np.argmin(np.abs(freq_hz - low))
            high_idx = np.argmin(np.abs(freq_hz - high))
            band_energy = np.sum(beat_spectrum[low_idx:high_idx])
            percentage = (band_energy / beat_total) * 100 if beat_total > 0 else 0
            if "气泡" in band_name:
                bubble_pct = percentage
            elif "高频" in band_name or "超高频" in band_name:
                high_pct = percentage
        
        print(f"\n音效类型推断:")
        if bubble_pct > 30:
            print(f"  ✓ 气泡声特征明显 ({bubble_pct:.1f}%)")
        if high_pct > 30:
            print(f"  ✓ 高频特征明显 ({high_pct:.1f}%)")
        if dominant_freq < 500:
            print(f"  ✓ 低频主导")
        
        return {
            'bubble_pct': bubble_pct,
            'high_pct': high_pct,
            'dominant_freq': dominant_freq
        }

def main():
    source_path = "/home/rui/RunningBPM/test-bpm/曾经的你.mp3"
    extracted_path = "/home/rui/RunningBPM/extracted_single_beat.wav"
    
    if not os.path.exists(source_path):
        print(f"错误: 源文件不存在 {source_path}")
        return
    
    # 分析源文件
    source_info = analyze_source_metronome(source_path)
    
    # 分析提取的节拍
    if os.path.exists(extracted_path):
        print(f"\n{'='*60}")
        print(f"分析提取的节拍: {os.path.basename(extracted_path)}")
        print(f"{'='*60}\n")
        
        y, sr = librosa.load(extracted_path, sr=44100)
        stft = librosa.stft(y, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        freq_hz = librosa.fft_frequencies(sr=sr, n_fft=2048)
        
        freq_bands = {
            "低频 (50-200Hz)": (50, 200),
            "气泡声 (200-800Hz)": (200, 800),
            "中频 (800-2kHz)": (800, 2000),
            "高频 (2k-8kHz)": (2000, 8000),
            "超高频 (8k-20kHz)": (8000, 20000),
        }
        
        print("频谱分布:")
        avg_magnitude = np.mean(magnitude, axis=1)
        total_energy = np.sum(avg_magnitude)
        
        for band_name, (low, high) in freq_bands.items():
            low_idx = np.argmin(np.abs(freq_hz - low))
            high_idx = np.argmin(np.abs(freq_hz - high))
            band_energy = np.sum(avg_magnitude[low_idx:high_idx])
            percentage = (band_energy / total_energy) * 100 if total_energy > 0 else 0
            bar = '█' * int(percentage / 2)
            print(f"  {band_name:25s}: {percentage:5.1f}% {bar}")
    
    print(f"\n{'='*60}")
    print("结论:")
    print(f"{'='*60}")
    if source_info:
        if source_info['bubble_pct'] > 30:
            print(f"✓ 源文件中的节拍器主要是气泡声 ({source_info['bubble_pct']:.1f}%)")
            print(f"  建议: 提取算法应该优先选择200-800Hz频段")
        if source_info['high_pct'] > 30:
            print(f"✓ 源文件中的节拍器有高频成分 ({source_info['high_pct']:.1f}%)")
        if source_info['dominant_freq'] < 500:
            print(f"✓ 主要频率在低频段: {source_info['dominant_freq']:.1f}Hz")

if __name__ == "__main__":
    main()
