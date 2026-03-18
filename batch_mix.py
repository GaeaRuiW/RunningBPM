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
    input_path = "/home/rui/RunningBPM/test-bpm/数学王希伟 - 喜欢你.mp3"
    extracted_beat_path = "/home/rui/RunningBPM/extracted_single_beat.wav"
    test_output_path = "/home/rui/RunningBPM/test_metronome_only.mp3"
    music_path = "/home/rui/RunningBPM/music"
    
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
    
    # 获取所有音乐文件
    music_files = [f for f in os.listdir(music_path) if f.endswith(('.mp3', '.flac', '.wav', '.m4a'))]
    nums_music = len(music_files)
    
    print(f"节拍间隔: {beat_interval_ms}ms (对应 {bpm} BPM)")
    print(f"找到 {nums_music} 个音乐文件")
    
    # 使用多线程处理
    import subprocess
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import multiprocessing
    
    # 获取 CPU 核心数
    max_workers = multiprocessing.cpu_count()
    print(f"使用 {max_workers} 个线程并行处理")
    print("=" * 60)
    
    def process_single_music(music_file, index, total):
        """处理单个音乐文件"""
        try:
            print(f"[{index}/{total}] 开始处理: {music_file}")
            
            # 加载音乐
            music_audio = AudioSegment.from_file(os.path.join(music_path, music_file))
            music_length = len(music_audio)
            
            # 创建静音音频
            duration_ms = music_length
            silence = AudioSegment.silent(duration=duration_ms)
            
            # 在静音上叠加节拍
            result = silence
            num_beats = int(duration_ms / beat_interval_ms)
            
            for i in range(num_beats):
                position_ms = i * beat_interval_ms
                if position_ms + len(single_beat) <= duration_ms:
                    result = result.overlay(single_beat, position=position_ms)
            
            # 保存节拍器音轨（临时文件，每个线程独立）
            temp_metronome_path = f"temp_metronome_{index}.mp3"
            result.export(temp_metronome_path, format="mp3")
            
            # 输出文件名
            output_filename = f"outputs/{"".join(music_file.split(".")[0])}【180 BPM】.mp3"
            
            # 构建 FFmpeg 命令（添加高质量参数）
            music_path_ = os.path.join(music_path, music_file)
            cmd = [
                "ffmpeg", "-y",
                "-i", music_path_,              # 输入0: 音乐
                "-i", temp_metronome_path,      # 输入1: 节拍器
                "-filter_complex", 
                "[1:a]asplit=2[sc][mix];[0:a][sc]sidechaincompress=threshold=0.05:ratio=5:attack=5:release=50[ducked];[ducked][mix]amix=inputs=2:duration=first:dropout_transition=0[out]",
                "-map", "[out]",
                "-codec:a", "libmp3lame",       # 使用 LAME MP3 编码器
                "-b:a", "320k",                 # 比特率 320kbps（高质量）
                "-q:a", "0",                    # 质量设置为最高
                output_filename
            ]
            
            # 执行 FFmpeg
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 清理临时文件
            if os.path.exists(temp_metronome_path):
                os.remove(temp_metronome_path)
            
            print(f"[{index}/{total}] ✓ 完成: {output_filename}")
            return (True, music_file, output_filename)
            
        except Exception as e:
            print(f"[{index}/{total}] ✗ 失败: {music_file} - {str(e)}")
            # 清理临时文件
            temp_metronome_path = f"temp_metronome_{index}.mp3"
            if os.path.exists(temp_metronome_path):
                os.remove(temp_metronome_path)
            return (False, music_file, str(e))
    
    # 使用线程池并行处理
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(process_single_music, music_file, i+1, nums_music): music_file 
            for i, music_file in enumerate(music_files)
        }
        
        # 等待任务完成
        for future in as_completed(futures):
            success, music_file, result = future.result()
            if success:
                success_count += 1
            else:
                failed_count += 1
    
    # 输出统计
    print()
    print("=" * 60)
    print("批量处理完成!")
    print("=" * 60)
    print(f"总计: {nums_music} 个文件")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print("=" * 60)

if __name__ == "__main__":
    main()
