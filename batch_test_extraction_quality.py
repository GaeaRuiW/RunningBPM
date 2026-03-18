#!/usr/bin/env python3
"""
批量测试节拍器提取质量
测试 test-bpm 目录下的所有音频文件，建立质量基准
"""

import sys
import os
import numpy as np
import librosa
from pathlib import Path
import json

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.audio_service import AudioService
from pydub import AudioSegment

def analyze_beat_quality(beat_audio_segment):
    """分析提取的节拍音频质量"""
    # 转换为numpy数组
    samples = np.array(beat_audio_segment.get_array_of_samples())
    if beat_audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = np.mean(samples, axis=1)
    
    # 归一化
    samples = samples.astype(np.float32) / (2**15)
    
    sr = beat_audio_segment.frame_rate
    
    # 计算频谱
    stft = librosa.stft(samples, n_fft=2048, hop_length=512)
    magnitude = np.abs(stft)
    freq_hz = librosa.fft_frequencies(sr=sr, n_fft=2048)
    
    # 分析频段能量分布
    avg_magnitude = np.mean(magnitude, axis=1)
    total_energy = np.sum(avg_magnitude)
    
    freq_bands = {
        "低频": (50, 200),
        "气泡声": (200, 800),
        "中频": (800, 2000),
        "高频": (2000, 8000),
        "超高频": (8000, 20000),
    }
    
    band_percentages = {}
    for band_name, (low, high) in freq_bands.items():
        low_idx = np.argmin(np.abs(freq_hz - low))
        high_idx = np.argmin(np.abs(freq_hz - high))
        band_energy = np.sum(avg_magnitude[low_idx:high_idx])
        percentage = (band_energy / total_energy) * 100 if total_energy > 0 else 0
        band_percentages[band_name] = percentage
    
    # 找出主导频段
    dominant_band = max(band_percentages.items(), key=lambda x: x[1])
    
    # 计算质量指标
    # 1. 气泡声占比（节拍器的典型特征）
    bubble_score = band_percentages["气泡声"]
    
    # 2. 噪音指标（超高频不应该太高）
    noise_score = 100 - band_percentages["超高频"]
    
    # 3. 能量集中度（主导频段应该足够强）
    concentration_score = dominant_band[1]
    
    # 综合质量分数
    quality_score = (bubble_score * 0.4 + noise_score * 0.3 + concentration_score * 0.3)
    
    return {
        "band_percentages": band_percentages,
        "dominant_band": dominant_band[0],
        "dominant_percentage": dominant_band[1],
        "bubble_percentage": band_percentages["气泡声"],
        "noise_percentage": band_percentages["超高频"],
        "quality_score": quality_score,
        "duration_ms": len(beat_audio_segment)
    }

def test_single_file(audio_path, audio_service, output_dir):
    """测试单个文件的提取质量"""
    filename = os.path.basename(audio_path)
    print(f"\n{'='*70}")
    print(f"测试文件: {filename}")
    print(f"{'='*70}")
    
    result = {
        "filename": filename,
        "success": False,
        "error": None,
        "quality": None
    }
    
    # 创建输出路径
    output_beat_path = os.path.join(output_dir, f"beat_{filename}.wav")
    
    try:
        # 进度回调
        def progress_callback(progress, message):
            if progress % 10 == 0 or "✓" in message or "⚠" in message:
                print(f"  [{progress:3d}%] {message}")
        
        # 提取节拍
        print("  开始提取节拍...")
        beat = audio_service._extract_single_beat(audio_path, progress_callback)
        
        # 保存
        beat.export(output_beat_path, format="wav")
        print(f"  ✓ 节拍已保存到: {output_beat_path}")
        
        # 分析质量
        quality = analyze_beat_quality(beat)
        
        print(f"\n  质量分析:")
        print(f"    时长: {quality['duration_ms']}ms")
        print(f"    主导频段: {quality['dominant_band']} ({quality['dominant_percentage']:.1f}%)")
        print(f"    气泡声占比: {quality['bubble_percentage']:.1f}%")
        print(f"    噪音水平: {quality['noise_percentage']:.1f}%")
        print(f"    质量评分: {quality['quality_score']:.1f}/100")
        
        # 频段分布
        print(f"\n  频段分布:")
        for band, pct in quality['band_percentages'].items():
            bar = '█' * int(pct / 2)
            print(f"    {band:8s}: {pct:5.1f}% {bar}")
        
        # 质量判断
        if quality['quality_score'] >= 70:
            status = "✓ 优秀"
        elif quality['quality_score'] >= 50:
            status = "○ 良好"
        elif quality['quality_score'] >= 30:
            status = "△ 一般"
        else:
            status = "✗ 较差"
        
        print(f"\n  提取质量: {status}")
        
        result["success"] = True
        result["quality"] = quality
        result["output_path"] = output_beat_path
        result["status"] = status
        
    except Exception as e:
        print(f"  ✗ 提取失败: {str(e)}")
        result["error"] = str(e)
    
    return result

def main():
    test_dir = "/home/rui/RunningBPM/test-bpm"
    output_dir = "/home/rui/RunningBPM/extraction_baseline"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找所有音频文件
    audio_files = []
    for ext in ['*.mp3', '*.flac', '*.wav']:
        audio_files.extend(Path(test_dir).glob(ext))
    
    audio_files = sorted(audio_files)
    
    print(f"{'='*70}")
    print(f"节拍器提取质量批量测试")
    print(f"{'='*70}")
    print(f"测试目录: {test_dir}")
    print(f"输出目录: {output_dir}")
    print(f"找到 {len(audio_files)} 个音频文件")
    print(f"{'='*70}")
    
    # 创建服务
    audio_service = AudioService()
    
    # 测试所有文件
    results = []
    for audio_path in audio_files:
        result = test_single_file(str(audio_path), audio_service, output_dir)
        results.append(result)
    
    # 统计汇总
    print(f"\n{'='*70}")
    print(f"测试汇总")
    print(f"{'='*70}\n")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"成功: {success_count}/{len(results)}")
    
    if success_count > 0:
        print(f"\n质量评分排名:")
        successful_results = [r for r in results if r["success"]]
        successful_results.sort(key=lambda r: r["quality"]["quality_score"], reverse=True)
        
        for i, r in enumerate(successful_results, 1):
            score = r["quality"]["quality_score"]
            bubble = r["quality"]["bubble_percentage"]
            print(f"  {i}. {r['filename']:40s} - {r['status']} (分数: {score:.1f}, 气泡声: {bubble:.1f}%)")
    
    # 保存结果到JSON
    json_path = os.path.join(output_dir, "baseline_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {json_path}")
    print(f"\n{'='*70}")
    print("建议:")
    print("  1. 播放评分较低的文件，确认提取质量")
    print("  2. 这些结果将作为改进前的基准")
    print("  3. 改进后重新运行此脚本，对比结果")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
