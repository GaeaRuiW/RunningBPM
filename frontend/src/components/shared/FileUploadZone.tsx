import React, { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import './FileUploadZone.css';

interface FileUploadZoneProps {
    onFilesSelected: (files: File[]) => void;
    accept?: string;
    multiple?: boolean;
    maxFiles?: number;
    label?: string;
    id?: string;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
    onFilesSelected,
    accept = "audio/*",
    multiple = false,
    maxFiles = 10,
    label = "拖拽音频文件到这里，或点击上传",
    id = "file-upload-input"
}) => {
    const [isDragging, setIsDragging] = useState(false);

    const handleDragEnter = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            onFilesSelected(files);
        }
    }, [onFilesSelected]);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            onFilesSelected(files);
        }
    }, [onFilesSelected]);

    return (
        <motion.div
            className={`file-upload-zone ${isDragging ? 'dragging' : ''}`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            animate={isDragging ? { scale: 1.02, borderColor: '#a855f7', backgroundColor: 'rgba(168, 85, 247, 0.1)' } : {}}
        >
            <input
                type="file"
                accept={accept}
                multiple={multiple}
                onChange={handleFileInput}
                className="file-input-hidden"
                id={id}
            />
            <label htmlFor={id} className="upload-label">
                <motion.div
                    className="upload-icon"
                    animate={isDragging ? { y: [0, -10, 0] } : {}}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                >
                    ☁️
                </motion.div>
                <h3>{isDragging ? "快松手! 🔥" : "上传音频"}</h3>
                <p>{label}</p>
                <div className="upload-hint">
                    支持格式: MP3, WAV, FLAC {multiple ? `(最多 ${maxFiles} 个文件)` : ''}
                </div>
            </label>

            {isDragging && (
                <motion.div
                    className="pulse-ring"
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1.5, opacity: 0 }}
                    transition={{ duration: 1, repeat: Infinity }}
                />
            )}
        </motion.div>
    );
};

export default FileUploadZone;
