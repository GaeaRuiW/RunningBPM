import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import './Layout.css';

const MainLayout: React.FC = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="layout-container">
            {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
            <nav className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
                <div className="logo-container">
                    <h1>Running<span>BPM</span></h1>
                    <div className="logo-sub">跑步音乐制作工具</div>
                </div>
                <div className="nav-menu">
                    <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                        首页
                    </NavLink>
                    <NavLink to="/mixer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                        音频合成
                    </NavLink>
                    <NavLink to="/stitcher" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                        音乐拼接
                    </NavLink>
                    <NavLink to="/extractor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                        节拍器提取
                    </NavLink>
                </div>
            </nav>
            <main className="content-area">
                <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="菜单">
                    <span /><span /><span />
                </button>
                <div className="page-content">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={window.location.pathname}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.18 }}
                        >
                            <Outlet />
                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
};

export default MainLayout;
