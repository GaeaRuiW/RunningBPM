import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import RunningScene from '../components/RunningScene';
import PaceCalculator from '../components/PaceCalculator';
import './Dashboard.css';

interface HistoryEntry {
    id: string;
    type: string;
    timestamp: number;
    inputFiles: string[];
    resultFiles: { filename: string; downloadUrl: string }[];
}

const Dashboard: React.FC = () => {
    const [history, setHistory] = useState<HistoryEntry[]>([]);

    useEffect(() => {
        try {
            const stored = localStorage.getItem('runningbpm_history');
            if (stored) setHistory(JSON.parse(stored));
        } catch {}
    }, []);

    const clearHistory = () => {
        localStorage.removeItem('runningbpm_history');
        setHistory([]);
    };

    const formatTime = (ts: number) => {
        const d = new Date(ts);
        return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
    };

    const typeLabel: Record<string, string> = {
        combine: '合成', extract: '提取', concatenate: '拼接'
    };

    return (
        <div className="dashboard">
            <div className="dashboard-hero">
                <h1>准备好了吗，开始奔跑！</h1>
                <p>选择一个工具，制作属于你的跑步音乐</p>
                <RunningScene />
            </div>
            <div className="tools-grid">
                <Link to="/mixer" className="tool-card">
                    <h3>音频合成</h3>
                    <p>将你的音乐与自定义节拍器混合，生成指定 BPM 的跑步音乐</p>
                    <span className="card-arrow">进入合成 &rarr;</span>
                </Link>
                <Link to="/stitcher" className="tool-card">
                    <h3>音乐拼接</h3>
                    <p>将多首曲目无缝拼接为一段连续的跑步歌单</p>
                    <span className="card-arrow">进入拼接 &rarr;</span>
                </Link>
                <Link to="/extractor" className="tool-card">
                    <h3>节拍器提取</h3>
                    <p>从已有的跑步音乐中分离并提取节拍器音轨</p>
                    <span className="card-arrow">进入提取 &rarr;</span>
                </Link>
            </div>
            <div className="dashboard-bottom-grid">
                <PaceCalculator />
                {history.length > 0 && (
                    <div className="history-section">
                        <div className="history-header">
                            <h3>最近处理</h3>
                            <button className="history-clear" onClick={clearHistory}>清空</button>
                        </div>
                        <div className="history-list">
                            {history.slice(0, 8).map(entry => (
                                <div key={entry.id} className="history-item">
                                    <span className="history-type">{typeLabel[entry.type] || entry.type}</span>
                                    <span className="history-files">{entry.inputFiles.join(', ')}</span>
                                    <span className="history-time">{formatTime(entry.timestamp)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
