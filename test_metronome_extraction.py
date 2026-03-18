#!/usr/bin/env python3
"""
测试节拍器提取算法
提取test.mp3中的节拍器，并生成一个只包含节拍器的测试文件
"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.audio_service import AudioService
from pydub import AudioSegment

def progress_callback(progress, message):
    """进度回调"""
    print(f"[{progress:3d}%] {message}")

def main():
    # 输入输出路径
    input_path = "/home/rui/RunningBPM/test-bpm/曾经的你.mp3"
    extracted_beat_path = "/home/rui/RunningBPM/extracted_single_beat.wav"
    test_output_path = "/home/rui/RunningBPM/test_metronome_only.mp3"
    music_path = "/home/rui/RunningBPM/Energy.flac"
    
    print("=" * 60)
    print("测试节拍器提取算法")
    print("=" * 60)
    print(f"输入文件: {input_path}")
    print(f"提取的单个节拍: {extracted_beat_path}")
    print(f"测试输出文件: {test_output_path}")
    print("=" * 60)
    print()
    
    # 创建服务实例
    audio_service = AudioService()
    
    # 提取单个节拍
    print("步骤1: 从test.mp3中提取单个节拍...")
    print("-" * 60)
    single_beat = audio_service._extract_single_beat(input_path, progress_callback)
    
    # 保存单个节拍
    print()
    print(f"单个节拍长度: {len(single_beat)}ms")
    print(f"保存单个节拍到: {extracted_beat_path}")
    
    # 增强节拍音量 (+6dB)
    print("增强节拍音量 (+6dB)...")
    single_beat = single_beat + 3
    
    single_beat.export(extracted_beat_path, format="wav")
    print("✓ 单个节拍已保存")
    print()
    
    # 生成测试文件：重复播放10次这个节拍，按照180 BPM的间隔
    print("步骤2: 生成测试文件（重复10次节拍，180 BPM）...")
    print("-" * 60)
    
    # 计算节拍间隔（180 BPM = 333ms间隔）
    bpm = 180
    beat_interval_ms = int(60000 / bpm)
    print(f"节拍间隔: {beat_interval_ms}ms (对应 {bpm} BPM)")
    music_audio = AudioSegment.from_file(music_path)
    music_length = len(music_audio)
    # 创建10秒的静音音频
    duration_ms = music_length
    silence = AudioSegment.silent(duration=duration_ms)
    
    # 在静音上叠加节拍
    result = silence
    num_beats = int(duration_ms / beat_interval_ms)
    print(f"将放置 {num_beats} 个节拍")
    
    
    for i in range(num_beats):
        position_ms = i * beat_interval_ms
        if position_ms + len(single_beat) <= duration_ms:
            result = result.overlay(single_beat, position=position_ms)
            # print(f"  放置节拍 {i+1}/{num_beats} 在位置 {position_ms}ms")
            if (i+1) % 50 == 0:
                print(f"  放置节拍 {i+1}/{num_beats} 在位置 {position_ms}ms")
    # 保存测试文件（节拍器音轨）
    print()
    print(f"保存节拍器音轨到: {test_output_path}")
    result.export(test_output_path, format="mp3")
    print("✓ 节拍器音轨已保存")
    print()

    print("步骤3: 使用 FFmpeg 进行专业侧链压缩 (Sidechain Compression)...")
    print("-" * 60)
    
    output_filename = "Energy_with_metronome_ffmpeg_ducking.mp3"
    
    import subprocess
    
    # 构建 FFmpeg 命令
    # 解释:
    # [1:a]asplit=2[sc][mix]: 将输入1(节拍器)分为两路，一路[sc]作为侧链控制信号，一路[mix]用于最后混合
    # [0:a][sc]sidechaincompress...: 使用[sc]控制[0:a](音乐)的音量。
    #    threshold=0.05: 触发阈值，越小越灵敏
    #    ratio=5: 压缩比，越大压得越狠
    #    attack=5: 起始时间(ms)，越快压得越快
    #    release=50: 释放时间(ms)，越短恢复越快
    # [ducked][mix]amix...: 将压限后的音乐[ducked]和原始节拍器[mix]混合
    
    cmd = [
        "ffmpeg", "-y",
        "-i", music_path,          # 输入0: 音乐
        "-i", test_output_path,    # 输入1: 节拍器
        "-filter_complex", 
        "[1:a]asplit=2[sc][mix];[0:a][sc]sidechaincompress=threshold=0.05:ratio=5:attack=5:release=50[ducked];[ducked][mix]amix=inputs=2:duration=first:dropout_transition=0[out]",
        "-map", "[out]",
        "-codec:a", "libmp3lame",   # 使用 LAME MP3 编码器
        "-b:a", "320k",             # 设置比特率为 320kbps（高质量）
        "-q:a", "0",                # 质量设置为最高
        output_filename
    ]
    
    print("执行命令:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ 混合完成: {output_filename}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg 执行失败: {e}")

    # final_mix.export("Energy_with_metronome_refined_ducking.mp3", format="mp3")
    # final_mix.export("Energy_with_metronome_ducking.mp3", format="mp3")
    # 保存测试文件
    print("=" * 60)
    print("测试完成!")
    print("=" * 60)
    print()
    print("请播放以下文件来验证提取的节拍器音效:")
    print(f"  1. 单个节拍: {extracted_beat_path}")
    print(f"  2. 测试节拍器: {test_output_path}")
    print(f"  3. 最终混合: {output_filename}")
    print()
    print("如果提取的节拍器不是'吐泡泡'音效，请告诉我具体是什么声音。")

if __name__ == "__main__":
    main()

