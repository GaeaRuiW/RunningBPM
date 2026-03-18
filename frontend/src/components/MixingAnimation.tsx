import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface MixingAnimationProps {
    progress: number;
    message: string;
}

const MixingAnimation: React.FC<MixingAnimationProps> = ({ progress, message }) => {
    const [isDucking, setIsDucking] = useState(false);

    useEffect(() => {
        // Enable ducking animation during mixing phase
        if (progress > 70 && progress < 90) {
            const interval = setInterval(() => {
                setIsDucking(prev => !prev);
            }, 500); // Simulate beat
            return () => clearInterval(interval);
        } else {
            setIsDucking(false);
        }
    }, [progress]);

    // Improved waveform generation
    const generateWaveform = (points: number, amplitude: number) => {
        let d = `M 0 ${30}`;
        for (let i = 0; i <= points; i++) {
            const x = (i / points) * 100;
            const noise = (Math.random() - 0.5) * amplitude * (Math.sin(i * 0.5) + 1.5);
            const y = 30 + noise;
            d += ` L ${x} ${y}`;
        }
        return d;
    };

    return (
        <div className="mixing-animation-container" style={{
            background: '#0a0a0a',
            borderRadius: '12px',
            padding: '24px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            color: '#fff',
            width: '100%',
            maxWidth: '700px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            border: '1px solid #222'
        }}>

            <div className="mixer-visual" style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* Music Track (Top) */}
                <div style={{ display: 'flex', alignItems: 'center', height: '56px', gap: '16px' }}>
                    <div style={{ width: '100px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '14px' }}>Music</span>
                        <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{ width: 0, height: 0, borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '8px solid #000', marginLeft: '2px' }}></div>
                        </div>
                    </div>

                    <div style={{ flex: 1, height: '100%', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #333', position: 'relative', overflow: 'hidden' }}>
                        <motion.div
                            animate={{
                                scaleY: isDucking ? 0.8 : 1,
                                opacity: isDucking ? 0.8 : 1
                            }}
                            transition={{ duration: 0.1 }}
                            style={{ height: '100%', width: '100%', display: 'flex', alignItems: 'center', padding: '0 10px' }}
                        >
                            <svg width="100%" height="100%" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                                <defs>
                                    <linearGradient id="grad-music" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stopColor="#4a90e2" stopOpacity="0.8" />
                                        <stop offset="50%" stopColor="#4a90e2" stopOpacity="1" />
                                        <stop offset="100%" stopColor="#4a90e2" stopOpacity="0.8" />
                                    </linearGradient>
                                </defs>
                                <path d={generateWaveform(100, 25)} fill="none" stroke="url(#grad-music)" strokeWidth="2" strokeLinecap="round" />
                                <path d={generateWaveform(100, 25)} fill="none" stroke="url(#grad-music)" strokeWidth="2" strokeLinecap="round" style={{ transform: 'scaleY(-1)', transformOrigin: 'center' }} />
                            </svg>
                        </motion.div>
                    </div>
                </div>

                {/* Connection Lines (Sidechain) */}
                <div style={{ height: '20px', position: 'relative' }}>
                    {progress > 70 && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            style={{
                                position: 'absolute',
                                left: '50%',
                                top: 0,
                                bottom: 0,
                                width: '2px',
                                background: '#f5a623',
                                transform: 'translateX(-50%)',
                                zIndex: 10
                            }}
                        >
                            <motion.div
                                animate={{ top: ['100%', '0%'] }}
                                transition={{ repeat: Infinity, duration: 0.5 }}
                                style={{
                                    position: 'absolute',
                                    width: '8px',
                                    height: '8px',
                                    background: '#fff',
                                    borderRadius: '50%',
                                    left: '-3px',
                                    boxShadow: '0 0 8px #f5a623'
                                }}
                            />
                        </motion.div>
                    )}
                </div>

                {/* Metronome Track (Bottom) */}
                <div style={{ display: 'flex', alignItems: 'center', height: '56px', gap: '16px' }}>
                    <div style={{ width: '100px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '14px' }}>Metronome</span>
                        <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{ width: 0, height: 0, borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '8px solid #000', marginLeft: '2px' }}></div>
                        </div>
                    </div>

                    <div style={{ flex: 1, height: '100%', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #333', position: 'relative', overflow: 'hidden' }}>
                        <motion.div
                            initial={{ y: 50, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={{ duration: 0.5 }}
                            style={{ height: '100%', width: '100%', display: 'flex', alignItems: 'center', padding: '0 10px' }}
                        >
                            <svg width="100%" height="100%" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                                <defs>
                                    <linearGradient id="grad-metro" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stopColor="#f5a623" stopOpacity="0.8" />
                                        <stop offset="50%" stopColor="#f5a623" stopOpacity="1" />
                                        <stop offset="100%" stopColor="#f5a623" stopOpacity="0.8" />
                                    </linearGradient>
                                </defs>
                                {/* Spiky metronome waveform */}
                                <path d="M0 30 L10 30 L12 5 L14 55 L16 30 L30 30 L32 5 L34 55 L36 30 L50 30 L52 5 L54 55 L56 30 L70 30 L72 5 L74 55 L76 30 L90 30 L92 5 L94 55 L96 30 L100 30"
                                    fill="none"
                                    stroke="url(#grad-metro)"
                                    strokeWidth="2"
                                    vectorEffect="non-scaling-stroke"
                                    strokeLinecap="round"
                                />
                            </svg>
                        </motion.div>
                    </div>
                </div>

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
                {progress > 70 && progress < 90 && <div className="spinner" style={{ width: '12px', height: '12px', border: '2px solid #666', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>}
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

export default MixingAnimation;
