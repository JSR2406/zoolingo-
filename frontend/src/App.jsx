import React, { useState, useRef } from 'react';
import AudioRecorder from './components/AudioRecorder';
import AnimalAvatar from './components/AnimalAvatar';
import { Volume2 } from 'lucide-react';

function App() {
    const [result, setResult] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const audioRef = useRef(null);

    const handleRecordingComplete = async (file) => {
        setIsProcessing(true);
        setResult(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch('/api/process-audio', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.status === "success") {
                setResult(data.data);
                if (data.data.audio_url) {
                    // Play audio automatically
                    const audio = new Audio(data.data.audio_url);
                    audioRef.current = audio;
                    audio.play().catch(e => console.log("Auto-play prevented:", e));
                }
            } else {
                alert("Error processing audio: " + data.message);
            }
        } catch (error) {
            console.error("API Error:", error);
            alert("Failed to connect to server.");
        } finally {
            setIsProcessing(false);
        }
    };

    const playAudio = () => {
        if (audioRef.current) {
            audioRef.current.play();
        }
    };

    return (
        <div className="min-h-screen bg-zoo-bg flex flex-col items-center py-10 px-4">
            <header className="mb-10 text-center">
                <h1 className="text-5xl font-bold text-zoo-dark mb-2">ZooLingo 🐾</h1>
                <p className="text-gray-600 text-lg">Understand what your pet is really saying.</p>
            </header>

            <main className="w-full max-w-md glass-panel rounded-3xl p-8 flex flex-col items-center space-y-8">

                {/* Avatar Section */}
                <div className="h-56 flex items-center justify-center">
                    {result ? (
                        <AnimalAvatar animal={result.animal} emotion={result.emotion} />
                    ) : (
                        <div className="w-48 h-48 rounded-full bg-gray-100 border-4 border-dashed border-gray-300 flex items-center justify-center text-gray-400">
                            <span className="text-6xl">?</span>
                        </div>
                    )}
                </div>

                {/* Result Text */}
                {result && (
                    <div className="text-center space-y-2 animate-fade-in">
                        <div className="inline-block px-3 py-1 rounded-full bg-gray-200 text-sm font-semibold text-gray-700 mb-2">
                            {result.animal} • {result.emotion}
                        </div>
                        <h2 className="text-2xl font-bold text-gray-800 leading-tight">
                            "{result.translation}"
                        </h2>
                        {result.audio_url && (
                            <button
                                onClick={playAudio}
                                className="mt-2 inline-flex items-center text-zoo-dark hover:text-zoo-green font-medium"
                            >
                                <Volume2 className="w-4 h-4 mr-1" /> Replay Voice
                            </button>
                        )}
                    </div>
                )}

                {/* Recorder */}
                <div className="w-full pt-4 border-t border-gray-200">
                    <AudioRecorder
                        onRecordingComplete={handleRecordingComplete}
                        isProcessing={isProcessing}
                    />
                </div>

            </main>

            <footer className="mt-12 text-center text-gray-500 text-sm">
                <p>Built for Techfest IIT Bombay • Powered by Murf Falcon & Deepgram</p>
            </footer>
        </div>
    );
}

export default App;
