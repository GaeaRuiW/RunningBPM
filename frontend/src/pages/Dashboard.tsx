import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const Dashboard: React.FC = () => {
    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <div className="dashboard">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="dashboard-header"
            >
                <h1>欢迎回来，跑者！🏃‍♂️</h1>
                <p>准备好制作你的完美跑步歌单了吗？</p>
            </motion.div>

            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="tools-grid"
            >
                <motion.div variants={item}>
                    <Link to="/mixer" className="tool-card mixer-card">
                        <div className="card-icon">🎚️</div>
                        <h2>音频合成</h2>
                        <p>将你的音乐与自定义节拍器结合，打造完美步频。</p>
                        <span className="arrow">→</span>
                    </Link>
                </motion.div>

                <motion.div variants={item}>
                    <Link to="/stitcher" className="tool-card stitcher-card">
                        <div className="card-icon">🔗</div>
                        <h2>音乐拼接</h2>
                        <p>无缝拼接多首曲目，制作连续的跑步音乐。</p>
                        <span className="arrow">→</span>
                    </Link>
                </motion.div>

                <motion.div variants={item}>
                    <Link to="/extractor" className="tool-card extractor-card">
                        <div className="card-icon">🥁</div>
                        <h2>节拍器提取</h2>
                        <p>从现有跑步音乐中分离并提取节拍。</p>
                        <span className="arrow">→</span>
                    </Link>
                </motion.div>
            </motion.div>
        </div>
    );
};

export default Dashboard;
