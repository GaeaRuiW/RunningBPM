import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import Wizard from '../components/shared/Wizard';
import FileUploadZone from '../components/shared/FileUploadZone';
import AudioVisualizer from '../components/shared/AudioVisualizer';
import AudioPlayer from '../components/AudioPlayer';
import './Stitcher.css';

const API_BASE_URL = 'http://localhost:8000';

const Stitcher: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(0);
    const [musicFiles, setMusicFiles] = useState<File[]>([]);
    const [targetDuration, setTargetDuration] = useState<number>(1800); // Default 30 mins
    const [outputFormat, setOutputFormat] = useState<string>('mp3');
    const [availableFormats, setAvailableFormats] = useState<string[]>(['mp3']);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
    const [filename, setFilename] = useState<string | null>(null);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [progress, setProgress] = useState<number>(0);
    const [progressMessage, setProgressMessage] = useState<string>('');


    // Detect formats when files change
    useEffect(() => {
        if (musicFiles.length > 0) {
            const formats = musicFiles.map(f => f.name.split('.').pop()?.toLowerCase() || 'mp3');

            const formatQuality: { [key: string]: number } = {
                'flac': 5, 'wav': 4, 'm4a': 3, 'aac': 3, 'ogg': 2, 'mp3': 1
            };

            const maxFormat = formats.reduce((a, b) =>
                (formatQuality[a] || 0) > (formatQuality[b] || 0) ? a : b
            );

            fetchAvailableFormats(maxFormat);
        }
    }, [musicFiles]);

    // Polling for progress
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
                        setDownloadUrl(`${API_BASE_URL}${response.data.result.download_url}`);
                        setFilename(response.data.result.filename);

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

    const handleMusicSelect = (files: File[]) => {
        setMusicFiles(prev => [...prev, ...files]);
    };

    const handleNext = () => {
        if (currentStep === 0 && musicFiles.length === 0) {
            setError('请至少上传一个音乐文件。');
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
        setDownloadUrl(null);
        setProgress(0);
        setProgressMessage('初始化中...');
        setCurrentStep(2);

        try {
            const formData = new FormData();
            musicFiles.forEach(file => formData.append('music_files', file));
            formData.append('target_duration', targetDuration.toString());
            formData.append('output_format', outputFormat);

            const response = await axios.post(`${API_BASE_URL}/api/concatenate`, formData, {
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

    const formatDuration = (seconds: number): string => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours > 0 ? `${hours}小时 ${minutes}分钟` : `${minutes}分钟`;
    };

    return (
        <div className="stitcher-page">
            <Wizard
                title="音乐拼接"
                steps={['上传音乐', '配置设置', '处理中']}
                currentStep={currentStep}
            >
                {currentStep === 0 && (
                    <div className="step-container">
                        <div className="upload-section full-width">
                            <h3>上传音乐文件</h3>
                            <FileUploadZone
                                id="stitcher-upload"
                                onFilesSelected={handleMusicSelect}
                                label={musicFiles.length > 0 ? `已选择 ${musicFiles.length} 个文件` : "拖拽音乐文件到这里"}
                                multiple={true}
                                accept="audio/*"
                            />
                            {musicFiles.length > 0 && (
                                <div className="file-list-preview">
                                    {musicFiles.map((f, i) => (
                                        <div key={i} className="file-preview-item">
                                            <span className="file-number">{i + 1}.</span>
                                            <span className="file-name">{f.name}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {error && <div className="error-message">{error}</div>}

                        <div className="wizard-actions">
                            <button className="action-button primary" onClick={handleNext}>
                                下一步: 配置设置 →
                            </button>
                        </div>
                    </div>
                )}

                {currentStep === 1 && (
                    <div className="step-container">
                        <div className="settings-grid">
                            <div className="setting-card">
                                <label>目标时长</label>
                                <div className="duration-input-wrapper">
                                    <input
                                        type="number"
                                        min="60"
                                        max="7200"
                                        step="60"
                                        value={targetDuration}
                                        onChange={(e) => setTargetDuration(parseFloat(e.target.value) || 1800)}
                                    />
                                    <span>秒</span>
                                </div>
                                <div className="duration-preview">
                                    ≈ {formatDuration(targetDuration)}
                                </div>
                                <small>建议: 600-3600秒 (10-60 分钟)</small>
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
                        </div>

                        <div className="wizard-actions">
                            <button className="action-button secondary" onClick={handleBack}>
                                ← 返回
                            </button>
                            <button className="action-button primary" onClick={handleSubmit}>
                                开始拼接 🔗
                            </button>
                        </div>
                    </div>
                )}

                {currentStep === 2 && (
                    <div className="step-container centered">
                        {loading ? (
                            <div className="processing-state">
                                <AudioVisualizer isPlaying={true} />
                                <h3>{progressMessage}</h3>
                                <div className="progress-bar-container">
                                    <motion.div
                                        className="progress-fill"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                    />
                                </div>
                                <p>{progress}% 完成</p>
                            </div>
                        ) : downloadUrl ? (
                            <div className="success-state">
                                <div className="success-icon">✅</div>
                                <h3>拼接完成!</h3>
                                <p>您的长音乐已准备就绪。</p>

                                <div className="result-card">
                                    <div className="result-info">
                                        <span className="result-filename">{filename}</span>
                                    </div>
                                    <div className="result-actions-row">
                                        <AudioPlayer audioUrl={downloadUrl} filename={filename || 'mix.mp3'} />
                                        <a href={downloadUrl} download={filename || 'mix.mp3'} className="download-btn large">
                                            📥 下载拼接音乐
                                        </a>
                                    </div>
                                </div>

                                <button
                                    className="action-button secondary"
                                    onClick={() => {
                                        setCurrentStep(0);
                                        setMusicFiles([]);
                                        setDownloadUrl(null);
                                    }}
                                >
                                    开始新的拼接
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

export default Stitcher;
