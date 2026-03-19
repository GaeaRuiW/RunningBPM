import React, { useState, useRef } from 'react';
import './FileUploadZone.css';

interface FileUploadZoneProps {
    onFilesSelected: (files: File[]) => void;
    accept?: string;
    multiple?: boolean;
    maxFiles?: number;
    label?: string;
    id: string;
    maxFileSize?: number;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
    onFilesSelected,
    accept = "audio/*",
    multiple = false,
    maxFiles = 10,
    label = "Drop files here or click to browse",
    id,
    maxFileSize
}) => {
    const [isDragging, setIsDragging] = useState(false);
    const [sizeError, setSizeError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const validateAndSelect = (files: File[]) => {
        setSizeError(null);
        const oversized = files.find(f => f.size > (maxFileSize || 524288000));
        if (oversized) {
            const limitMB = Math.round((maxFileSize || 524288000) / 1024 / 1024);
            setSizeError(`文件 "${oversized.name}" 超过 ${limitMB}MB 限制`);
            return;
        }
        onFilesSelected(files);
    };

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
        if (files.length > 0) validateAndSelect(files);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []).slice(0, maxFiles);
        if (files.length > 0) validateAndSelect(files);
    };

    return (
        <>
            <label
                htmlFor={id}
                className={`file-upload-zone ${isDragging ? 'dragging' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <div className="upload-icon">+</div>
                <span className="upload-label">{label}</span>
                <span className="upload-hint">支持 MP3、WAV、FLAC、M4A、OGG 格式</span>
                <input
                    ref={inputRef}
                    id={id}
                    type="file"
                    accept={accept}
                    multiple={multiple}
                    onChange={handleChange}
                />
            </label>
            {sizeError && (
                <div className="file-size-error" style={{ color: 'var(--error, #e74c3c)', fontSize: '0.85rem', marginTop: '8px' }}>
                    {sizeError}
                </div>
            )}
        </>
    );
};

export default FileUploadZone;
