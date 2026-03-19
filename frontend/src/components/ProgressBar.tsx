import React from 'react';

interface ProgressBarProps {
  progress: number;
  message: string;
  status: 'processing' | 'completed' | 'failed';
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, message, status }) => {
  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
        <span style={{ color: 'var(--text-secondary)' }}>{message}</span>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{progress}%</span>
      </div>
      <div className="progress-bar-container">
        <div
          className="progress-fill"
          style={{
            width: `${progress}%`,
            background: status === 'failed' ? 'var(--error)' : status === 'completed' ? 'var(--success)' : 'var(--accent)'
          }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
