import React, { useState, useRef } from 'react';

interface AudioPlayerProps {
    audioUrl: string;
    filename: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, filename }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const audioRef = useRef<HTMLAudioElement>(null);

    const togglePlay = () => {
        if (!audioRef.current) return;
        if (isPlaying) {
            audioRef.current.pause();
        } else {
            audioRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleEnded = () => setIsPlaying(false);

    return (
        <button
            onClick={togglePlay}
            className="action-button secondary"
            style={{ padding: '8px 14px', fontSize: '0.85rem' }}
            title={isPlaying ? 'Pause' : 'Play'}
        >
            {isPlaying ? '\u23F8' : '\u25B6'}
            <audio ref={audioRef} src={audioUrl} onEnded={handleEnded} />
        </button>
    );
};

export default AudioPlayer;
