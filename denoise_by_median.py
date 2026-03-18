#!/usr/bin/env python3
"""
通过多个片段的中位数滤波去除杂音，生成纯净的节拍器音效
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import librosa
import numpy as np
from scipy import signal
import soundfile as sf
from pydub import AudioSegment

def align_segments(segments, sr):
    """对齐多个音频片段（基于互相关）"""
    if len(segments) == 0:
        return segments
    
    # 使用第一个片段作为参考
    reference = segments[0]
    aligned_segments = [reference]
    
    for seg in segments[1:]:
        # 计算互相关找到最佳对齐位置
        correlation = np.correlate(reference, seg, mode='full')
        lag = np.argmax(correlation) - (len(reference) - 1)
        
        # 对齐片段
        if lag > 0:
            # seg需要向后移
            aligned = np.pad(seg, (lag, 0), mode='constant')[:len(reference)]
        elif lag < 0:
            # seg需要向前移
            aligned = np.pad(seg, (0, -lag), mode='constant')[-lag:-lag+len(reference)]
        else:
            aligned = seg
        
        # 确保长度一致
        if len(aligned) > len(reference):
            aligned = aligned[:len(reference)]
        elif len(aligned) < len(reference):
            aligned = np.pad(aligned, (0, len(reference) - len(aligned)), mode='constant')
        
        aligned_segments.append(aligned)
    
    return aligned_segments

def denoise_by_median(audio_path, candidate_indices, output_dir="/home/rui/RunningBPM"):
    """
    通过中位数滤波去除杂音
    
    Args:
        audio_path: 音频文件路径
        candidate_indices: 好的候选片段的索引列表（如[8, 10]表示候选8和候选10）
    """
    print("=" * 70)
    print("通过多片段中位数滤波去除杂音")
    print("=" * 70)
    print(f"输入文件: {audio_path}")
    print(f"使用候选片段: {candidate_indices}")
    print()
    
    # 加载音频
    print("加载音频...")
    y, sr = librosa.load(audio_path, sr=44100, duration=30.0)
    print(f"采样率: {sr} Hz")
    print()
    
    # 检测所有节拍点
    print("检测节拍点...")
    hop_length = 512
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, units='frames', hop_length=hop_length,
        backtrack=True, delta=0.1, wait=8
    )
    
    print(f"检测到 {len(onset_frames)} 个节拍点")
    print()
    
    # 提取所有节拍片段
    print("提取所有节拍片段...")
    all_segments = []
    
    for i, onset_frame in enumerate(onset_frames):
        onset_sample = int(onset_frame * hop_length)
        
        # 提取150ms的片段
        beat_start = max(0, onset_sample - int(sr * 0.05))
        beat_end = min(len(y), beat_start + int(sr * 0.15))
        segment = y[beat_start:beat_end]
        
        if len(segment) >= sr * 0.10:  # 至少100ms
            # 归一化
            max_amp = np.max(np.abs(segment))
            if max_amp > 0:
                segment = segment / max_amp
            all_segments.append(segment)
    
    print(f"提取了 {len(all_segments)} 个有效片段")
    print()
    
    # 对齐所有片段
    print("对齐所有片段...")
    # 首先统一长度（使用最短的长度）
    min_length = min(len(seg) for seg in all_segments)
    all_segments = [seg[:min_length] for seg in all_segments]
    
    # 使用动态时间规整(DTW)或简单的互相关对齐
    print("使用互相关对齐片段...")
    aligned_segments = align_segments(all_segments, sr)
    
    print(f"对齐完成，片段长度: {len(aligned_segments[0])} 样本 ({len(aligned_segments[0])/sr*1000:.0f}ms)")
    print()
    
    # 方法1: 中位数滤波（去除异常值）
    print("方法1: 中位数滤波...")
    segments_matrix = np.array(aligned_segments)
    median_signal = np.median(segments_matrix, axis=0)
    
    # 归一化
    max_amp = np.max(np.abs(median_signal))
    if max_amp > 0:
        median_signal = median_signal / max_amp * 0.8
    
    # 保存中位数滤波版本
    median_repeated = np.tile(median_signal, 10)
    median_path = f"{output_dir}/denoised_median.wav"
    sf.write(median_path, median_repeated, sr)
    print(f"✓ 中位数滤波版本: {median_path}")
    print()
    
    # 方法2: 加权平均（使用前20%最相似的片段）
    print("方法2: 加权平均（选择最相似的片段）...")
    
    # 计算参考信号（中位数）
    reference = median_signal
    
    # 计算每个片段与参考的相似度
    similarities = []
    for seg in aligned_segments:
        # 使用归一化互相关作为相似度
        corr = np.corrcoef(reference, seg)[0, 1]
        if not np.isnan(corr):
            similarities.append(corr)
        else:
            similarities.append(0)
    
    # 选择相似度最高的20%片段
    n_select = max(3, int(len(similarities) * 0.2))
    top_indices = np.argsort(similarities)[-n_select:]
    
    print(f"选择相似度最高的 {n_select} 个片段（总共{len(similarities)}个）")
    print(f"选择的片段相似度: {[similarities[i] for i in top_indices[-5:]]}")
    
    # 对选中的片段进行平均
    selected_segments = [aligned_segments[i] for i in top_indices]
    weighted_signal = np.mean(selected_segments, axis=0)
    
    # 归一化
    max_amp = np.max(np.abs(weighted_signal))
    if max_amp > 0:
        weighted_signal = weighted_signal / max_amp * 0.8
    
    # 保存加权平均版本
    weighted_repeated = np.tile(weighted_signal, 10)
    weighted_path = f"{output_dir}/denoised_weighted.wav"
    sf.write(weighted_path, weighted_repeated, sr)
    print(f"✓ 加权平均版本: {weighted_path}")
    print()
    
    # 方法3: 软阈值降噪（在频域）
    print("方法3: 频域软阈值降噪...")
    
    # 对中位数信号应用频域降噪
    # 计算STFT
    n_fft = 2048
    stft = librosa.stft(median_signal, n_fft=n_fft, hop_length=256)
    magnitude = np.abs(stft)
    phase = np.angle(stft)
    
    # 估计噪声（使用幅度的低百分位数）
    noise_floor = np.percentile(magnitude, 20, axis=1, keepdims=True)
    
    # 软阈值
    threshold = noise_floor * 2.0
    magnitude_denoised = np.maximum(magnitude - threshold, 0)
    
    # 重建信号
    stft_denoised = magnitude_denoised * np.exp(1j * phase)
    freq_denoised = librosa.istft(stft_denoised, hop_length=256)
    
    # 归一化
    max_amp = np.max(np.abs(freq_denoised))
    if max_amp > 0:
        freq_denoised = freq_denoised / max_amp * 0.8
    
    # 保存频域降噪版本
    freq_repeated = np.tile(freq_denoised, 10)
    freq_path = f"{output_dir}/denoised_frequency.wav"
    sf.write(freq_path, freq_repeated, sr)
    print(f"✓ 频域降噪版本: {freq_path}")
    print()
    
    # 生成测试MP3（使用加权平均版本）
    print("生成测试MP3文件...")
    test_output_path = f"{output_dir}/denoised_test.mp3"
    
    # 创建10秒的测试音频
    silence = AudioSegment.silent(duration=10000)
    beat_audio = AudioSegment.from_file(weighted_path)
    
    # 按180 BPM放置节拍
    beat_interval_ms = int(60000 / 180)
    num_beats = int(10000 / beat_interval_ms)
    
    result = silence
    for i in range(num_beats):
        position_ms = i * beat_interval_ms
        if position_ms + len(beat_audio) <= 10000:
            result = result.overlay(beat_audio, position=position_ms)
    
    result.export(test_output_path, format="mp3")
    print(f"✓ 测试MP3: {test_output_path}")
    print()
    
    print("=" * 70)
    print("降噪完成！")
    print("=" * 70)
    print()
    print("生成了3个降噪版本，请播放对比：")
    print(f"  1. 中位数滤波: {median_path}")
    print(f"  2. 加权平均（最相似片段）: {weighted_path}")
    print(f"  3. 频域降噪: {freq_path}")
    print()
    print(f"测试文件: {test_output_path}")
    print()
    print("告诉我哪个版本最好，或者需要调整参数！")

if __name__ == "__main__":
    # 基于用户反馈，候选8和10是相对好的
    # 但我们会使用所有片段进行统计分析
    denoise_by_median("/home/rui/RunningBPM/test.mp3", candidate_indices=[8, 10])

