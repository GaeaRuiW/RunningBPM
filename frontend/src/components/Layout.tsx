import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import InteractiveBackground from './InteractiveBackground';
import './Layout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="layout-container">
            <aside className="sidebar">
                <div className="logo-container">
                    <h1>🏃 RunningBPM</h1>
                    <p>Sonic Flow 版</p>
                </div>

                <nav className="nav-menu">
                    <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <span className="icon">🏠</span> 仪表盘
                    </NavLink>
                    <NavLink to="/mixer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <span className="icon">🎚️</span> 音频合成
                    </NavLink>
                    <NavLink to="/stitcher" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <span className="icon">🔗</span> 音乐拼接
                    </NavLink>
                    <NavLink to="/extractor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <span className="icon">🥁</span> 节拍器提取
                    </NavLink>
                </nav>

                <div className="sidebar-footer">
                    <p>© 2025 RunningBPM</p>
                </div>
            </aside>

            <main className="content-area">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                    className="page-content"
                >
                    <Outlet />
                </motion.div>
            </main>

            <InteractiveBackground />
        </div>
    );
};

export default MainLayout;
