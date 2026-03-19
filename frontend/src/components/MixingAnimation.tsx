import React from 'react';

interface MixingAnimationProps {
    progress: number;
    message: string;
}

const MixingAnimation: React.FC<MixingAnimationProps> = ({ progress, message }) => {
    return (
        <div className="loading-indicator">
            <div className="spinner" />
            <p>{message}</p>
        </div>
    );
};

export default MixingAnimation;
