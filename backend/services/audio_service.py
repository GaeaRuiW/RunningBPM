import librosa
import numpy as np
from pydub import AudioSegment
from scipy import signal
import soundfile as sf
from typing import List, Optional, Callable
import os


class AudioService:
    """音频处理服务"""
    
    def __init__(self):
        self.sample_rate = 44100
    
    def _detect_audio_start_time(self, y: np.ndarray, sr: int) -> tuple:
        """
        检测音频中第一个显著声音的开始时间
        
        Args:
            y: 音频信号数组
            sr: 采样率
            
        Returns:
            (start_time_seconds, confidence)
            - start_time_seconds: 第一个声音的开始时间（秒）
            - confidence: 检测置信度 (0-1)
        """
        # 分析前5秒的音频
        analysis_duration = min(5.0, len(y) / sr)
        analysis_samples = int(analysis_duration * sr)
        y_analysis = y[:analysis_samples]
        
        # 计算RMS能量（使用短窗口以获得更精细的时间分辨率）
        frame_length = int(sr * 0.01)  # 10ms窗口
        hop_length = int(sr * 0.005)   # 5ms步进
        
        rms = librosa.feature.rms(y=y_analysis, frame_length=frame_length, hop_length=hop_length)[0]
        
        # 计算动态阈值
        # 使用音频的能量分布来确定"有声音"的阈值
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # 静音阈值：低于平均值30dB的部分视为静音
        noise_floor = np.percentile(rms_db, 10)  # 使用10百分位作为噪声基线
        threshold_db = noise_floor + 10  # 超过噪声基线10dB即视为有声音
        
        # 找到第一个超过阈值的帧
        start_frame = None
        for i in range(len(rms_db)):
            if rms_db[i] > threshold_db:
                start_frame = i
                break
        
        if start_frame is None:
            # 未检测到声音
            return (0.0, 0.0)
        
        # 转换为时间（秒）
        start_time = start_frame * hop_length / sr
        
        # 计算置信度
        # 基于以下因素：
        # 1. 声音开始后的能量强度
        # 2. 能量上升的陡峭程度
        if start_frame + 10 < len(rms_db):
            initial_energy = np.mean(rms_db[start_frame:start_frame + 10])
            energy_rise = initial_energy - threshold_db
            
            # 置信度：能量上升越多，置信度越高
            confidence = min(energy_rise / 20.0, 1.0)  # 20dB以上视为高置信度
        else:
            confidence = 0.5
        
        return (start_time, confidence)
    
    def _analyze_initial_energy_pattern(self, y: np.ndarray, sr: int) -> dict:
        """
        分析音频开始部分的能量模式，判断是否符合节拍器特征
        
        节拍器特征：
        - 从开始（< 0.2秒）就有声音
        - 前3-5秒有明显的周期性脉冲
        - 能量分布均匀，没有明显的渐强
        
        音乐特征：
        - 开始时间晚（> 0.5秒）
        - 能量逐渐增强（渐入）
        - 周期性不明显或不规则
        
        Args:
            y: 音频信号数组
            sr: 采样率
            
        Returns:
            {
                'has_immediate_sound': bool,  # 是否立即有声音
                'start_time': float,  # 声音开始时间（秒）
                'is_periodic': bool,  # 是否有周期性
                'periodicity_score': float,  # 周期性强度 (0-1)
                'metronome_likelihood': float,  # 节拍器可能性 (0-1)
                'pattern_type': str  # 'metronome', 'music', 'silence', 'unknown'
            }
        """
        # 1. 检测开始时间
        start_time, start_confidence = self._detect_audio_start_time(y, sr)
        
        # 2. 分析前3-5秒的能量模式
        analysis_duration = min(5.0, len(y) / sr)
        analysis_samples = int(analysis_duration * sr)
        y_analysis = y[:analysis_samples]
        
        # 计算能量包络
        hop_length = 512
        n_fft = 2048
        rms = librosa.feature.rms(y=y_analysis, frame_length=n_fft, hop_length=hop_length)[0]
        
        # 3. 检测周期性（使用自相关）
        # 节拍器的BPM范围：60-240
        min_bpm = 60
        max_bpm = 240
        min_period_samples = int(sr * 60 / max_bpm)
        max_period_samples = int(sr * 60 / min_bpm)
        min_period_frames = min_period_samples // hop_length
        max_period_frames = max_period_samples // hop_length
        
        # 归一化RMS
        if np.max(rms) > 0:
            rms_normalized = (rms - np.mean(rms)) / (np.std(rms) + 1e-10)
        else:
            rms_normalized = rms
        
        # 计算自相关
        if len(rms_normalized) >= max_period_frames * 2:
            fft_signal = np.fft.fft(rms_normalized, n=len(rms_normalized) * 2)
            autocorr = np.fft.ifft(fft_signal * np.conj(fft_signal))
            autocorr = np.real(autocorr[:len(rms_normalized)])
            
            if autocorr[0] > 0:
                autocorr_normalized = autocorr / autocorr[0]
            else:
                autocorr_normalized = autocorr
            
            # 在合理范围内查找周期性峰值
            search_range = autocorr_normalized[min_period_frames:min(max_period_frames, len(autocorr_normalized))]
            
            if len(search_range) > 0:
                max_peak = np.max(search_range)
                mean_value = np.mean(search_range)
                periodicity_score = max(0, (max_peak - mean_value) / (1.0 - mean_value + 1e-10))
                periodicity_score = min(periodicity_score, 1.0)
            else:
                periodicity_score = 0.0
        else:
            periodicity_score = 0.0
        
        # 4. 检测能量变化模式（渐强 vs 均匀）
        # 将音频分成多段，检查能量变化趋势
        num_segments = min(10, len(rms) // 10)
        if num_segments >= 3:
            segment_energies = []
            segment_size = len(rms) // num_segments
            for i in range(num_segments):
                start_idx = i * segment_size
                end_idx = (i + 1) * segment_size if i < num_segments - 1 else len(rms)
                segment_energies.append(np.mean(rms[start_idx:end_idx]))
            
            # 计算线性趋势（音乐通常有正趋势，节拍器趋势接近0）
            if len(segment_energies) > 1:
                x = np.arange(len(segment_energies))
                coeffs = np.polyfit(x, segment_energies, 1)
                energy_trend = coeffs[0] / (np.mean(segment_energies) + 1e-10)
            else:
                energy_trend = 0.0
        else:
            energy_trend = 0.0
        
        # 5. 综合判断
        has_immediate_sound = start_time < 0.2
        is_periodic = periodicity_score > 0.5
        
        # 计算节拍器可能性评分
        # 调整权重：周期性是最关键的指标，给予更高权重
        # 权重：周期性(60%) + 开始时间(25%) + 能量均匀性(15%)
        start_time_score = 1.0 if start_time < 0.1 else max(0, 1.0 - start_time / 0.5)
        energy_uniformity_score = max(0, 1.0 - abs(energy_trend) * 10)  # 趋势越接近0，得分越高
        
        metronome_likelihood = (
            periodicity_score * 0.60 +      # 周期性最重要
            start_time_score * 0.25 +       # 开始时间次之
            energy_uniformity_score * 0.15  # 能量均匀性作为辅助
        )
        
        # 判断模式类型
        # 提高阈值，减少误判
        if start_time > 2.0:
            pattern_type = 'silence'
        elif metronome_likelihood > 0.7:  # 提高到70%
            pattern_type = 'metronome'
        elif metronome_likelihood < 0.4:  # 降低到40%
            pattern_type = 'music'
        else:
            pattern_type = 'unknown'
        
        return {
            'has_immediate_sound': has_immediate_sound,
            'start_time': start_time,
            'is_periodic': is_periodic,
            'periodicity_score': periodicity_score,
            'metronome_likelihood': metronome_likelihood,
            'pattern_type': pattern_type,
            'start_confidence': start_confidence,
            'energy_trend': energy_trend
        }
    
    def _verify_metronome_quality(self, y: np.ndarray, sr: int) -> dict:
        """
        验证提取的音频是否是高质量的节拍器
        
        通过分析频段能量分布来判断提取质量
        
        Args:
            y: 音频信号数组
            sr: 采样率
            
        Returns:
            {
                'is_valid': bool,  # 是否通过质量验证
                'bubble_percentage': float,  # 气泡声占比
                'noise_percentage': float,  # 噪音占比
                'quality_score': float,  # 质量评分 (0-100)
                'reason': str  # 验证结果说明
            }
        """
        # 计算频谱
        stft = librosa.stft(y, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        freq_hz = librosa.fft_frequencies(sr=sr, n_fft=2048)
        
        # 计算频段能量
        avg_magnitude = np.mean(magnitude, axis=1)
        total_energy = np.sum(avg_magnitude)
        
        if total_energy == 0:
            return {
                'is_valid': False,
                'bubble_percentage': 0.0,
                'noise_percentage': 0.0,
                'quality_score': 0.0,
                'reason': '音频无能量'
            }
        
        # 定义频段
        freq_bands = {
            'low': (50, 200),      # 低频
            'bubble': (200, 800),  # 气泡声
            'mid': (800, 2000),    # 中频
            'high': (2000, 8000),  # 高频
            'ultra': (8000, 20000) # 超高频
        }
        
        band_energies = {}
        for band_name, (low, high) in freq_bands.items():
            low_idx = np.argmin(np.abs(freq_hz - low))
            high_idx = np.argmin(np.abs(freq_hz - high))
            band_energy = np.sum(avg_magnitude[low_idx:high_idx])
            band_energies[band_name] = (band_energy / total_energy) * 100
        
        bubble_pct = band_energies['bubble']
        noise_pct = band_energies['ultra']
        low_pct = band_energies['low']
        
        # 质量评分计算
        # 气泡声权重最高，噪音和低频越少越好
        quality_score = (
            bubble_pct * 0.5 +                    # 气泡声越多越好
            (100 - noise_pct) * 0.3 +             # 噪音越少越好
            (100 - low_pct) * 0.2                 # 低频越少越好
        )
        
        # 验证标准
        # 至少25%气泡声 AND 噪音<20% AND 低频<30%
        is_valid = (
            bubble_pct >= 25.0 and
            noise_pct < 20.0 and
            low_pct < 30.0
        )
        
        # 生成说明
        if is_valid:
            if bubble_pct >= 70:
                reason = f"优秀: 气泡声{bubble_pct:.1f}%, 噪音{noise_pct:.1f}%"
            elif bubble_pct >= 50:
                reason = f"良好: 气泡声{bubble_pct:.1f}%, 噪音{noise_pct:.1f}%"
            else:
                reason = f"合格: 气泡声{bubble_pct:.1f}%, 噪音{noise_pct:.1f}%"
        else:
            problems = []
            if bubble_pct < 25:
                problems.append(f"气泡声过低({bubble_pct:.1f}%)")
            if noise_pct >= 20:
                problems.append(f"噪音过高({noise_pct:.1f}%)")
            if low_pct >= 30:
                problems.append(f"低频过高({low_pct:.1f}%)")
            reason = "不合格: " + ", ".join(problems)
        
        return {
            'is_valid': is_valid,
            'bubble_percentage': bubble_pct,
            'noise_percentage': noise_pct,
            'low_percentage': low_pct,
            'quality_score': quality_score,
            'reason': reason
        }
    
    def combine_audio(
        self,
        metronome_path: str,
        music_path: str,
        target_bpm: int,
        output_path: str,
        output_format: str = "mp3",
        metronome_volume: int = 0,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        auto_extract_metronome: bool = True
    ):
        """
        合成节拍器和音乐：从节拍器音频中提取单个节拍，然后按照目标BPM间隔放置在音乐中
        
        Args:
            metronome_path: 节拍器音频路径
            music_path: 音乐音频路径
            target_bpm: 目标步频（每分钟步数）
            output_path: 输出文件路径
            output_format: 输出格式（默认 mp3）
            metronome_volume: 节拍器音量调整 (dB)，范围 -20 到 +20，默认 0
            progress_callback: 进度回调函数 (progress, message)
            auto_extract_metronome: 是否自动从节拍器文件中提取节拍器（默认 True）
        """
        if progress_callback:
            progress_callback(5, "加载音乐音频文件...")
        
        # 加载音频
        music_audio = AudioSegment.from_file(music_path)
        music_duration_ms = len(music_audio)
        
        if progress_callback:
            progress_callback(7, f"音乐时长: {music_duration_ms/1000:.1f}秒")
        
        if progress_callback:
            progress_callback(8, "开始分析节拍器音频...")
        
        if auto_extract_metronome:
            # 提取单个节拍（进度从10%到35%）
            def extract_progress_wrapper(progress: int, message: str):
                # 将提取进度映射到10-35%
                mapped_progress = 10 + int(progress * 0.25)
                if progress_callback:
                    progress_callback(mapped_progress, message)
            
            single_beat = self._extract_single_beat(metronome_path, extract_progress_wrapper)
        else:
            # 直接使用上传的节拍器文件
            if progress_callback:
                progress_callback(10, "加载节拍器音频文件...")
            
            single_beat = AudioSegment.from_file(metronome_path)
            
            if progress_callback:
                progress_callback(35, f"节拍器加载完成 (时长: {len(single_beat)}ms)")
        
        if progress_callback:
            progress_callback(36, "节拍提取完成，准备合成...")
        
        # 使用辅助方法生成节拍器轨道
        # 使用辅助方法生成节拍器轨道
        metronome_track = self._generate_metronome_track(
            beat_audio=single_beat,
            target_bpm=target_bpm,
            duration_ms=music_duration_ms,
            progress_callback=progress_callback
        )
        
        # 保存节拍器轨道为临时文件
        import tempfile
        temp_metronome = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_metronome_path = temp_metronome.name
        temp_metronome.close()
        metronome_track.export(temp_metronome_path, format='mp3')
        
        if progress_callback:
            progress_callback(75, "使用FFmpeg进行专业侧链压缩混合...")
        
        # 使用FFmpeg进行sidechain compression
        import subprocess
        
        # 临时输出文件
        temp_output = tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False)
        temp_output_path = temp_output.name
        temp_output.close()
        
        # FFmpeg命令
        # [1:a]asplit=2[sc][mix]: 将节拍器分为两路，一路作为侧链控制信号，一路用于混合
        # [0:a][sc]sidechaincompress: 使用节拍器控制音乐的音量
        # [ducked][mix]amix: 将压缩后的音乐和节拍器混合
        cmd = [
            "ffmpeg", "-y",
            "-i", music_path,           # 输入0: 音乐
            "-i", temp_metronome_path,  # 输入1: 节拍器
            "-filter_complex",
            "[1:a]asplit=2[sc][mix];[0:a][sc]sidechaincompress=threshold=0.05:ratio=5:attack=5:release=50[ducked];[ducked][mix]amix=inputs=2:duration=first:dropout_transition=0[out]",
            "-map", "[out]",
            "-codec:a", "libmp3lame",    # 使用 LAME MP3 编码器
            "-b:a", "320k",              # 设置比特率为 320kbps（高质量）
            "-q:a", "0",                 # 质量设置为最高
            temp_output_path
        ]
        
        if progress_callback:
            progress_callback(80, "执行FFmpeg混合...")
        
        try:
            # 运行FFmpeg (静默模式)
            subprocess.run(cmd, check=True, capture_output=True)
            
            if progress_callback:
                progress_callback(90, "FFmpeg混合完成，转换格式...")
            
            # 如果输出格式不是mp3,需要转换
            if output_format != 'mp3':
                final_audio = AudioSegment.from_file(temp_output_path)
                final_audio.export(output_path, format=output_format)
            else:
                # 直接移动文件
                import shutil
                shutil.move(temp_output_path, output_path)
            
            # 清理临时文件
            for temp_file in [temp_metronome_path, temp_output_path]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            if progress_callback:
                progress_callback(100, "完成！")
                
        except subprocess.CalledProcessError as e:
            # FFmpeg失败，回退到简单混合
            if progress_callback:
                progress_callback(80, "FFmpeg失败，使用简单混合方法...")
            
            # 简单叠加
            combined = music_audio.overlay(metronome_track)
            combined.export(output_path, format=output_format)
            
            # 清理临时文件
            if os.path.exists(temp_metronome_path):
                os.remove(temp_metronome_path)
            
            if progress_callback:
                progress_callback(100, f"完成！共放置 {processed_beats} 个节拍（使用简单混合）")

    
    def _extract_single_beat_with_demucs(
        self,
        metronome_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AudioSegment:
        """
        使用Demucs AI模型从节拍器音频中提取单个节拍
        这是最先进的方法，使用深度学习进行音频源分离
        
        Args:
            metronome_path: 节拍器音频路径
            progress_callback: 进度回调函数
            
        Returns:
            单个节拍的音频段
        """
        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
            import tempfile
            
            if progress_callback:
                progress_callback(5, "加载Demucs AI模型...")
            
            # 使用htdemucs模型（最新最好的）
            model = get_model('htdemucs')
            model.eval()
            
            if progress_callback:
                progress_callback(10, "加载音频文件...")
            
            # 加载音频
            y, sr = librosa.load(metronome_path, sr=self.sample_rate, mono=False, duration=30.0)
            
            # 新增：分析音频开始特征（在处理前先诊断）
            # 转换为单声道进行分析
            if y.ndim == 2:
                y_mono_for_analysis = np.mean(y, axis=0)
            else:
                y_mono_for_analysis = y
            
            if progress_callback:
                progress_callback(11, "检测音频开始特征...")
            
            initial_pattern = self._analyze_initial_energy_pattern(y_mono_for_analysis, sr)
            
            if progress_callback:
                pattern_desc = {
                    'metronome': '节拍器',
                    'music': '音乐',
                    'silence': '静音',
                    'unknown': '未知'
                }.get(initial_pattern['pattern_type'], '未知')
                
                progress_callback(12, 
                    f"音频模式: {pattern_desc} "
                    f"(开始时间: {initial_pattern['start_time']:.2f}秒, "
                    f"周期性: {initial_pattern['periodicity_score']:.1%}, "
                    f"节拍器可能性: {initial_pattern['metronome_likelihood']:.1%})")
            
            # 根据分析结果提供诊断信息
            if initial_pattern['metronome_likelihood'] < 0.3:
                if progress_callback:
                    if initial_pattern['pattern_type'] == 'music':
                        progress_callback(13, 
                            "⚠ 注意: 音频似乎是纯音乐(没有节拍器)或节拍器音量很低")
                    elif initial_pattern['pattern_type'] == 'silence':
                        progress_callback(13, 
                            "⚠ 注意: 音频开始有较长的静音期")
                    else:
                        progress_callback(13, 
                            "⚠ 注意: 未检测到明显的节拍器特征，AI提取可能不准确")
            elif initial_pattern['metronome_likelihood'] > 0.7:
                if progress_callback:
                    progress_callback(13, "✓ 检测到典型节拍器特征，AI模型应能准确分离")
            
            # 确保是立体声
            if y.ndim == 1:
                y = np.stack([y, y])
            
            # 转换为torch tensor
            wav = torch.from_numpy(y).float()
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            wav = wav.unsqueeze(0)  # Add batch dimension
            
            if progress_callback:
                progress_callback(15, "使用AI模型分离音频源（这可能需要1-2分钟）...")
            
            # 应用模型进行源分离
            with torch.no_grad():
                sources = apply_model(model, wav, device='cpu', split=True, overlap=0.25)
            
            # sources shape: [batch, source, channel, time]
            # htdemucs输出: drums, bass, other, vocals
            sources = sources[0]  # Remove batch dimension
            
            if progress_callback:
                progress_callback(50, "AI分离完成，提取鼓声/节拍器轨道...")
            
            
            # 节拍器通常在drums或other中
            # 先尝试drums
            drums = sources[0].cpu().numpy()  # [channel, time]
            other = sources[2].cpu().numpy()  # [channel, time] - "other"轨道
            
            # 转换回单声道
            if drums.shape[0] == 2:
                drums_mono = np.mean(drums, axis=0)
            else:
                drums_mono = drums[0]
            
            if other.shape[0] == 2:
                other_mono = np.mean(other, axis=0)
            else:
                other_mono = other[0]
            
            # 检测哪个轨道包含更多的节拍器信号
            # 计算200-800Hz频段的能量(节拍器频段)
            from scipy import signal as scipy_signal
            
            def get_metronome_energy(audio_mono, sr):
                """计算节拍器频段(200-800Hz)的能量"""
                nyquist = sr / 2
                b, a = scipy_signal.butter(4, [200/nyquist, 800/nyquist], btype='band')
                filtered = scipy_signal.filtfilt(b, a, audio_mono)
                return np.sum(np.abs(filtered))
            
            drums_energy = get_metronome_energy(drums_mono, sr)
            other_energy = get_metronome_energy(other_mono, sr)
            
            if progress_callback:
                progress_callback(52, f"检测节拍器位置 - Drums能量: {drums_energy:.0f}, Other能量: {other_energy:.0f}")
            
            # 选择能量更高的轨道
            if other_energy > drums_energy * 1.5:  # other明显更强
                selected_stem = other_mono
                stem_name = "other"
                if progress_callback:
                    progress_callback(53, "✓ 节拍器在'other'轨道,使用该轨道")
            else:
                selected_stem = drums_mono
                stem_name = "drums"
                if progress_callback:
                    progress_callback(53, "✓ 节拍器在'drums'轨道,使用该轨道")
            
            
            if progress_callback:
                progress_callback(55, "应用强力频谱噪声门去除白噪声...")
            
            # 使用noisereduce库去除白噪声
            try:
                import noisereduce as nr
                
                # 第一遍：使用前0.5秒作为噪声样本进行标准降噪
                noise_sample_duration = min(0.5, len(selected_stem) / sr * 0.1)
                noise_sample_len = int(noise_sample_duration * sr)
                
                # 应用噪声减少 - 优化版参数（降低强度以保留更多气泡声）
                selected_stem = nr.reduce_noise(
                    y=selected_stem,
                    sr=sr,
                    stationary=True,
                    prop_decrease=0.7,  # 从1.0降到0.7，保留更多有用信号
                    freq_mask_smooth_hz=500,  # 从1000降到500
                    time_mask_smooth_ms=50  # 从100降到50
                )
                
                # 第二遍：非平稳噪声去除(针对残留的随机噪声) - 更保守
                selected_stem = nr.reduce_noise(
                    y=selected_stem,
                    sr=sr,
                    stationary=False,  # 非平稳噪声
                    prop_decrease=0.6,  # 从0.8降到0.6，更保守
                    freq_mask_smooth_hz=300,  # 从500降到300
                    time_mask_smooth_ms=30  # 从50降到30
                )
                
                if progress_callback:
                    progress_callback(57, "✓ 双重噪声去除完成")
                    
                # 额外的噪声门处理
                # 计算能量阈值,低于此阈值的部分视为噪声
                energy = np.abs(selected_stem)
                # 使用更严格的阈值 - 只保留最强的15%信号
                threshold = np.percentile(energy, 85)  # 85百分位
                
                # 创建掩码
                mask = energy > threshold
                
                # 平滑掩码边缘(避免咔嗒声)
                from scipy.ndimage import binary_dilation
                mask = binary_dilation(mask, iterations=int(sr * 0.01))  # 10ms扩展
                
                # 应用掩码
                selected_stem = selected_stem * mask
                
                if progress_callback:
                    progress_callback(58, "✓ 强力噪声门应用完成")
                    
            except ImportError:
                if progress_callback:
                    progress_callback(58, "noisereduce未安装,跳过噪声去除...")
            except Exception as e:
                if progress_callback:
                    progress_callback(58, f"噪声去除失败: {str(e)},继续处理...")
            
            # 现在在干净的stem上应用Beat Stacking
            # 保存到临时文件
            temp_drums = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_drums_path = temp_drums.name
            temp_drums.close()
            sf.write(temp_drums_path, selected_stem, sr)
            
            if progress_callback:
                progress_callback(60, "在分离后的音频上应用Beat Stacking...")
            # 调用原始的提取方法（在干净的drums上）
            def demucs_progress_wrapper(progress: int, message: str):
                # 映射进度到60-100%
                mapped_progress = 60 + int(progress * 0.4)
                if progress_callback:
                    progress_callback(mapped_progress, message)
            
            beat = self._extract_single_beat(temp_drums_path, demucs_progress_wrapper, use_demucs=False)
            
            # 清理临时文件
            if os.path.exists(temp_drums_path):
                os.remove(temp_drums_path)
            
            # 新增：验证提取质量
            if progress_callback:
                progress_callback(95, "验证提取质量...")
            
            # 将AudioSegment转换为numpy数组进行验证
            samples = np.array(beat.get_array_of_samples())
            if beat.channels == 2:
                samples = samples.reshape((-1, 2))
                samples = np.mean(samples, axis=1)
            samples = samples.astype(np.float32) / (2**15)
            
            quality = self._verify_metronome_quality(samples, beat.frame_rate)
            
            if progress_callback:
                progress_callback(97, f"质量验证: {quality['reason']}")
            
            # 如果质量不合格，回退到传统方法
            if not quality['is_valid']:
                if progress_callback:
                    progress_callback(98, f"⚠ Demucs提取质量不佳，使用传统方法重新提取...")
                
                # 直接从源文件用传统方法提取
                return self._extract_single_beat(metronome_path, progress_callback, use_demucs=False)
            
            if progress_callback:
                progress_callback(100, f"✓ Demucs提取完成 (质量评分: {quality['quality_score']:.1f})")
            
            return beat
            
        except Exception as e:
            if progress_callback:
                progress_callback(10, f"Demucs提取失败 ({str(e)})，回退到传统方法...")
            # 回退到原始方法
            return self._extract_single_beat(metronome_path, progress_callback, use_demucs=False)
    
    
    def _extract_single_beat(
        self,
        metronome_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        use_demucs: bool = True
    ) -> AudioSegment:
        """
        从节拍器音频中提取单个节拍
        优先使用Demucs AI模型，失败时回退到Beat Stacking方法
        
        Args:
            metronome_path: 节拍器音频路径
            progress_callback: 进度回调函数
            use_demucs: 是否尝试使用Demucs（默认True）
            
        Returns:
            单个节拍的音频段
        """
        # 首先尝试使用Demucs AI模型
        if use_demucs:
            try:
                return self._extract_single_beat_with_demucs(metronome_path, progress_callback)
            except Exception as e:
                if progress_callback:
                    progress_callback(10, f"Demucs不可用，使用传统方法...")
        
        # 回退到原始Beat Stacking方法
        if progress_callback:
            progress_callback(15, "读取节拍器文件...")

        
        # 使用librosa加载音频进行分析
        # 限制加载时长，避免处理过长的文件（最多30秒）
        # 这样可以加快处理速度，并且节拍器通常在前几秒就能检测到
        max_duration = 30.0
        y, sr = librosa.load(metronome_path, sr=self.sample_rate, duration=max_duration)
        duration_seconds = len(y) / sr
        
        if progress_callback:
            progress_callback(16, f"节拍器文件加载完成（时长: {duration_seconds:.1f}秒）...")
        
        # 新增：分析音频开始特征，验证是否为节拍器
        if progress_callback:
            progress_callback(17, "检测音频开始特征...")
        
        initial_pattern = self._analyze_initial_energy_pattern(y, sr)
        
        if progress_callback:
            pattern_desc = {
                'metronome': '节拍器',
                'music': '音乐',
                'silence': '静音',
                'unknown': '未知'
            }.get(initial_pattern['pattern_type'], '未知')
            
            progress_callback(17, 
                f"音频模式: {pattern_desc} "
                f"(开始时间: {initial_pattern['start_time']:.2f}秒, "
                f"周期性: {initial_pattern['periodicity_score']:.1%}, "
                f"节拍器可能性: {initial_pattern['metronome_likelihood']:.1%})")
        
        # 根据分析结果提供诊断信息
        if initial_pattern['metronome_likelihood'] < 0.3:
            if progress_callback:
                if initial_pattern['pattern_type'] == 'music':
                    progress_callback(17, 
                        "⚠ 注意: 音频似乎是纯音乐(没有节拍器)或节拍器音量很低")
                elif initial_pattern['pattern_type'] == 'silence':
                    progress_callback(17, 
                        "⚠ 注意: 音频开始有较长的静音期")
                else:
                    progress_callback(17, 
                        "⚠ 注意: 未检测到明显的节拍器特征，提取可能不准确")
        elif initial_pattern['metronome_likelihood'] > 0.6:
            if progress_callback:
                progress_callback(17, "✓ 检测到典型节拍器特征，提取准确性应该较高")
        
        if progress_callback:
            progress_callback(18, "分析音频周期性特征...")
        
        # 核心方法：使用自相关检测周期性
        # 节拍器最显著的特征就是严格的周期性，这是识别节拍器的关键
        
        # 1. 首先提取可能包含节拍器的频段
        # 计算STFT
        hop_length = 512
        n_fft = 2048
        stft = librosa.stft(y, hop_length=hop_length, n_fft=n_fft)
        magnitude = np.abs(stft)
        freq_hz = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        
        # 计算不同频段的能量（节拍器可能在多个频段出现）
        # 高频：1.5-10kHz（传统节拍器，"哒哒哒"声）
        hf_low_idx = np.argmin(np.abs(freq_hz - 1500))
        hf_high_idx = np.argmin(np.abs(freq_hz - 10000))
        high_freq_energy = np.sum(magnitude[hf_low_idx:hf_high_idx, :], axis=0)
        
        # 中频：300-2kHz（水滴声、"吐泡泡"声等）
        mf_low_idx = np.argmin(np.abs(freq_hz - 300))
        mf_high_idx = np.argmin(np.abs(freq_hz - 2000))
        mid_freq_energy = np.sum(magnitude[mf_low_idx:mf_high_idx, :], axis=0)
        
        # 低频：50-500Hz（低音节拍器）
        lf_low_idx = np.argmin(np.abs(freq_hz - 50))
        lf_high_idx = np.argmin(np.abs(freq_hz - 500))
        low_freq_energy = np.sum(magnitude[lf_low_idx:lf_high_idx, :], axis=0)
        
        # "吐泡泡"声音特征频段：200-800Hz（气泡声通常在这个范围）
        bubble_low_idx = np.argmin(np.abs(freq_hz - 200))
        bubble_high_idx = np.argmin(np.abs(freq_hz - 800))
        bubble_freq_energy = np.sum(magnitude[bubble_low_idx:bubble_high_idx, :], axis=0)
        
        # 计算RMS能量
        rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
        
        # 计算频谱特征来区分"吐泡泡"和"哒哒哒"声音
        # 频谱质心：吐泡泡声音通常频谱质心较低（中低频），哒哒哒声音频谱质心较高（高频）
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        
        # 频谱滚降：吐泡泡声音的频谱滚降点通常较低
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        
        # 计算每个时间帧的频谱特征，用于识别"吐泡泡"声音
        # 吐泡泡声音特征：中低频能量强，频谱质心低，频谱滚降点低
        bubble_score = np.zeros(len(rms))
        for i in range(len(rms)):
            # 计算"吐泡泡"声音的得分
            # 1. 气泡频段能量相对较强
            bubble_energy_ratio = bubble_freq_energy[i] / (rms[i] + 1e-10) if rms[i] > 0 else 0
            # 2. 高频能量相对较弱（不是"哒哒哒"）
            high_energy_ratio = high_freq_energy[i] / (rms[i] + 1e-10) if rms[i] > 0 else 0
            # 3. 频谱质心较低（中低频）
            centroid_normalized = spectral_centroids[i] / (sr / 2) if i < len(spectral_centroids) else 0.5
            # 4. 频谱滚降点较低
            rolloff_normalized = spectral_rolloff[i] / (sr / 2) if i < len(spectral_rolloff) else 0.5
            
            # 综合得分：气泡频段能量强 + 高频能量弱 + 频谱质心低 + 频谱滚降点低
            bubble_score[i] = (
                bubble_energy_ratio * 0.4 +  # 气泡频段能量
                (1.0 - min(high_energy_ratio, 1.0)) * 0.3 +  # 高频能量弱（反向）
                (1.0 - min(centroid_normalized, 1.0)) * 0.2 +  # 频谱质心低（反向）
                (1.0 - min(rolloff_normalized, 1.0)) * 0.1  # 频谱滚降点低（反向）
            )
        
        # 2. 对每个频段的能量信号进行自相关分析，找到周期性
        if progress_callback:
            progress_callback(19, "计算自相关函数，检测周期性（重点：160-200 BPM）...")
        
        # 定义节拍器典型的BPM范围：160-200
        # 这是跑步节拍器最常见的范围
        min_bpm = 160
        max_bpm = 200
        min_period_samples = int(sr * 60 / max_bpm)  # 对应200 BPM
        max_period_samples = int(sr * 60 / min_bpm)  # 对应160 BPM
        max_period_frames = max_period_samples // hop_length
        
        if progress_callback:
            progress_callback(19, f"搜索周期范围：{min_period_samples/sr:.2f}秒 到 {max_period_samples/sr:.2f}秒（{min_bpm}-{max_bpm} BPM）...")
        
        # 对每个频段计算自相关
        best_period = None
        best_period_score = 0
        best_energy_signal = None
        
        # 优先使用"吐泡泡"声音特征信号，而不是高频信号（高频通常是"哒哒哒"）
        # 使用气泡频段能量和气泡得分来识别节拍器
        bubble_combined_signal = bubble_freq_energy * (1.0 + bubble_score)  # 增强气泡特征明显的部分
        
        energy_signals = [
            (bubble_combined_signal, "气泡声（吐泡泡）"),  # 优先：专门针对"吐泡泡"声音
            (bubble_freq_energy, "气泡频段"),
            (mid_freq_energy, "中频"),
            (low_freq_energy, "低频"),
            (rms, "全频段RMS"),
            # 最后才考虑高频（通常是"哒哒哒"，不是我们要的）
            # (high_freq_energy, "高频"),  # 暂时禁用，避免识别到"哒哒哒"
        ]
        
        for energy_signal, signal_name in energy_signals:
            if len(energy_signal) < max_period_frames * 2:
                continue
            
            # 归一化能量信号
            if np.max(energy_signal) > 0:
                energy_normalized = (energy_signal - np.mean(energy_signal)) / (np.std(energy_signal) + 1e-10)
            else:
                continue
            
            # 计算自相关（只计算合理的延迟范围）
            # 使用FFT加速自相关计算（比np.correlate快得多）
            # 自相关 = IFFT(FFT(x) * conj(FFT(x)))
            fft_signal = np.fft.fft(energy_normalized, n=len(energy_normalized) * 2)
            autocorr = np.fft.ifft(fft_signal * np.conj(fft_signal))
            autocorr = np.real(autocorr[:len(energy_normalized)])  # 只取正延迟部分
            
            # 归一化自相关（除以第一个值，即零延迟的自相关）
            if autocorr[0] > 0:
                autocorr_normalized = autocorr / autocorr[0]
            else:
                continue
            
            # 在合理的周期范围内查找峰值
            min_period_frames = min_period_samples // hop_length
            search_range = autocorr_normalized[min_period_frames:min(max_period_frames, len(autocorr_normalized))]
            
            if len(search_range) == 0:
                continue
            
            # 找到峰值（局部最大值）
            peaks = []
            # 计算搜索范围的平均值和标准差，用于判断峰值强度
            search_mean = np.mean(search_range)
            search_std = np.std(search_range)
            threshold = search_mean + search_std * 0.5  # 阈值：平均值 + 0.5倍标准差
            
            for i in range(1, len(search_range) - 1):
                if search_range[i] > search_range[i-1] and search_range[i] > search_range[i+1]:
                    # 检查峰值是否足够强（超过阈值）
                    if search_range[i] > threshold:
                        period_frames = i + min_period_frames
                        period_samples = period_frames * hop_length
                        # 使用归一化后的峰值强度作为分数
                        peak_strength = (search_range[i] - search_mean) / (search_std + 1e-10)
                        peaks.append((peak_strength, period_samples, period_frames))
            
            # 对峰值按强度排序
            peaks.sort(reverse=True)
            
            # 验证周期性：检查这个周期是否在整个信号中重复出现
            # 核心：节拍器必须贯穿整个音频，而不是只在某些部分出现
            for peak_strength, period_samples, period_frames in peaks[:5]:  # 只检查前5个最强的峰值
                # 验证BPM是否在合理范围内
                bpm = 60 * sr / period_samples
                if bpm < min_bpm - 5 or bpm > max_bpm + 5:  # 允许小误差
                    continue
                
                # 计算这个周期的稳定性分数
                # 方法：检查信号在多个周期位置的一致性
                num_periods = len(energy_signal) // period_frames
                if num_periods < 3:  # 至少要有3个周期，确保是持续的
                    continue
                
                # 关键验证：节拍器必须贯穿整个音频
                # 检查从头到尾是否都有节拍（不能只在中间或某部分）
                # 将音频分成3段：开始、中间、结束，每段都应该有明显的节拍
                third_len = len(energy_signal) // 3
                first_third_energy = np.mean(energy_signal[:third_len])
                middle_third_energy = np.mean(energy_signal[third_len:2*third_len])
                last_third_energy = np.mean(energy_signal[2*third_len:])
                
                # 所有三段的能量应该都比较接近（变异系数小于0.5）
                energies = [first_third_energy, middle_third_energy, last_third_energy]
                energy_mean = np.mean(energies)
                energy_std = np.std(energies)
                energy_cv = energy_std / energy_mean if energy_mean > 0 else 1.0
                
                # 如果某部分能量特别低，说明节拍器不是贯穿整个音频的
                if energy_cv > 0.5 or min(energies) < energy_mean * 0.3:
                    continue
                
                # 额外验证：检查节拍点的均匀分布
                # 使用onset检测找到所有峰值，验证它们是否均匀分布在整个音频中
                threshold = np.percentile(energy_signal, 75)
                detected_beats = []
                for i in range(1, len(energy_signal) - 1):
                    if energy_signal[i] > threshold and energy_signal[i] > energy_signal[i-1] and energy_signal[i] > energy_signal[i+1]:
                        detected_beats.append(i)
                
                if len(detected_beats) < num_periods * 0.8:  # 至少检测到80%的预期节拍数
                    continue
                
                # 检查检测到的节拍是否均匀分布
                if len(detected_beats) >= 3:
                    beat_intervals = [detected_beats[i] - detected_beats[i-1] for i in range(1, len(detected_beats))]
                    interval_mean = np.mean(beat_intervals)
                    interval_std = np.std(beat_intervals)
                    interval_cv = interval_std / interval_mean if interval_mean > 0 else 1.0
                    
                    # 节拍间隔应该非常均匀（变异系数<0.25）
                    if interval_cv > 0.25:
                        continue
                    
                    # 平均间隔应该接近检测到的周期
                    if abs(interval_mean - period_frames) > period_frames * 0.2:
                        continue
                
                # 将信号按周期分段，计算各段之间的相关性
                period_segments = []
                # 从整个音频中均匀采样周期段，确保覆盖头、中、尾
                segment_indices = []
                for i in range(min(10, num_periods)):  # 最多检查10个周期
                    idx = int(i * num_periods / min(10, num_periods))
                    segment_indices.append(idx)
                
                for idx in segment_indices:
                    start_frame = idx * period_frames
                    end_frame = min(start_frame + period_frames, len(energy_signal))
                    if end_frame - start_frame >= period_frames * 0.8:  # 至少80%完整
                        period_segments.append(energy_normalized[start_frame:end_frame])
                
                if len(period_segments) < 3:  # 至少3个周期段
                    continue
                
                # 计算各段之间的平均相关性（周期性越强，相关性越高）
                correlations = []
                for i in range(len(period_segments)):
                    for j in range(i + 1, len(period_segments)):
                        min_len = min(len(period_segments[i]), len(period_segments[j]))
                        if min_len > 0:
                            corr = np.corrcoef(
                                period_segments[i][:min_len],
                                period_segments[j][:min_len]
                            )[0, 1]
                            if not np.isnan(corr):
                                correlations.append(corr)
                
                if len(correlations) > 0:
                    avg_correlation = np.mean(correlations)
                    # 周期性要求更严格：相关性必须很高（>0.7）
                    if avg_correlation < 0.7:
                        continue
                    
                    # 计算节拍均匀性得分（如果有detected_beats）
                    beat_uniformity = 0
                    if 'beat_intervals' in locals() and len(beat_intervals) > 0:
                        beat_uniformity = 1.0 - min(interval_cv, 1.0)  # 间隔越均匀，得分越高
                    
                    # 综合分数：自相关峰值强度 + 周期稳定性 + 贯穿整个音频 + 节拍均匀性
                    energy_consistency_bonus = 1.0 - energy_cv  # 能量越一致，奖励越高
                    period_score = (
                        peak_strength * 0.25 + 
                        (avg_correlation + 1) * 0.25 +  # 周期稳定性
                        energy_consistency_bonus * 0.25 +  # 贯穿整个音频
                        beat_uniformity * 0.25  # 节拍均匀分布
                    )
                    
                    if progress_callback:
                        progress_callback(19, f"候选周期：{bpm:.0f} BPM（相关性:{avg_correlation:.2f}, 能量一致性:{energy_consistency_bonus:.2f}, 均匀性:{beat_uniformity:.2f}, 得分:{period_score:.2f}）")
                    
                    if period_score > best_period_score:
                        best_period_score = period_score
                        best_period = period_samples
                        best_energy_signal = energy_signal
        
        # 3. 如果找到了周期性，基于周期提取节拍
        if best_period is not None and best_period > 0:
            period_seconds = best_period / sr
            bpm = 60 / period_seconds if period_seconds > 0 else 0
            
            # 检查得分是否足够高
            if best_period_score < 0.9:
                if progress_callback:
                    progress_callback(21, f"⚠ 检测到的周期得分较低（{bpm:.0f} BPM，得分: {best_period_score:.2f}），可能不是贯穿整个音频的节拍器...")
                    progress_callback(21, "提示：请确保上传的是包含节拍器的完整音频，且节拍器从头到尾都存在...")
                # 降低要求，但给出警告
                if best_period_score < 0.7:
                    # 得分太低，放弃
                    if progress_callback:
                        progress_callback(22, "未检测到符合条件的节拍器（160-200 BPM，贯穿整个音频），使用回退方法...")
                    best_period = None
            else:
                if progress_callback:
                    progress_callback(22, f"✓ 检测到符合条件的节拍器（{bpm:.0f} BPM，得分: {best_period_score:.2f}）...")
            # 3. 如果找到了周期性，基于周期提取节拍
        if best_period is not None and best_period > 0:
            
            # 使用检测到的周期，找到第一个完整的节拍
            period_frames = int(best_period / hop_length)
            period_samples = best_period
            
            # 在能量信号中找到第一个明显的节拍起始点
            # 使用onset检测找到节拍点
            try:
                onset_frames = librosa.onset.onset_detect(
                    y=y,
                    sr=sr,
                    units='frames',
                    hop_length=hop_length,
                    backtrack=True,
                    delta=0.1,
                    wait=8
                )
            except:
                onset_frames = []
            
            # 如果检测到onset点，验证它们是否符合检测到的周期
            valid_onsets = []
            if len(onset_frames) >= 2:
                for i, onset in enumerate(onset_frames):
                    # 检查这个onset是否在周期的整数倍位置附近
                    period_num = onset / period_frames
                    if abs(period_num - round(period_num)) < 0.2:  # 允许20%的误差
                        valid_onsets.append(onset)
            
            # 确定第一个节拍的位置
            first_beat_frame = 0
            if len(valid_onsets) < 2:
                # 优先使用气泡特征信号来定位节拍
                search_frames = min(period_frames * 3, len(bubble_combined_signal))
                search_signal = bubble_combined_signal[:search_frames] if len(bubble_combined_signal) >= search_frames else bubble_combined_signal
                
                if len(search_signal) > 0:
                    peak_frame = np.argmax(search_signal)
                    # 向前查找能量开始上升的点
                    threshold = np.percentile(search_signal, 30)
                    for i in range(peak_frame, max(0, peak_frame - period_frames // 4), -1):
                        if search_signal[i] < threshold * 1.2:
                            peak_frame = i + 1
                            break
                    first_beat_frame = peak_frame
                else:
                    first_beat_frame = 0
            else:
                # 使用第一个有效的onset点，但验证它是否是"吐泡泡"声音
                best_onset = valid_onsets[0]
                best_bubble_score = 0
                for onset in valid_onsets[:min(5, len(valid_onsets))]:
                    if onset < len(bubble_score):
                        if bubble_score[onset] > best_bubble_score:
                            best_bubble_score = bubble_score[onset]
                            best_onset = onset
                first_beat_frame = best_onset
            
            # 计算第一个节拍的样本位置
            first_beat_samples = int(first_beat_frame * hop_length)
            
            # 节拍长度：150ms
            beat_duration_samples = int(sr * 0.15)
            
            # --- 核心改进：Beat Stacking (节拍叠加/平均) ---
            if progress_callback:
                progress_callback(23, "执行节拍叠加(Beat Stacking)以消除背景音乐...")
            
            # 收集所有可能的节拍片段
            beat_segments = []
            
            # 预测所有节拍的位置
            # 使用精确的浮点数计算，避免累积误差
            num_beats_in_audio = int((len(y) - first_beat_samples) / period_samples)
            
            # 限制最大叠加数量，30个足够消除噪音，太多会增加计算量
            max_beats_to_stack = 100
            
            for i in range(min(num_beats_in_audio, max_beats_to_stack)):
                # 粗略位置
                target_sample = int(first_beat_samples + i * period_samples)
                
                # 局部微调对齐：在粗略位置附近寻找能量最大的点
                # 搜索范围：前后 10% 周期
                search_radius = int(period_samples * 0.1)
                search_start = max(0, target_sample - search_radius)
                search_end = min(len(y), target_sample + search_radius + beat_duration_samples)
                
                if search_end - search_start < beat_duration_samples:
                    continue
                    
                # 在该区域内计算短时能量，找到峰值作为对齐点
                local_y = y[search_start:search_end]
                
                # 使用气泡频段滤波器进行对齐，这样对齐最准
                # 设计简单的带通滤波器
                nyquist = sr / 2
                b_align, a_align = signal.butter(2, [200/nyquist, 800/nyquist], btype='band')
                local_y_filtered = signal.filtfilt(b_align, a_align, local_y)
                
                # 计算包络
                local_env = np.abs(local_y_filtered)
                
                # 找到局部最大值位置
                if len(local_env) > 0:
                    local_peak_idx = np.argmax(local_env)
                    aligned_start = search_start + local_peak_idx
                    
                    # 稍微回退一点，捕捉起振部分 (比如 10ms)
                    offset = int(sr * 0.01)
                    aligned_start = max(0, aligned_start - offset)
                    aligned_end = aligned_start + beat_duration_samples
                    
                    if aligned_end <= len(y):
                        segment = y[aligned_start:aligned_end]
                        # 简单的振幅归一化，防止某个特别响的节拍主导平均值
                        # 但不要完全归一化，保留相对动态
                        seg_max = np.max(np.abs(segment))
                        if seg_max > 0:
                            # 归一化到 0.5，保留余量
                            segment = segment / seg_max * 0.5
                            beat_segments.append(segment)
            
            if len(beat_segments) > 0:
                if progress_callback:
                    progress_callback(24, f"已收集 {len(beat_segments)} 个节拍片段，正在计算中位数...")
                
                # 堆叠片段
                stack = np.array(beat_segments)
                
                # 计算中位数 (Median)
                # 中位数比平均值(Mean)更好，因为它可以完全忽略偶尔出现的响亮背景音乐（离群值）
                beat_samples_raw = np.median(stack, axis=0)
                
                # 再次应用带通滤波器 (200-800Hz) 净化最终结果
                if progress_callback:
                    progress_callback(25, "应用最终滤波和降噪...")
                    
                nyquist = sr / 2
                b, a = signal.butter(6, [200/nyquist, 800/nyquist], btype='band')
                beat_samples = signal.filtfilt(b, a, beat_samples_raw)
                
                # 归一化
                max_amp = np.max(np.abs(beat_samples))
                if max_amp > 0:
                    beat_samples = beat_samples / max_amp * 0.98
                
                # 强力噪声门 (Noise Gate)
                # 消除气泡声之间的任何残留底噪
                window_size = int(sr * 0.005)
                energy_envelope = np.convolve(np.abs(beat_samples), np.ones(window_size)/window_size, mode='same')
                threshold = np.max(energy_envelope) * 0.1  # 10% 阈值
                
                # 创建门限遮罩
                mask = energy_envelope > threshold
                
                # 平滑遮罩 (Attack/Release)
                # 简单的二值膨胀
                dilation_size = int(sr * 0.01) # 10ms 保持
                mask_dilated = np.convolve(mask.astype(float), np.ones(dilation_size), mode='same') > 0
                
                # 应用遮罩
                beat_samples = beat_samples * mask_dilated
                
                # 再次精确裁剪
                if np.any(mask_dilated):
                    first_idx = np.argmax(mask_dilated)
                    last_idx = len(mask_dilated) - np.argmax(mask_dilated[::-1]) - 1
                    # 留余量
                    margin = int(sr * 0.01)
                    first_idx = max(0, first_idx - margin)
                    last_idx = min(len(beat_samples), last_idx + margin)
                    beat_samples = beat_samples[first_idx:last_idx]
                
            else:
                # 如果叠加失败（不应该发生），回退到单次提取
                if progress_callback:
                    progress_callback(24, "⚠ 叠加失败，回退到单次提取...")
                beat_start = max(0, first_beat_samples)
                beat_end = min(len(y), beat_start + beat_duration_samples)
                beat_samples = y[beat_start:beat_end]
                # ... (原有滤波逻辑) ...
                b, a = signal.butter(6, [200/(sr/2), 800/(sr/2)], btype='band')
                beat_samples = signal.filtfilt(b, a, beat_samples)
            
            if progress_callback:
                beat_duration_ms = (beat_end - beat_start) / sr * 1000
                progress_callback(25, f"提取节拍片段（长度: {beat_duration_ms:.0f}ms）...")
        else:
            # 回退方法：如果没有检测到明显的周期性，使用onset检测
            if progress_callback:
                progress_callback(20, "未检测到明显周期性，使用onset检测方法...")
            
            try:
                onset_frames = librosa.onset.onset_detect(
                    y=y,
                    sr=sr,
                    units='frames',
                    hop_length=hop_length,
                    backtrack=True,
                    delta=0.12,
                    wait=12
                )
            except:
                onset_frames = []
            
            if len(onset_frames) >= 2:
                # 优先选择气泡特征最强的onset点（确保是"吐泡泡"而不是"哒哒哒"）
                best_onset_idx = 0
                best_bubble_score = 0
                for idx, frame in enumerate(onset_frames):
                    if frame < len(bubble_score):
                        if bubble_score[frame] > best_bubble_score:
                            best_bubble_score = bubble_score[frame]
                            best_onset_idx = idx
                
                # 计算节拍间隔
                onset_samples = [int(frame * hop_length) for frame in onset_frames]
                intervals = [onset_samples[i] - onset_samples[i-1] for i in range(1, len(onset_samples))]
                median_interval = int(np.median(intervals))
                
                # 使用气泡特征最强的节拍点
                beat_start = onset_samples[best_onset_idx]
                # 缩短节拍长度到150ms
                beat_end = min(len(y), beat_start + int(sr * 0.15))
            elif len(onset_frames) == 1:
                beat_start = int(onset_frames[0] * hop_length)
                beat_end = min(len(y), beat_start + int(sr * 0.15))
            else:
                # 最后的回退：使用音频开始部分，但应用气泡频段滤波
                beat_start = 0
                beat_end = min(len(y), int(sr * 0.15))
            
            # 提取节拍片段
            beat_samples_full = y[beat_start:beat_end]
            
            # 使用带通滤波器提取气泡频段（200-800Hz），去除钢琴杂音
            if progress_callback:
                progress_callback(21, "提取气泡频段节拍特征，去除杂音...")
            
            # 设计带通滤波器：200-800Hz（气泡声的主要频段）
            nyquist = sr / 2
            low = 200 / nyquist
            high = 800 / nyquist
            b, a = signal.butter(6, [low, high], btype='band')  # 提高阶数到6
            beat_samples_filtered = signal.filtfilt(b, a, beat_samples_full)
            
            # 优先使用滤波后的信号
            beat_samples = beat_samples_filtered
            
            # 归一化
            max_amp = np.max(np.abs(beat_samples))
            if max_amp > 0:
                beat_samples = beat_samples / max_amp * 0.98
            
            # 精确裁剪：去除首尾的低能量部分
            window_size = int(sr * 0.005)
            energy_envelope = np.convolve(np.abs(beat_samples), np.ones(window_size)/window_size, mode='same')
            energy_threshold = np.max(energy_envelope) * 0.15
            above_threshold = energy_envelope > energy_threshold
            
            if np.any(above_threshold):
                first_idx = np.argmax(above_threshold)
                last_idx = len(above_threshold) - np.argmax(above_threshold[::-1]) - 1
                margin = int(sr * 0.005)
                first_idx = max(0, first_idx - margin)
                last_idx = min(len(beat_samples), last_idx + margin)
                beat_samples = beat_samples[first_idx:last_idx]
        
        if progress_callback:
            progress_callback(30, "提取多个节拍片段，通过中位数滤波去除杂音...")
        
        # 新策略：提取所有节拍片段，对齐后使用加权平均去除杂音
        # 核心思路：杂音是随机的，一致的部分是真正的节拍器音效
        
        # 检测所有节拍点
        try:
            all_onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, units='frames', hop_length=hop_length,
                backtrack=True, delta=0.1, wait=8
            )
        except:
            all_onset_frames = []
        
        if len(all_onset_frames) >= 3:
            # 如果检测到多个节拍点，提取所有片段
            if progress_callback:
                progress_callback(30, f"检测到 {len(all_onset_frames)} 个节拍点，提取片段...")
            
            all_segments = []
            
            # 提取所有节拍点的片段
            for onset_frame in all_onset_frames:
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
            
            if len(all_segments) >= 3:
                if progress_callback:
                    progress_callback(31, f"提取了 {len(all_segments)} 个有效片段，开始对齐和降噪...")
                
                # 统一长度
                min_length = min(len(seg) for seg in all_segments)
                all_segments = [seg[:min_length] for seg in all_segments]
                
                # 对齐片段（使用互相关）
                reference = all_segments[0]
                aligned_segments = [reference]
                
                for seg in all_segments[1:]:
                    # 计算互相关找到最佳对齐位置
                    correlation = np.correlate(reference, seg, mode='full')
                    lag = np.argmax(correlation) - (len(reference) - 1)
                    
                    # 对齐片段
                    if abs(lag) < len(reference) // 4:  # 只对齐小偏移
                        if lag > 0:
                            aligned = np.pad(seg, (lag, 0), mode='constant')[:len(reference)]
                        elif lag < 0:
                            aligned = np.pad(seg, (0, -lag), mode='constant')[-lag:-lag+len(reference)]
                        else:
                            aligned = seg
                        
                        # 确保长度一致
                        if len(aligned) > len(reference):
                            aligned = aligned[:len(reference)]
                        elif len(aligned) < len(reference):
                            aligned = np.pad(aligned, (0, len(reference) - len(aligned)), mode='constant')
                        
                        aligned_segments.append(aligned)
                    else:
                        aligned_segments.append(seg)
                
                if progress_callback:
                    progress_callback(32, f"对齐完成，使用加权平均降噪...")
                
                # 计算中位数信号作为参考
                segments_matrix = np.array(aligned_segments)
                median_signal = np.median(segments_matrix, axis=0)
                
                # 计算每个片段与中位数的相似度
                similarities = []
                for seg in aligned_segments:
                    corr = np.corrcoef(median_signal, seg)[0, 1]
                    if not np.isnan(corr):
                        similarities.append(corr)
                    else:
                        similarities.append(0)
                
                # 选择相似度最高的20%片段进行平均
                n_select = max(3, int(len(similarities) * 0.2))
                top_indices = np.argsort(similarities)[-n_select:]
                
                selected_segments = [aligned_segments[i] for i in top_indices]
                beat_samples = np.mean(selected_segments, axis=0)
                
                # 归一化
                max_amp = np.max(np.abs(beat_samples))
                if max_amp > 0:
                    beat_samples = beat_samples / max_amp * 0.98
                
                if progress_callback:
                    avg_similarity = np.mean([similarities[i] for i in top_indices])
                    progress_callback(33, f"降噪完成，使用了 {n_select} 个最相似片段（平均相似度: {avg_similarity:.4f}）...")
            else:
                # 如果有效片段太少，使用beat_samples（之前提取的）
                pass
        
        # 去除首尾的静音部分（beat_samples已经在上面提取并处理过了）
        if len(beat_samples) > 0:
            sample_energy = np.abs(beat_samples)
            energy_threshold = np.percentile(sample_energy, 10)
            
            start_idx = 0
            for i in range(len(beat_samples)):
                if sample_energy[i] > energy_threshold * 2:
                    start_idx = i
                    break
            
            end_idx = len(beat_samples)
            for i in range(len(beat_samples) - 1, -1, -1):
                if sample_energy[i] > energy_threshold * 2:
                    end_idx = i + 1
                    break
            
            margin_samples = int(sr * 0.01)
            start_idx = max(0, start_idx - margin_samples)
            end_idx = min(len(beat_samples), end_idx + margin_samples)
            
            beat_samples = beat_samples[start_idx:end_idx]
        
        # 如果提取的片段太短（少于30ms），说明提取失败，使用音频开头的片段
        if len(beat_samples) < sr * 0.03:
            if progress_callback:
                progress_callback(30, "提取的节拍片段太短，重新提取...")
            # 使用音频开头的150ms，应用气泡滤波
            duration_samples = int(sr * 0.15)
            segment = y[:min(duration_samples, len(y))]
            
            # 应用气泡滤波去除杂音
            nyquist = sr / 2
            low = 200 / nyquist
            high = 800 / nyquist
            b, a = signal.butter(6, [low, high], btype='band')
            segment_filtered = signal.filtfilt(b, a, segment)
            beat_samples = segment_filtered * 0.8 + segment * 0.2
            
            # 归一化
            max_amp = np.max(np.abs(beat_samples))
            if max_amp > 0:
                beat_samples = beat_samples / max_amp * 0.98
        
        # 验证提取的节拍样本
        if len(beat_samples) == 0:
            raise ValueError("节拍样本为空，无法提取节拍")
        
        beat_max_amplitude = np.max(np.abs(beat_samples))
        if beat_max_amplitude < 0.001:
            if progress_callback:
                progress_callback(30, f"警告：提取的节拍信号很弱（最大振幅: {beat_max_amplitude:.6f}），尝试使用音频开始部分...")
            # 使用音频开始部分，并增强音量
            default_duration_samples = int(sr * 0.25)
            beat_samples = y[:min(default_duration_samples, len(y))]
            if np.max(np.abs(beat_samples)) > 0:
                # 增强音量
                beat_samples = beat_samples * (0.1 / np.max(np.abs(beat_samples)))
        
        # 转换为AudioSegment
        import tempfile
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        sf.write(temp_wav_path, beat_samples, sr)
        beat_audio = AudioSegment.from_file(temp_wav_path)
        
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        
        # 最终验证
        if len(beat_audio) == 0:
            raise ValueError("提取的节拍音频为空")
        
        beat_rms = beat_audio.rms
        beat_max_db = beat_audio.max_dBFS
        
        if progress_callback:
            progress_callback(35, f"节拍提取完成（长度: {len(beat_audio)}ms, RMS: {beat_rms:.1f}, 最大dB: {beat_max_db:.1f}）")
        
        return beat_audio
    
    def extract_metronome(
        self,
        music_path: str,
        output_path: str,
        output_format: str = "mp3",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        """
        从音乐中提取节拍器
        
        使用与 combine_audio 相同的逻辑：
        1. 检测 BPM
        2. 提取单个节拍
        3. 重建节拍器轨道
        
        Args:
            music_path: 带节拍器的音乐路径
            output_path: 输出文件路径
            output_format: 输出格式（默认 mp3）
            progress_callback: 进度回调函数 (progress, message)
        """
        if progress_callback:
            progress_callback(10, "加载音频文件...")
        
        # 加载音频
        music_audio = AudioSegment.from_file(music_path)
        duration_ms = len(music_audio)
        
        if progress_callback:
            progress_callback(20, "检测 BPM...")
            
        # 检测 BPM
        bpm = self._detect_bpm(music_path)
        if bpm <= 0:
            # 如果检测失败，尝试使用默认值或报错
            # 这里我们假设如果是跑步音乐，BPM通常在150-200之间
            # 但为了安全，我们报错
            raise ValueError("无法检测到有效的 BPM")
            
        if progress_callback:
            progress_callback(30, f"检测到 BPM: {bpm:.1f}")
            
        # 提取单个节拍
        if progress_callback:
            progress_callback(35, "提取单个节拍样本...")
            
        def extract_progress_wrapper(progress: int, message: str):
            # 将提取进度映射到35-60%
            mapped_progress = 35 + int(progress * 0.25)
            if progress_callback:
                progress_callback(mapped_progress, message)
        
        beat_audio = self._extract_single_beat(music_path, extract_progress_wrapper)
        
        # 生成节拍器轨道
        if progress_callback:
            progress_callback(65, "生成完整节拍器轨道...")
            
        metronome_track = self._generate_metronome_track(
            beat_audio=beat_audio,
            target_bpm=int(bpm),
            duration_ms=duration_ms,
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(90, "导出音频文件...")
            
        # 导出
        metronome_track.export(output_path, format=output_format)
        
        if progress_callback:
            progress_callback(100, "完成")

    def _generate_metronome_track(
        self, 
        beat_audio: AudioSegment, 
        target_bpm: int, 
        duration_ms: int,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AudioSegment:
        """
        生成节拍器轨道
        
        Args:
            beat_audio: 单个节拍音频
            target_bpm: 目标 BPM
            duration_ms: 目标时长（毫秒）
            progress_callback: 进度回调
            
        Returns:
            AudioSegment: 完整的节拍器轨道
        """
        if progress_callback:
            progress_callback(40, f"计算节拍间隔（目标 BPM: {target_bpm}）...")
        
        # 计算节拍间隔（毫秒）
        beat_interval_ms = int(60000 / target_bpm)
        
        # 计算需要放置多少个节拍
        num_beats = int(duration_ms / beat_interval_ms) + 1
        
        # 调整节拍音量
        beat_rms = beat_audio.rms
        beat_max_db = beat_audio.max_dBFS
        
        # 如果节拍音量太低，增强它；否则稍微降低以避免过于突兀
        if beat_rms < 100 or beat_max_db < -40:
            # 增强节拍音量（增加6dB）
            beat_audio = beat_audio + 6
        else:
            # 稍微降低节拍音量（降低3dB）
            beat_audio = beat_audio - 3
            
        # 收集所有需要放置的节拍位置
        beat_positions = []
        for beat_num in range(num_beats):
            beat_position_ms = beat_num * beat_interval_ms
            if beat_position_ms >= duration_ms:
                break
            beat_positions.append(beat_position_ms)
            
        # 创建静音轨道
        metronome_track = AudioSegment.silent(duration=duration_ms)
        
        # 在静音上叠加节拍
        for i, beat_position_ms in enumerate(beat_positions):
            if beat_position_ms + len(beat_audio) <= duration_ms:
                metronome_track = metronome_track.overlay(beat_audio, position=beat_position_ms)
            
            # 每50个节拍更新一次进度
            if (i + 1) % 50 == 0 and progress_callback:
                # 这里的进度是相对的，假设调用者分配了一定的进度区间
                # 我们这里简单打印日志，或者如果需要更精确的控制，可以传入start/end progress
                pass
                
        return metronome_track
    
    def concatenate_audio(
        self,
        music_paths: List[str],
        target_duration: float,
        output_path: str,
        output_format: str = "mp3",
        crossfade_ms: int = 0,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        """
        拼接多个音乐文件，达到目标时长
        
        Args:
            music_paths: 音乐文件路径列表
            target_duration: 目标总时长（秒）
            output_path: 输出文件路径
            output_format: 输出格式（默认 mp3）
            progress_callback: 进度回调函数 (progress, message)
        """
        combined = AudioSegment.empty()
        current_duration = 0.0
        target_duration_ms = target_duration * 1000
        total_files = len(music_paths)
        
        if progress_callback:
            progress_callback(5, f"开始拼接 {total_files} 个音频文件...")
        total_input_duration_ms = 0
        audio_segments = []
        
        if progress_callback:
            progress_callback(10, f"加载并分析 {total_files} 个音频文件...")
            
        for i, path in enumerate(music_paths):
            audio = AudioSegment.from_file(path)
            audio_segments.append(audio)
            total_input_duration_ms += len(audio)
            if progress_callback:
                progress_callback(10 + int((i+1)/total_files * 10), f"加载文件 {i+1}/{total_files}...")
        
        # 限制目标时长不超过总时长
        if target_duration_ms > total_input_duration_ms:
            target_duration_ms = total_input_duration_ms
            if progress_callback:
                progress_callback(25, f"目标时长超过总时长，已调整为 {target_duration_ms/1000:.1f}秒")
        
        if progress_callback:
            progress_callback(30, "开始拼接音频...")
        
        # 循环添加音乐直到达到目标时长
        music_index = 0
        while current_duration < target_duration_ms and music_index < len(audio_segments):
            # 使用预加载的音频段
            audio = audio_segments[music_index % len(audio_segments)]
            
            if progress_callback:
                progress = int(30 + (current_duration / target_duration_ms) * 60)
                progress_callback(progress, f"拼接进度 {progress}%...")
            
            remaining = target_duration_ms - current_duration
            
            if len(audio) <= remaining:
                # 如果当前音乐完整长度不超过剩余时长，全部添加
                if crossfade_ms > 0 and len(combined) > crossfade_ms:
                    combined = combined.append(audio, crossfade=crossfade_ms)
                else:
                    combined += audio
                current_duration += len(audio)
            else:
                # 否则只添加需要的部分
                if crossfade_ms > 0 and len(combined) > crossfade_ms:
                    combined = combined.append(audio[:int(remaining)], crossfade=crossfade_ms)
                else:
                    combined += audio[:int(remaining)]
                current_duration = target_duration_ms
            
            music_index += 1
        
        if progress_callback:
            progress_callback(95, "导出音频文件...")
        
        # 导出
        combined.export(output_path, format=output_format)
        
        if progress_callback:
            progress_callback(100, "完成")
    
    def _detect_bpm(self, audio_path: str) -> float:
        """
        检测音频的 BPM
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            检测到的 BPM 值
        """
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            return float(tempo)
        except:
            return 0.0
    
    def _adjust_speed(self, audio: AudioSegment, speed_ratio: float) -> AudioSegment:
        """
        调整音频播放速度
        
        Args:
            audio: 音频段
            speed_ratio: 速度比例（1.0 为原始速度）
            
        Returns:
            调整后的音频段
        """
        # 使用 frame_rate 调整来改变速度（同时改变音调）
        new_sample_rate = int(audio.frame_rate * speed_ratio)
        return audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})

