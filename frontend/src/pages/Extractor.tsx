import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import Wizard from '../components/shared/Wizard';
import FileUploadZone from '../components/shared/FileUploadZone';
import AudioPlayer from '../components/AudioPlayer';
import './Extractor.css';

const API_BASE_URL = 'http://localhost:8000';

const Extractor: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(0);
    const [musicFile, setMusicFile] = useState<File | null>(null);
    const [outputFormat, setOutputFormat] = useState<string>('mp3');
    const [availableFormats, setAvailableFormats] = useState<string[]>(['mp3']);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
    const [filename, setFilename] = useState<string | null>(null);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [progress, setProgress] = useState<number>(0);
    const [progressMessage, setProgressMessage] = useState<string>('');

    // Detect formats when file changes
    useEffect(() => {
        if (musicFile) {
            const fileExt = musicFile.name.split('.').pop()?.toLowerCase() || 'mp3';
            fetchAvailableFormats(fileExt);
        }
    }, [musicFile]);

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

    const handleFileSelect = (files: File[]) => {
        if (files.length > 0) setMusicFile(files[0]);
    };

    const handleNext = () => {
        if (currentStep === 0 && !musicFile) {
            setError('请上传音乐文件。');
            return;
        }
        setError(null);
        setCurrentStep(prev => prev + 1);
    };

    const handleBack = () => {
        setCurrentStep(prev => prev - 1);
    };

    const handleSubmit = async () => {
        if (!musicFile) return;

        setLoading(true);
        setError(null);
        setDownloadUrl(null);
        setProgress(0);
        setProgressMessage('初始化中...');
        setCurrentStep(2);

        try {
            const formData = new FormData();
            formData.append('music', musicFile);
            formData.append('output_format', outputFormat);

            const response = await axios.post(`${API_BASE_URL}/api/extract`, formData, {
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
            setError(err.response?.data?.detail || '提取失败');
        }
    };

    return (
        <div className="extractor-page">
            <Wizard
                title="节拍器提取"
                steps={['上传文件', '配置设置', '处理中']}
                currentStep={currentStep}
            >
                {currentStep === 0 && (
                    <div className="step-container">
                        <div className="upload-section full-width">
                            <h3>上传带节拍器的音乐</h3>
                            <FileUploadZone
                                id="extractor-upload"
                                onFilesSelected={handleFileSelect}
                                label={musicFile ? `已选择: ${musicFile.name}` : "拖拽音频文件到这里"}
                                accept="audio/*"
                            />
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
                        <div className="settings-grid single-column">
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
                                <small>选择提取出的节拍器格式</small>
                            </div>
                        </div>

                        <div className="wizard-actions">
                            <button className="action-button secondary" onClick={handleBack}>
                                ← 返回
                            </button>
                            <button className="action-button primary" onClick={handleSubmit}>
                                开始提取
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
                        ) : downloadUrl ? (
                            <div className="success-state">
                                <div className="success-icon">{"\u2713"}</div>
                                <h3>提取完成!</h3>
                                <p>节拍器音轨已分离。</p>

                                <div className="result-card">
                                    <div className="result-info">
                                        <span className="result-filename">{filename}</span>
                                    </div>
                                    <div className="result-actions-row">
                                        <AudioPlayer audioUrl={downloadUrl} filename={filename || 'metronome.mp3'} />
                                        <a href={downloadUrl} download={filename || 'metronome.mp3'} className="download-btn large">
                                            下载节拍器
                                        </a>
                                    </div>
                                </div>

                                <button
                                    className="action-button secondary"
                                    onClick={() => {
                                        setCurrentStep(0);
                                        setMusicFile(null);
                                        setDownloadUrl(null);
                                    }}
                                >
                                    提取另一个
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

export default Extractor;
