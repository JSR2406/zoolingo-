import React, { useState, useRef, useCallback } from 'react';
import { Mic, Square, Loader2, Upload, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const AudioRecorder = ({ onRecordingComplete, isProcessing }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [isDragOver, setIsDragOver] = useState(false);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const timerRef = useRef(null);
    const fileInputRef = useRef(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Use a more compatible format
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm';

            mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
            chunksRef.current = [];
            setRecordingTime(0);

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorderRef.current.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                const file = new File([blob], "recording.webm", { type: 'audio/webm' });
                onRecordingComplete(file);
            };

            mediaRecorderRef.current.start(100); // Collect data every 100ms
            setIsRecording(true);

            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Could not access microphone. Please ensure permissions are granted.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            clearInterval(timerRef.current);

            // Stop all tracks
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
    };

    const handleFileUpload = (file) => {
        if (file) {
            const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/webm', 'audio/m4a', 'audio/flac'];
            if (!allowedTypes.some(type => file.type.includes(type.split('/')[1]))) {
                alert('Please upload a valid audio file (WAV, MP3, OGG, FLAC, M4A, or WebM)');
                return;
            }
            onRecordingComplete(file);
        }
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(false);
        const file = e.dataTransfer.files[0];
        handleFileUpload(file);
    }, []);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = () => {
        setIsDragOver(false);
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col items-center justify-center p-6 space-y-6">
            {/* Main Record Button */}
            <div className="relative">
                {/* Pulse Rings when recording */}
                <AnimatePresence>
                    {isRecording && (
                        <>
                            <motion.div
                                className="absolute inset-0 rounded-full border-2 border-red-500"
                                initial={{ scale: 1, opacity: 1 }}
                                animate={{ scale: 1.5, opacity: 0 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                            />
                            <motion.div
                                className="absolute inset-0 rounded-full border-2 border-red-500"
                                initial={{ scale: 1, opacity: 1 }}
                                animate={{ scale: 1.8, opacity: 0 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 1.5, repeat: Infinity, delay: 0.5 }}
                            />
                        </>
                    )}
                </AnimatePresence>

                <motion.button
                    whileHover={{ scale: isProcessing ? 1 : 1.05 }}
                    whileTap={{ scale: isProcessing ? 1 : 0.95 }}
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isProcessing}
                    className={`
                        relative flex items-center justify-center w-28 h-28 rounded-full transition-all duration-300 z-10
                        ${isRecording
                            ? 'bg-gradient-to-br from-red-500 to-red-600 glow-red recording-pulse'
                            : 'bg-gradient-to-br from-primary to-primary-dark glow-green'
                        }
                        ${isProcessing
                            ? 'opacity-50 cursor-not-allowed'
                            : 'cursor-pointer hover:shadow-2xl'
                        }
                    `}
                >
                    <AnimatePresence mode="wait">
                        {isProcessing ? (
                            <motion.div
                                key="loading"
                                initial={{ opacity: 0, scale: 0.5 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.5 }}
                            >
                                <Loader2 className="w-12 h-12 text-white animate-spin" />
                            </motion.div>
                        ) : isRecording ? (
                            <motion.div
                                key="stop"
                                initial={{ opacity: 0, scale: 0.5 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.5 }}
                            >
                                <Square className="w-10 h-10 text-white fill-current" />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="mic"
                                initial={{ opacity: 0, scale: 0.5 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.5 }}
                            >
                                <Mic className="w-12 h-12 text-white" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.button>
            </div>

            {/* Recording Timer */}
            <AnimatePresence>
                {isRecording && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="flex items-center space-x-2"
                    >
                        <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                        <span className="text-red-400 font-mono text-lg font-semibold">
                            {formatTime(recordingTime)}
                        </span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Status Text */}
            <motion.p
                className="text-text-secondary font-medium text-center"
                animate={{ opacity: 1 }}
            >
                {isProcessing
                    ? "Analyzing sound..."
                    : isRecording
                        ? "Listening to your pet..."
                        : "Tap to record animal sound"
                }
            </motion.p>

            {/* Divider */}
            <div className="flex items-center w-full max-w-xs">
                <div className="flex-1 h-px bg-glass-border" />
                <span className="px-4 text-text-muted text-sm">or</span>
                <div className="flex-1 h-px bg-glass-border" />
            </div>

            {/* File Upload Area */}
            <motion.div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => !isProcessing && fileInputRef.current?.click()}
                whileHover={{ scale: isProcessing ? 1 : 1.02 }}
                className={`
                    relative w-full max-w-xs p-6 rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer
                    ${isDragOver
                        ? 'border-primary bg-primary/10'
                        : 'border-glass-border hover:border-text-muted'
                    }
                    ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
                `}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    className="hidden"
                    onChange={(e) => handleFileUpload(e.target.files?.[0])}
                    disabled={isProcessing}
                />
                <div className="flex flex-col items-center space-y-2">
                    <Upload className={`w-8 h-8 ${isDragOver ? 'text-primary' : 'text-text-muted'}`} />
                    <p className={`text-sm text-center ${isDragOver ? 'text-primary' : 'text-text-muted'}`}>
                        Drop audio file here or click to upload
                    </p>
                    <p className="text-xs text-text-muted">
                        WAV, MP3, OGG, FLAC, M4A
                    </p>
                </div>
            </motion.div>

            {/* Waveform Animation when Recording */}
            <AnimatePresence>
                {isRecording && (
                    <motion.div
                        initial={{ opacity: 0, scaleY: 0 }}
                        animate={{ opacity: 1, scaleY: 1 }}
                        exit={{ opacity: 0, scaleY: 0 }}
                        className="flex items-center justify-center space-x-1 h-8"
                    >
                        {[...Array(12)].map((_, i) => (
                            <motion.div
                                key={i}
                                className="w-1 bg-gradient-to-t from-red-500 to-red-400 rounded-full"
                                animate={{
                                    height: [8, 24, 8],
                                }}
                                transition={{
                                    duration: 0.5,
                                    repeat: Infinity,
                                    delay: i * 0.05,
                                    ease: "easeInOut"
                                }}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default AudioRecorder;
