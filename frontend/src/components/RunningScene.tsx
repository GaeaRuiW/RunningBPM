import React from 'react';
import './RunningScene.css';

interface RunningSceneProps {
    compact?: boolean;
    showRunner?: boolean;
}

const RunningScene: React.FC<RunningSceneProps> = ({ compact = false, showRunner = true }) => {
    return (
        <div className={`running-scene ${compact ? 'compact' : ''}`}>
            <div className="scene-sun" />
            <div className="scene-cloud cloud-1" />
            <div className="scene-cloud cloud-2" />
            <div className="scene-cloud cloud-3" />

            <div className="hill hill-far" />
            <div className="hill hill-mid" />
            <div className="hill hill-near" />

            <div className="scene-path" />

            <div className="wheat-row">
                {Array.from({ length: 14 }).map((_, i) => (
                    <div key={i} className={`wheat w${i % 4}`} />
                ))}
            </div>

            {showRunner && (
                <div className="runner-wrap">
                    <svg className="runner-svg" viewBox="0 0 40 56" fill="currentColor">
                        <circle cx="22" cy="7" r="6" />
                        <path d="M18 14h8l2 12-6 8 6 10h-5l-5-9-3 9h-5l6-14-4-6z" />
                        <path d="M14 18l-7-3 1-3 8 4M28 18l5-5 2 2-6 6" opacity=".85" />
                    </svg>
                </div>
            )}
        </div>
    );
};

export default RunningScene;
