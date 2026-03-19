import React from 'react';
import './MetronomeDetectionAnimation.css';

interface MetronomeDetectionAnimationProps {
    progress: number;
    message: string;
}

const MetronomeDetectionAnimation: React.FC<MetronomeDetectionAnimationProps> = ({ progress, message }) => {
    return (
        <div className="detect-progress">
            <div className="dp-visual">
                <div className="dp-ring dp-ring-1" />
                <div className="dp-ring dp-ring-2" />
                <div className="dp-ring dp-ring-3" />
                <div className="dp-center">
                    <svg viewBox="0 0 40 56" fill="currentColor" width="22" height="30">
                        <circle cx="22" cy="7" r="6" />
                        <path d="M18 14h8l2 12-6 8 6 10h-5l-5-9-3 9h-5l6-14-4-6z" />
                    </svg>
                </div>
            </div>
            <div className="dp-bar">
                <div className="dp-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="dp-info">
                <span className="dp-msg">{message}</span>
                <span className="dp-pct">{progress}%</span>
            </div>
        </div>
    );
};

export default MetronomeDetectionAnimation;
