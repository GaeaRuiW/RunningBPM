import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './Wizard.css';

interface WizardProps {
    steps: string[];
    currentStep: number;
    children: React.ReactNode;
    title: string;
}

const Wizard: React.FC<WizardProps> = ({ steps, currentStep, children, title }) => {
    return (
        <div className="wizard-container">
            <div className="wizard-header">
                <h2>{title}</h2>
                <div className="steps-indicator">
                    {steps.map((step, index) => (
                        <div
                            key={index}
                            className={`step-item ${index <= currentStep ? 'active' : ''} ${index === currentStep ? 'current' : ''}`}
                        >
                            <div className="step-number">
                                {index < currentStep ? '✓' : index + 1}
                            </div>
                            <span className="step-label">{step}</span>
                            {index < steps.length - 1 && <div className="step-line" />}
                        </div>
                    ))}
                </div>
            </div>

            <div className="wizard-content">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ x: 20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: -20, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="step-content"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Wizard;
