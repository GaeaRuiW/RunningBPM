import React from 'react';
import './AudioVisualizer.css';

interface AudioVisualizerProps {
    isPlaying?: boolean;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ isPlaying = false }) => {
    return (
        <div className={`visualizer-container ${isPlaying ? 'playing' : ''}`}>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
        </div>
    );
};

export default AudioVisualizer;
