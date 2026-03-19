import React, { useState } from 'react';
import './PaceCalculator.css';

const PaceCalculator: React.FC = () => {
    const [paceMin, setPaceMin] = useState(5);
    const [paceSec, setPaceSec] = useState(30);

    // Common running cadence formula:
    // Slower pace = lower cadence, faster = higher
    // Approximate: BPM ≈ 230 - (pace_in_minutes * 10)
    // Clamped to reasonable range
    const paceTotal = paceMin + paceSec / 60;
    const recommendedBPM = Math.round(Math.max(120, Math.min(200, 230 - paceTotal * 10)));

    const presets = [
        { label: '散步', pace: '8:00', bpm: 100 },
        { label: '慢跑', pace: '6:30', bpm: 150 },
        { label: '跑步', pace: '5:00', bpm: 170 },
        { label: '快跑', pace: '4:00', bpm: 190 },
    ];

    return (
        <div className="pace-calc">
            <h3>配速计算器</h3>
            <div className="pace-input-row">
                <label>配速 (分/公里)</label>
                <div className="pace-inputs">
                    <input type="number" min={3} max={12} value={paceMin}
                        onChange={e => setPaceMin(parseInt(e.target.value) || 5)} />
                    <span>:</span>
                    <input type="number" min={0} max={59} value={paceSec}
                        onChange={e => setPaceSec(parseInt(e.target.value) || 0)} />
                </div>
            </div>
            <div className="pace-result">
                推荐 BPM: <strong>{recommendedBPM}</strong>
            </div>
            <div className="pace-presets">
                {presets.map(p => (
                    <button key={p.label} className="pace-preset-btn"
                        onClick={() => { setPaceMin(parseInt(p.pace)); setPaceSec(parseInt(p.pace.split(':')[1])); }}>
                        {p.label} {p.pace} → {p.bpm}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default PaceCalculator;
