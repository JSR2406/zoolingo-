import React, { useState, useRef } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';

const AudioRecorder = ({ onRecordingComplete, isProcessing }) => {
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

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

            mediaRecorderRef.current.start();
            setIsRecording(true);
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Could not access microphone. Please ensure permissions are granted.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);

            // Stop all tracks
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
    };

    return (
        <div className="flex flex-col items-center justify-center p-6">
            <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isProcessing}
                className={`
          relative flex items-center justify-center w-24 h-24 rounded-full transition-all duration-300
          ${isRecording ? 'bg-red-500 hover:bg-red-600 animate-pulse' : 'bg-zoo-green hover:bg-zoo-dark'}
          ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer shadow-lg hover:shadow-xl hover:scale-105'}
        `}
            >
                {isProcessing ? (
                    <Loader2 className="w-10 h-10 text-white animate-spin" />
                ) : isRecording ? (
                    <Square className="w-10 h-10 text-white fill-current" />
                ) : (
                    <Mic className="w-10 h-10 text-white" />
                )}
            </button>
            <p className="mt-4 text-gray-600 font-medium">
                {isProcessing ? "Translating..." : isRecording ? "Listening..." : "Tap to Listen"}
            </p>
        </div>
    );
};

export default AudioRecorder;
