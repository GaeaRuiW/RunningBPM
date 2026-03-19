import React, { useState, useRef } from 'react';
import './FileUploadZone.css';

interface FileUploadZoneProps {
    onFilesSelected: (files: File[]) => void;
    accept?: string;
    multiple?: boolean;
    maxFiles?: number;
    label?: string;
    id: string;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
    onFilesSelected,
    accept = "audio/*",
    multiple = false,
    maxFiles = 10,
    label = "Drop files here or click to browse",
    id
}) => {
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const files = Array.from(e.dataTransfer.files).slice(0, maxFiles);
        if (files.length > 0) onFilesSelected(files);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []).slice(0, maxFiles);
        if (files.length > 0) onFilesSelected(files);
    };

    return (
        <label
            htmlFor={id}
            className={`file-upload-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            <div className="upload-icon">+</div>
            <span className="upload-label">{label}</span>
            <span className="upload-hint">Supports MP3, WAV, FLAC, M4A, OGG</span>
            <input
                ref={inputRef}
                id={id}
                type="file"
                accept={accept}
                multiple={multiple}
                onChange={handleChange}
            />
        </label>
    );
};

export default FileUploadZone;
