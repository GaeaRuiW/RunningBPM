import React from 'react';
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
                        <React.Fragment key={index}>
                            <div className={`step-item ${index < currentStep ? 'completed' : ''} ${index === currentStep ? 'current' : ''}`}>
                                <div className="step-number">
                                    {index < currentStep ? '\u2713' : index + 1}
                                </div>
                                <span className="step-name">{step}</span>
                            </div>
                            {index < steps.length - 1 && (
                                <div className={`step-line ${index < currentStep ? 'completed' : ''}`} />
                            )}
                        </React.Fragment>
                    ))}
                </div>
            </div>
            <div className="wizard-content">
                {children}
            </div>
        </div>
    );
};

export default Wizard;
