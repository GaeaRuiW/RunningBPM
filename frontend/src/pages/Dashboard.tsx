import React from 'react';
import { Link } from 'react-router-dom';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>Welcome back, runner</h1>
                <p>Choose a tool to get started with your running music.</p>
            </div>
            <div className="tools-grid">
                <Link to="/mixer" className="tool-card">
                    <h3>Mixer</h3>
                    <p>Combine your music with a custom metronome beat at your target BPM.</p>
                    <span className="card-arrow">Open Mixer &rarr;</span>
                </Link>
                <Link to="/stitcher" className="tool-card">
                    <h3>Stitcher</h3>
                    <p>Stitch multiple tracks into one continuous running playlist.</p>
                    <span className="card-arrow">Open Stitcher &rarr;</span>
                </Link>
                <Link to="/extractor" className="tool-card">
                    <h3>Extractor</h3>
                    <p>Extract the metronome beat from existing running music.</p>
                    <span className="card-arrow">Open Extractor &rarr;</span>
                </Link>
            </div>
        </div>
    );
};

export default Dashboard;
