import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const InteractiveBackground: React.FC = () => {
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
    const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            setMousePosition({
                x: e.clientX,
                y: e.clientY
            });
        };

        const handleResize = () => {
            setDimensions({
                width: window.innerWidth,
                height: window.innerHeight
            });
        };

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    // Generate random runners
    const runners = Array.from({ length: 15 }).map((_, i) => ({
        id: i,
        duration: 10 + Math.random() * 15,
        delay: Math.random() * 5,
        y: Math.random() * 100,
        size: 4 + Math.random() * 6
    }));

    // Dynamic path based on screen width
    const pathD = `M0,${dimensions.height * 0.5} 
                   Q${dimensions.width * 0.25},${dimensions.height * 0.2} ${dimensions.width * 0.5},${dimensions.height * 0.5} 
                   T${dimensions.width},${dimensions.height * 0.5}`;

    return (
        <div className="interactive-background" style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            overflow: 'hidden',
            zIndex: 0,
            pointerEvents: 'none'
        }}>
            {/* Ambient Gradient Mesh - Made slightly more visible */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: `
                    radial-gradient(circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(99, 102, 241, 0.25) 0%, transparent 40%),
                    radial-gradient(circle at 85% 30%, rgba(168, 85, 247, 0.2) 0%, transparent 50%)
                `,
                transition: 'background 0.1s ease'
            }} />

            {/* Running Lines (Heartbeat / Path) - Increased opacity and stroke width */}
            <svg style={{ position: 'absolute', width: '100%', height: '100%', opacity: 0.6 }}>
                <motion.path
                    d={pathD}
                    fill="none"
                    stroke="url(#gradient-line)"
                    strokeWidth="4"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 3, ease: "easeInOut" }}
                />
                {/* Second echo line */}
                <motion.path
                    d={pathD}
                    fill="none"
                    stroke="url(#gradient-line)"
                    strokeWidth="2"
                    style={{ translateY: 20, opacity: 0.5 }}
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 4, delay: 0.5, ease: "easeInOut" }}
                />
                <defs>
                    <linearGradient id="gradient-line" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="rgba(99, 102, 241, 0)" />
                        <stop offset="50%" stopColor="rgba(168, 85, 247, 0.8)" />
                        <stop offset="100%" stopColor="rgba(99, 102, 241, 0)" />
                    </linearGradient>
                </defs>
            </svg>

            {/* Ambient Runners (Particles) - Brighter and larger */}
            {runners.map((runner) => (
                <motion.div
                    key={runner.id}
                    style={{
                        position: 'absolute',
                        left: '-50px',
                        top: `${runner.y}%`,
                        width: runner.size,
                        height: runner.size,
                        borderRadius: '50%',
                        background: '#fff',
                        boxShadow: '0 0 15px rgba(255, 255, 255, 0.8), 0 0 30px rgba(168, 85, 247, 0.4)'
                    }}
                    animate={{
                        x: ['-5vw', '105vw'],
                        opacity: [0, 1, 1, 0]
                    }}
                    transition={{
                        duration: runner.duration,
                        repeat: Infinity,
                        delay: runner.delay,
                        ease: "linear"
                    }}
                />
            ))}

            {/* Interactive Cursor Follower - More distinct */}
            <motion.div
                animate={{
                    x: mousePosition.x - 150,
                    y: mousePosition.y - 150
                }}
                transition={{ type: "spring", damping: 25, stiffness: 150 }}
                style={{
                    position: 'absolute',
                    width: 300,
                    height: 300,
                    borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
                    pointerEvents: 'none',
                    mixBlendMode: 'screen'
                }}
            />
        </div>
    );
};

export default InteractiveBackground;
