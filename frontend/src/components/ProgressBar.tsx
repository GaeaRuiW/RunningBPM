import React from 'react';
import '../App.css';

interface ProgressBarProps {
  progress: number;
  message: string;
  status: 'processing' | 'completed' | 'failed';
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, message, status }) => {
  return (
    <div className="progress-container">
      <div className="progress-info">
        <span className="progress-message">{message}</span>
        <span className="progress-percentage">{progress}%</span>
      </div>
      <div className="progress-bar-wrapper">
        <div
          className={`progress-bar ${status}`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;

