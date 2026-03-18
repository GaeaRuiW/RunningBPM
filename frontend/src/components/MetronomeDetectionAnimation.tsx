import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface MetronomeDetectionAnimationProps {
    progress: number;
    message: string;
}

const MetronomeDetectionAnimation: React.FC<MetronomeDetectionAnimationProps> = ({ progress, message }) => {
    const [stage, setStage] = useState<'idle' | 'loading' | 'separating' | 'analyzing' | 'detected'>('idle');
    const [activeTrack, setActiveTrack] = useState<string | null>(null);

    useEffect(() => {
        if (progress < 5) setStage('idle');
        else if (progress < 15) setStage('loading');
        else if (progress < 50) setStage('separating');
        else if (progress < 90) setStage('analyzing');
        else setStage('detected');

        // Determine active track based on message or progress
        if (message.includes('drums') || message.includes('Drums')) setActiveTrack('Drums');
        else if (message.includes('other') || message.includes('Other')) setActiveTrack('Other');
        else if (progress >= 90) setActiveTrack('Metronome'); // Final state
    }, [progress, message]);

    // Generate random waveform data
    const generateWaveform = (points: number, amplitude: number) => {
        let d = `M 0 ${25}`;
        for (let i = 0; i <= points; i++) {
            const x = (i / points) * 100;
            // Create a more "audio-like" waveform with some randomness but clustered peaks
            const noise = (Math.random() - 0.5) * amplitude * (Math.sin(i * 0.5) + 1.5);
            const y = 25 + noise;
            d += ` L ${x} ${y}`;
        }
        return d;
    };

    const tracks = [
        { name: 'Vocals', color: '#a3d977', delay: 0 },
        { name: 'Drums', color: '#f0e68c', delay: 0.2 },
        { name: 'Bass', color: '#d65d8e', delay: 0.4 },
        { name: 'Other', color: '#9076ff', delay: 0.6 },
    ];

    return (
        <div className="metronome-animation-container" style={{
            background: '#0a0a0a', // Very dark background like the image
            borderRadius: '12px',
            padding: '24px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            color: '#fff',
            width: '100%',
            maxWidth: '700px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            border: '1px solid #222'
        }}>

            <div className="tracks-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <AnimatePresence>
                    {tracks.map((track, index) => {
                        // Logic to show/hide tracks based on stage
                        if (stage === 'idle' && index > 0) return null;
                        if (stage === 'loading' && index > 0) return null;

                        const isTarget = (track.name === activeTrack) || (stage === 'detected' && (track.name === 'Drums' || track.name === 'Other'));
                        const isDimmed = activeTrack && !isTarget && stage !== 'detected';

                        return (
                            <motion.div
                                key={track.name}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{
                                    opacity: isDimmed ? 0.4 : 1,
                                    y: 0,
                                }}
                                exit={{ opacity: 0 }}
                                transition={{ delay: track.delay, duration: 0.4 }}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    height: '56px',
                                    gap: '16px'
                                }}
                            >
                                {/* Track Label & Icon */}
                                <div style={{
                                    width: '100px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    flexShrink: 0
                                }}>
                                    <span style={{
                                        color: '#fff',
                                        fontWeight: 600,
                                        fontSize: '14px',
                                        letterSpacing: '0.5px'
                                    }}>{track.name}</span>

                                    {/* Play Button Icon */}
                                    <div style={{
                                        width: '28px',
                                        height: '28px',
                                        borderRadius: '50%',
                                        background: '#fff',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        cursor: 'default'
                                    }}>
                                        <div style={{
                                            width: 0,
                                            height: 0,
                                            borderTop: '5px solid transparent',
                                            borderBottom: '5px solid transparent',
                                            borderLeft: '8px solid #000',
                                            marginLeft: '2px'
                                        }}></div>
                                    </div>
                                </div>

                                {/* Waveform Container */}
                                <div style={{
                                    flex: 1,
                                    height: '100%',
                                    background: '#1a1a1a', // Darker inner container
                                    borderRadius: '8px',
                                    position: 'relative',
                                    overflow: 'hidden',
                                    border: '1px solid #333'
                                }}>
                                    {/* Playhead */}
                                    {(stage === 'analyzing' || stage === 'detected') && (
                                        <motion.div
                                            style={{
                                                position: 'absolute',
                                                top: 0,
                                                bottom: 0,
                                                width: '2px',
                                                background: track.color, // Playhead matches track color or white? Image shows white/light
                                                opacity: 0.8,
                                                zIndex: 10,
                                                boxShadow: `0 0 8px ${track.color}`
                                            }}
                                            animate={{ left: ['0%', '100%'] }}
                                            transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
                                        />
                                    )}

                                    {/* Waveform */}
                                    <div style={{
                                        width: '100%',
                                        height: '100%',
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '0 10px'
                                    }}>
                                        <svg width="100%" height="100%" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                                            <defs>
                                                <linearGradient id={`grad-${track.name}`} x1="0%" y1="0%" x2="100%" y2="0%">
                                                    <stop offset="0%" stopColor={track.color} stopOpacity="0.8" />
                                                    <stop offset="50%" stopColor={track.color} stopOpacity="1" />
                                                    <stop offset="100%" stopColor={track.color} stopOpacity="0.8" />
                                                </linearGradient>
                                            </defs>

                                            {/* Top half */}
                                            <motion.path
                                                d={generateWaveform(80, 20)}
                                                fill="none"
                                                stroke={`url(#grad-${track.name})`}
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                initial={{ pathLength: 0, opacity: 0 }}
                                                animate={{ pathLength: 1, opacity: 1 }}
                                                transition={{ duration: 1.5, delay: track.delay }}
                                            />
                                            {/* Bottom half (Mirror) */}
                                            <motion.path
                                                d={generateWaveform(80, 20)}
                                                fill="none"
                                                stroke={`url(#grad-${track.name})`}
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                style={{ transform: 'scaleY(-1)', transformOrigin: 'center' }}
                                                initial={{ pathLength: 0, opacity: 0 }}
                                                animate={{ pathLength: 1, opacity: 1 }}
                                                transition={{ duration: 1.5, delay: track.delay }}
                                            />
                                        </svg>
                                    </div>

                                    {/* Highlight effect for target track */}
                                    {isTarget && (
                                        <motion.div
                                            style={{
                                                position: 'absolute',
                                                top: 0,
                                                left: 0,
                                                right: 0,
                                                bottom: 0,
                                                border: `2px solid ${track.color}`,
                                                borderRadius: '8px',
                                                pointerEvents: 'none'
                                            }}
                                            animate={{ opacity: [0.5, 1, 0.5] }}
                                            transition={{ repeat: Infinity, duration: 1.5 }}
                                        />
                                    )}
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>

            <div style={{
                marginTop: '20px',
                fontSize: '13px',
                color: '#666',
                textAlign: 'center',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px'
            }}>
                {stage === 'analyzing' && <div className="spinner" style={{ width: '12px', height: '12px', border: '2px solid #666', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>}
                <span style={{ color: '#888' }}>{message}</span>
            </div>
            <style>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default MetronomeDetectionAnimation;
