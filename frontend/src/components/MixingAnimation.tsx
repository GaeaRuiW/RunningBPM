import React from 'react';
import './MixingAnimation.css';

interface MixingAnimationProps {
    progress: number;
    message: string;
}

const MixingAnimation: React.FC<MixingAnimationProps> = ({ progress, message }) => {
    return (
        <div className="running-progress">
            <div className="rp-scene">
                <div className="rp-trail" />
                <div className="rp-trail-fill" style={{ width: `${progress}%` }} />
                <div className="rp-runner" style={{ left: `${Math.min(progress, 96)}%` }}>
                    <svg viewBox="0 0 40 56" fill="currentColor" width="20" height="28">
                        <circle cx="22" cy="7" r="6" />
                        <path d="M18 14h8l2 12-6 8 6 10h-5l-5-9-3 9h-5l6-14-4-6z" />
                    </svg>
                </div>
            </div>
            <div className="rp-info">
                <span className="rp-msg">{message}</span>
                <span className="rp-pct">{progress}%</span>
            </div>
        </div>
    );
};

export default MixingAnimation;
