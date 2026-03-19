import React from 'react';
import { Link } from 'react-router-dom';
import RunningScene from '../components/RunningScene';
import './Dashboard.css';

const Dashboard: React.FC = () => {
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
        </div>
    );
};

export default Dashboard;
