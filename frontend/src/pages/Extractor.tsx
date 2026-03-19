import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import Wizard from '../components/shared/Wizard';
import FileUploadZone from '../components/shared/FileUploadZone';
import AudioPlayer from '../components/AudioPlayer';
import { API_BASE_URL } from '../config';
import './Extractor.css';

interface OutputFile {
    download_url: string;
    filename: string;
}

const Extractor: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(0);
    const [musicFiles, setMusicFiles] = useState<File[]>([]);
    const [outputFormat, setOutputFormat] = useState<string>('mp3');
    const [availableFormats, setAvailableFormats] = useState<string[]>(['mp3']);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
    const [filename, setFilename] = useState<string | null>(null);
    const [outputFiles, setOutputFiles] = useState<OutputFile[]>([]);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [progress, setProgress] = useState<number>(0);
    const [progressMessage, setProgressMessage] = useState<string>('');
    const [, setPollErrors] = useState(0);
    const [pollStartTime] = useState<number>(Date.now());
    const [cancelling, setCancelling] = useState(false);

    // Audio preview URLs
    const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});

    useEffect(() => {
        if (musicFiles.length > 0) {
            const fileExt = musicFiles[0].name.split('.').pop()?.toLowerCase() || 'mp3';
            fetchAvailableFormats(fileExt);
        }
    }, [musicFiles]);

    // After musicFiles change, update preview URLs
    useEffect(() => {
        const urls: Record<string, string> = {};
        musicFiles.forEach(f => {
            if (!previewUrls[f.name]) {
                urls[f.name] = URL.createObjectURL(f);
            } else {
                urls[f.name] = previewUrls[f.name];
            }
        });
        setPreviewUrls(urls);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [musicFiles]);

    useEffect(() => {
        if (!taskId || !loading) return;

        const fetchProgress = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/progress/${taskId}`);
                setProgress(response.data.progress);
                setProgressMessage(response.data.message);
                setPollErrors(0);

                if (response.data.status === 'completed') {
                    setLoading(false);
                    if (response.data.result) {
                        if (response.data.result.files) {
                            // Batch result
                            const files = response.data.result.files.map((file: OutputFile) => ({
                                download_url: `${API_BASE_URL}${file.download_url}`,
                                filename: file.filename
                            }));
                            setOutputFiles(files);
                        } else {
                            // Single result
                            setDownloadUrl(`${API_BASE_URL}${response.data.result.download_url}`);
                            setFilename(response.data.result.filename);
                        }

                        // Save to history
                        try {
                            const resultFiles = response.data.result.files
                                ? response.data.result.files.map((file: OutputFile) => ({
                                    filename: file.filename,
                                    downloadUrl: `${API_BASE_URL}${file.download_url}`
                                }))
                                : [{
                                    filename: response.data.result.filename,
                                    downloadUrl: `${API_BASE_URL}${response.data.result.download_url}`
                                }];
                            const hist = JSON.parse(localStorage.getItem('runningbpm_history') || '[]');
                            hist.unshift({
                                id: taskId,
                                type: 'extract',
                                timestamp: Date.now(),
                                inputFiles: musicFiles.map(f => f.name),
                                resultFiles
                            });
                            localStorage.setItem('runningbpm_history', JSON.stringify(hist.slice(0, 20)));
                        } catch {}
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
                setPollErrors(prev => {
                    const newCount = prev + 1;
                    if (newCount >= 5) {
                        setLoading(false);
                        setError('无法连接服务器，请检查网络后重试');
                        return 0;
                    }
                    return newCount;
                });
                // Timeout after 30 minutes
                if (Date.now() - pollStartTime > 30 * 60 * 1000) {
                    setLoading(false);
                    setError('处理超时，请重试');
                    return true;
                }
                return false;
            }
        };

        fetchProgress();
        const interval = setInterval(async () => {
            const done = await fetchProgress();
            if (done) clearInterval(interval);
        }, 1000);

        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        setMusicFiles(prev => [...prev, ...files]);
    };

    const handleRemoveMusic = (index: number) => {
        setMusicFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleNext = () => {
        if (currentStep === 0 && musicFiles.length === 0) {
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
        if (musicFiles.length === 0) return;

        setLoading(true);
        setError(null);
        setDownloadUrl(null);
        setOutputFiles([]);
        setProgress(0);
        setProgressMessage('初始化中...');
        setCurrentStep(2);

        try {
            const formData = new FormData();
            formData.append('output_format', outputFormat);

            let response;
            if (musicFiles.length === 1) {
                // Use existing /api/extract
                formData.append('music', musicFiles[0]);
                response = await axios.post(`${API_BASE_URL}/api/extract`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
            } else {
                // Use /api/extract-batch
                musicFiles.forEach(f => formData.append('music_files', f));
                response = await axios.post(`${API_BASE_URL}/api/extract-batch`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
            }

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

    const handleCancel = async () => {
        if (!taskId) return;
        setCancelling(true);
        try {
            await axios.post(`${API_BASE_URL}/api/cancel/${taskId}`);
            setLoading(false);
            setError('任务已取消');
            setCurrentStep(1);
        } catch (err) {
            console.error('Cancel failed:', err);
        }
        setCancelling(false);
    };

    const isBatchMode = musicFiles.length > 1;

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
                                label={musicFiles.length > 0 ? `已选择 ${musicFiles.length} 个文件` : "拖拽音频文件到这里"}
                                multiple={true}
                                accept="audio/*"
                            />
                            {musicFiles.length > 0 && (
                                <div className="file-list-preview">
                                    {musicFiles.map((f, i) => (
                                        <div key={i} className="file-preview-item">
                                            {previewUrls[f.name] && (
                                                <button className="file-action-btn" onClick={() => {
                                                    const a = new Audio(previewUrls[f.name]);
                                                    a.play();
                                                }} title="试听">&#9654;</button>
                                            )}
                                            <span className="file-name">{f.name}</span>
                                            <button className="file-remove-btn" onClick={() => handleRemoveMusic(i)} title="移除">&times;</button>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {isBatchMode && (
                                <div className="batch-notice">
                                    批量模式: 将同时提取 {musicFiles.length} 个文件的节拍器
                                </div>
                            )}
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
                                返回
                            </button>
                            <button className="action-button primary" onClick={handleSubmit}>
                                开始提取{isBatchMode ? ` (${musicFiles.length} 个文件)` : ''}
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
                                <button className="action-button secondary" onClick={handleCancel} disabled={cancelling}>
                                    {cancelling ? '取消中...' : '取消任务'}
                                </button>
                            </div>
                        ) : (downloadUrl || outputFiles.length > 0) ? (
                            <div className="success-state">
                                <div className="success-icon">{"\u2713"}</div>
                                <h3>提取完成!</h3>
                                <p>节拍器音轨已分离。</p>

                                {outputFiles.length > 0 ? (
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
                                ) : (
                                    <div className="result-card">
                                        <div className="result-info">
                                            <span className="result-filename">{filename}</span>
                                        </div>
                                        <div className="result-actions-row">
                                            <AudioPlayer audioUrl={downloadUrl!} filename={filename || 'metronome.mp3'} />
                                            <a href={downloadUrl!} download={filename || 'metronome.mp3'} className="download-btn large">
                                                下载节拍器
                                            </a>
                                        </div>
                                    </div>
                                )}

                                <button
                                    className="action-button secondary"
                                    onClick={() => {
                                        setCurrentStep(0);
                                        setMusicFiles([]);
                                        setDownloadUrl(null);
                                        setOutputFiles([]);
                                        setTaskId(null);
                                        // Don't reset outputFormat
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
