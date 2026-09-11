import React, { useState, useRef, useCallback } from 'react';

// Convert an AudioBuffer to a 16-bit PCM WAV Blob
const audioBufferToWav = (buffer) => {
    const numChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const numFrames = buffer.length;
    const bytesPerSample = 2;
    const blockAlign = numChannels * bytesPerSample;
    const dataSize = numFrames * blockAlign;

    const arrayBuffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(arrayBuffer);

    const writeString = (offset, str) => {
        for (let i = 0; i < str.length; i++) {
            view.setUint8(offset + i, str.charCodeAt(i));
        }
    };

    // RIFF header
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(8, 'WAVE');
    // fmt chunk
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    // data chunk
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    // Interleave channels, clip to 16-bit signed, mixed to mono
    const channelData = [];
    for (let c = 0; c < numChannels; c++) {
        channelData.push(buffer.getChannelData(c));
    }
    let offset = 44;
    for (let i = 0; i < numFrames; i++) {
        let sample = 0;
        for (let c = 0; c < numChannels; c++) {
            sample += channelData[c][i];
        }
        sample = sample / numChannels;
        sample = Math.max(-1, Math.min(1, sample));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
        offset += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
};
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

    // Decode the WebM/Opus recording and re-encode as WAV so the backend can
    // process it (backend decodes WAV directly without ffmpeg).
    const webmToWav = async (blob) => {
        try {
            const arrayBuffer = await blob.arrayBuffer();
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            const audioCtx = new AudioCtx();
            const decoded = await audioCtx.decodeAudioData(arrayBuffer);
            const wavBlob = audioBufferToWav(decoded);
            return new File([wavBlob], "recording.wav", { type: 'audio/wav' });
        } catch (err) {
            console.error("WebM->WAV conversion failed:", err);
            return new File([blob], "recording.webm", { type: 'audio/webm' });
        }
    };

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

            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                const wavFile = await webmToWav(blob);
                onRecordingComplete(wavFile);
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
