import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import './Layout.css';

const MainLayout: React.FC = () => {
    return (
        <div className="layout-container">
            <nav className="sidebar">
                <div className="logo-container">
                    <h1>Running<span>BPM</span></h1>
                </div>
                <div className="nav-menu">
                    <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        Dashboard
                    </NavLink>
                    <NavLink to="/mixer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        Mixer
                    </NavLink>
                    <NavLink to="/stitcher" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        Stitcher
                    </NavLink>
                    <NavLink to="/extractor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        Extractor
                    </NavLink>
                </div>
            </nav>
            <main className="content-area">
                <div className="page-content">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={window.location.pathname}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
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
