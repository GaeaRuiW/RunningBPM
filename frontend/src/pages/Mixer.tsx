import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import Wizard from '../components/shared/Wizard';
import FileUploadZone from '../components/shared/FileUploadZone';
import AudioPlayer from '../components/AudioPlayer';
import './Mixer.css';

const API_BASE_URL = 'http://localhost:8000';

interface OutputFile {
    download_url: string;
    filename: string;
}

const Mixer: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(0);
    const [metronomeFile, setMetronomeFile] = useState<File | null>(null);
    const [musicFiles, setMusicFiles] = useState<File[]>([]);
    const [targetBPM, setTargetBPM] = useState<number>(180);
    const [outputFormat, setOutputFormat] = useState<string>('mp3');
    const [availableFormats, setAvailableFormats] = useState<string[]>(['mp3']);
    const [autoExtractMetronome, setAutoExtractMetronome] = useState<boolean>(false);
    const [metronomeVolume, setMetronomeVolume] = useState<number>(0);
    const [maxConcurrent, setMaxConcurrent] = useState<number>(4);
    const [serverCpuCount, setServerCpuCount] = useState<number>(4);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [outputFiles, setOutputFiles] = useState<OutputFile[]>([]);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [progress, setProgress] = useState<number>(0);
    const [progressMessage, setProgressMessage] = useState<string>('');

    useEffect(() => {
        const fetchServerInfo = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/server-info`);
                setServerCpuCount(response.data.cpu_count);
                setMaxConcurrent(response.data.default_max_concurrent);
            } catch (err) {
                console.error('Failed to fetch server info:', err);
            }
        };
        fetchServerInfo();
    }, []);

    useEffect(() => {
        if (musicFiles.length > 0) {
            const fileExt = musicFiles[0].name.split('.').pop()?.toLowerCase() || 'mp3';
            fetchAvailableFormats(fileExt);
        }
    }, [musicFiles]);

    useEffect(() => {
        if (!taskId || !loading) return;

        const fetchProgress = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/progress/${taskId}`);
                setProgress(response.data.progress);
                setProgressMessage(response.data.message);

                if (response.data.status === 'completed') {
                    setLoading(false);
                    if (response.data.result) {
                        const files = response.data.result.files
                            ? response.data.result.files.map((file: OutputFile) => ({
                                download_url: `${API_BASE_URL}${file.download_url}`,
                                filename: file.filename
                            }))
                            : [{
                                download_url: `${API_BASE_URL}${response.data.result.download_url}`,
                                filename: response.data.result.filename
                            }];
                        setOutputFiles(files);
                    }
                    return true;
                } else if (response.data.status === 'failed') {
                    setLoading(false);
                    setError(response.data.message);
                    return true;
                }
                return false;
            } catch (err) {
                console.error('Failed to fetch progress:', err);
                return false;
            }
        };

        fetchProgress();
        const interval = setInterval(async () => {
            const done = await fetchProgress();
            if (done) clearInterval(interval);
        }, 1000);

        return () => clearInterval(interval);
    }, [taskId, loading]);

    const fetchAvailableFormats = async (sourceFormat: string) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/formats/${sourceFormat}`);
            setAvailableFormats(response.data.available_formats);
            if (response.data.available_formats.includes('mp3')) {
                setOutputFormat('mp3');
            } else if (response.data.available_formats.length > 0) {
                setOutputFormat(response.data.available_formats[0]);
            }
        } catch (err) {
            console.error('Failed to fetch formats:', err);
        }
    };

    const handleMetronomeSelect = (files: File[]) => {
        if (files.length > 0) setMetronomeFile(files[0]);
    };

    const handleMusicSelect = (files: File[]) => {
        setMusicFiles(prev => [...prev, ...files]);
    };

    const handleNext = () => {
        if (currentStep === 0 && (!metronomeFile || musicFiles.length === 0)) {
            setError('请上传节拍器和音乐文件。');
            return;
        }
        setError(null);
        setCurrentStep(prev => prev + 1);
    };

    const handleBack = () => {
        setCurrentStep(prev => prev - 1);
    };

    const handleSubmit = async () => {
        setLoading(true);
        setError(null);
        setOutputFiles([]);
        setProgress(0);
        setProgressMessage('初始化中...');
        setCurrentStep(2);

        try {
            const formData = new FormData();
            if (metronomeFile) formData.append('metronome', metronomeFile);
            musicFiles.forEach(file => formData.append('music_files', file));
            formData.append('target_bpm', targetBPM.toString());
            formData.append('output_format', outputFormat);
            formData.append('auto_extract_metronome', autoExtractMetronome.toString());
            formData.append('metronome_volume', metronomeVolume.toString());
            formData.append('max_concurrent', maxConcurrent.toString());

            const response = await axios.post(`${API_BASE_URL}/api/combine`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            if (response.data.success) {
                setTaskId(response.data.task_id);
            } else {
                setLoading(false);
                setError('服务器返回失败状态');
            }
        } catch (err: any) {
            setLoading(false);
            setError(err.response?.data?.detail || '处理失败');
        }
    };

    const handleBatchDownload = async () => {
        if (outputFiles.length === 0) return;
        try {
            const filenames = outputFiles.map(file => file.filename);
            const response = await axios.post(
                `${API_BASE_URL}/api/batch-download`,
                { filenames },
                { responseType: 'blob' }
            );
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `batch_combined_${Date.now()}.zip`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            setError('批量下载失败');
        }
    };

    return (
        <div className="mixer-page">
            <Wizard
                title="音频合成"
                steps={['上传文件', '配置设置', '处理中']}
                currentStep={currentStep}
            >
                {currentStep === 0 && (
                    <div className="step-container">
                        <div className="upload-grid">
                            <div className="upload-section">
                                <h3>1. 节拍器音频</h3>
                                <FileUploadZone
                                    id="metronome-upload"
                                    onFilesSelected={handleMetronomeSelect}
                                    label={metronomeFile ? `已选择: ${metronomeFile.name}` : "上传节拍器音频"}
                                    accept="audio/*"
                                />
                            </div>
                            <div className="upload-section">
                                <h3>2. 音乐音频</h3>
                                <FileUploadZone
                                    id="music-upload"
                                    onFilesSelected={handleMusicSelect}
                                    label={musicFiles.length > 0 ? `已选择 ${musicFiles.length} 个文件` : "上传音乐文件"}
                                    multiple={true}
                                    accept="audio/*"
                                />
                                {musicFiles.length > 0 && (
                                    <div className="file-list-preview">
                                        {musicFiles.map((f, i) => (
                                            <div key={i} className="file-preview-item">{f.name}</div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="checkbox-wrapper">
                            <label className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={autoExtractMetronome}
                                    onChange={(e) => setAutoExtractMetronome(e.target.checked)}
                                />
                                <span>从源文件中自动提取节拍器</span>
                            </label>
                        </div>

                        {error && <div className="error-message">{error}</div>}

                        <div className="wizard-actions">
                            <button className="action-button primary" onClick={handleNext}>
                                下一步: 配置设置
                            </button>
                        </div>
                    </div>
                )}

                {currentStep === 1 && (
                    <div className="step-container">
                        <div className="settings-grid">
                            <div className="setting-card">
                                <label>目标步频 (BPM)</label>
                                <div className="bpm-input-wrapper">
                                    <input
                                        type="number"
                                        min="60"
                                        max="300"
                                        value={targetBPM}
                                        onChange={(e) => setTargetBPM(parseInt(e.target.value) || 180)}
                                    />
                                    <span>BPM</span>
                                </div>
                                <small>建议范围: 120-200 BPM</small>
                            </div>

                            <div className="setting-card">
                                <label>输出格式</label>
                                <select
                                    value={outputFormat}
                                    onChange={(e) => setOutputFormat(e.target.value)}
                                >
                                    {availableFormats.map(fmt => (
                                        <option key={fmt} value={fmt}>{fmt.toUpperCase()}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="setting-card full-width">
                                <label>节拍器音量 ({metronomeVolume > 0 ? '+' : ''}{metronomeVolume} dB)</label>
                                <input
                                    type="range"
                                    min="-20"
                                    max="20"
                                    value={metronomeVolume}
                                    onChange={(e) => setMetronomeVolume(parseInt(e.target.value))}
                                />
                                <div className="range-labels">
                                    <span>-20dB</span>
                                    <span>0dB</span>
                                    <span>+20dB</span>
                                </div>
                            </div>

                            <div className="setting-card full-width">
                                <label>最大并发数 ({maxConcurrent})</label>
                                <input
                                    type="range"
                                    min="1"
                                    max={serverCpuCount}
                                    value={maxConcurrent}
                                    onChange={(e) => setMaxConcurrent(parseInt(e.target.value))}
                                />
                                <div className="range-labels">
                                    <span>1</span>
                                    <span>{Math.ceil(serverCpuCount / 2)}</span>
                                    <span>{serverCpuCount}</span>
                                </div>
                                <small>同时处理的文件数量，服务器最多支持 {serverCpuCount} 个并发</small>
                            </div>
                        </div>

                        <div className="wizard-actions">
                            <button className="action-button secondary" onClick={handleBack}>
                                返回
                            </button>
                            <button className="action-button primary" onClick={handleSubmit}>
                                开始处理
                            </button>
                        </div>
                    </div>
                )}

                {currentStep === 2 && (
                    <div className="step-container centered">
                        {loading ? (
                            <div className="processing-state">
                                <div className="loading-indicator">
                                    <div className="spinner" />
                                    <p>{progressMessage}</p>
                                </div>
                                <div className="progress-bar-container" style={{ marginTop: '20px' }}>
                                    <motion.div
                                        className="progress-fill"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                    />
                                </div>
                                <p>{progress}% 完成</p>
                            </div>
                        ) : outputFiles.length > 0 ? (
                            <div className="success-state">
                                <div className="success-icon">{"\u2713"}</div>
                                <h3>处理完成!</h3>
                                <p>成功生成 {outputFiles.length} 个文件。</p>

                                <div className="results-list">
                                    {outputFiles.map((file, index) => (
                                        <div key={index} className="result-item">
                                            <span>{file.filename}</span>
                                            <div className="result-actions">
                                                <AudioPlayer audioUrl={file.download_url} filename={file.filename} />
                                                <a href={file.download_url} download={file.filename} className="download-btn">
                                                    下载
                                                </a>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {outputFiles.length > 1 && (
                                    <button onClick={handleBatchDownload} className="action-button primary">
                                        批量下载 ZIP
                                    </button>
                                )}

                                <button
                                    className="action-button secondary"
                                    onClick={() => {
                                        setCurrentStep(0);
                                        setOutputFiles([]);
                                        setMusicFiles([]);
                                        setMetronomeFile(null);
                                    }}
                                >
                                    开始新的合成
                                </button>
                            </div>
                        ) : (
                            <div className="error-state">
                                <h3>出错了</h3>
                                <p>{error}</p>
                                <button className="action-button secondary" onClick={() => setCurrentStep(1)}>
                                    重试
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </Wizard>
        </div>
    );
};

export default Mixer;
