import React from 'react';

interface MetronomeDetectionAnimationProps {
    progress: number;
    message: string;
}

const MetronomeDetectionAnimation: React.FC<MetronomeDetectionAnimationProps> = ({ progress, message }) => {
    return (
        <div className="loading-indicator">
            <div className="spinner" />
            <p>{message}</p>
        </div>
    );
};

export default MetronomeDetectionAnimation;
