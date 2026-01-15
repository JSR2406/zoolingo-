import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2, History, Sparkles, Zap, Github, ExternalLink } from 'lucide-react';
import AudioRecorder from './components/AudioRecorder';
import AnimalAvatar from './components/AnimalAvatar';
import HistoryPanel from './components/HistoryPanel';
import DemoSoundSelector from './components/DemoSoundSelector';
import { ToastProvider, useToast } from './components/Toast';

// API base URL - adjust based on environment
const API_BASE = import.meta.env.VITE_API_URL || '';

function AppContent() {
    const [result, setResult] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [history, setHistory] = useState([]);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('record'); // 'record' or 'demo'
    const audioRef = useRef(null);
    const toast = useToast();

    const handleRecordingComplete = async (file) => {
        setIsProcessing(true);
        setResult(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${API_BASE}/api/process-audio`, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.status === "success") {
                const newResult = {
                    ...data.data,
                    id: Date.now(),
                    timestamp: new Date().toISOString()
                };
                setResult(newResult);
                setHistory(prev => [newResult, ...prev].slice(0, 20)); // Keep last 20

                toast.success("Translation Complete", `Your ${data.data.animal} is feeling ${data.data.emotion.toLowerCase()}!`);

                if (data.data.audio_url) {
                    const audio = new Audio(`${API_BASE}${data.data.audio_url}`);
                    audioRef.current = audio;
                    audio.play().catch(e => console.log("Auto-play prevented:", e));
                }
            } else {
                toast.error("Processing Failed", data.message || "Could not process the audio");
            }
        } catch (error) {
            console.error("API Error:", error);
            toast.error("Connection Error", "Failed to connect to the server. Make sure the backend is running.");
        } finally {
            setIsProcessing(false);
        }
    };

    const handleDemoSelect = async (demo) => {
        setIsProcessing(true);
        setResult(null);

        // Simulate API call for demo
        try {
            // For demo purposes, we'll make a mock request
            // In production, you'd have actual demo audio files
            const response = await fetch(`${API_BASE}/api/demo/${demo.id}`, {
                method: 'POST',
            }).catch(() => null);

            // If no backend or demo endpoint, simulate result
            if (!response || !response.ok) {
                await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate processing

                const mockTranslations = {
                    'Dog': {
                        'Happy': ["I love you so much!", "Let's play!", "This is the best day ever!"],
                        'Angry': ["Back off, I'm warning you!", "Grrr, leave me alone!"],
                        'Sad': ["I miss you...", "Please don't leave."],
                        'Hungry': ["Feed me now!", "Is that bacon I smell?"],
                        'Pain': ["Ouch, that hurts!", "Help me please..."]
                    },
                    'Cat': {
                        'Happy': ["Purr... you may pet me now.", "I tolerate your presence."],
                        'Angry': ["Hiss! Don't touch me!", "I will destroy you!"],
                        'Sad': ["My bowl is empty again.", "Why is the door closed?"],
                        'Hungry': ["Feed me now, peasant!", "I can see the bottom of my bowl!"],
                        'Pain': ["Hiss... stay away.", "Something is wrong..."]
                    },
                    'Cow': {
                        'Happy': ["Moo! Life is good in the pasture.", "Such fresh grass today!"],
                        'Angry': ["Stay away from my herd!", "Moo! I'm getting irritated!"],
                        'Sad': ["The barn feels empty today.", "I miss the sunshine."],
                        'Hungry': ["More hay, please!", "Moo! When is feeding time?"],
                        'Pain': ["Something hurts, farmer.", "Moo... I need help."]
                    },
                    'Lion': {
                        'Happy': ["ROAR! I am the king!", "The pride is strong today."],
                        'Angry': ["ROAR! Leave my territory!", "You dare challenge me?!"],
                        'Sad': ["The savanna feels lonely.", "I miss the old days."],
                        'Hungry': ["Time for the hunt!", "I hunger for the chase!"],
                        'Pain': ["Even kings feel pain.", "I need rest..."]
                    }
                };

                const translations = mockTranslations[demo.animal]?.[demo.emotion] || ["I am an animal."];
                const translation = translations[Math.floor(Math.random() * translations.length)];

                const mockResult = {
                    animal: demo.animal,
                    emotion: demo.emotion,
                    confidence: 0.85 + Math.random() * 0.14,
                    translation: translation,
                    audio_url: null, // No audio in demo mode
                    id: Date.now(),
                    timestamp: new Date().toISOString()
                };

                setResult(mockResult);
                setHistory(prev => [mockResult, ...prev].slice(0, 20));
                toast.success("Demo Translation", `Simulated ${demo.animal} translation!`);
            } else {
                const data = await response.json();
                if (data.status === "success") {
                    const newResult = {
                        ...data.data,
                        id: Date.now(),
                        timestamp: new Date().toISOString()
                    };
                    setResult(newResult);
                    setHistory(prev => [newResult, ...prev].slice(0, 20));
                    toast.success("Translation Complete", `Your ${data.data.animal} is feeling ${data.data.emotion.toLowerCase()}!`);
                }
            }
        } catch (error) {
            console.error("Demo Error:", error);
            toast.error("Demo Failed", "Could not load demo audio");
        } finally {
            setIsProcessing(false);
        }
    };

    const playAudio = useCallback((url) => {
        if (url) {
            const audio = new Audio(url.startsWith('http') ? url : `${API_BASE}${url}`);
            audio.play().catch(e => console.log("Audio play prevented:", e));
        } else if (audioRef.current) {
            audioRef.current.play();
        }
    }, []);

    const clearHistory = () => {
        setHistory([]);
        toast.info("History Cleared", "All translations have been removed");
    };

    return (
        <div className="min-h-screen flex flex-col">
            {/* Animated Background */}
            <div className="fixed inset-0 z-0">
                <div className="absolute inset-0 bg-gradient-to-br from-bg-dark via-[#1a2332] to-bg-dark" />
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse-slow" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
            </div>

            {/* Header */}
            <header className="relative z-10 pt-8 pb-6 text-center px-4">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel mb-4"
                >
                    <Sparkles className="w-4 h-4 text-primary" />
                    <span className="text-sm text-text-secondary">Powered by Murf Falcon TTS</span>
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-5xl md:text-6xl font-extrabold mb-3"
                >
                    <span className="gradient-text">ZooLingo</span>
                    <span className="ml-3">🐾</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-text-secondary text-lg max-w-md mx-auto"
                >
                    Voice-first AI agent that translates animal sounds into human language
                </motion.p>

                {/* History Button */}
                <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    onClick={() => setIsHistoryOpen(true)}
                    className="absolute top-8 right-4 md:right-8 p-3 glass-panel rounded-xl hover:bg-white/10 transition-colors group"
                >
                    <History className="w-5 h-5 text-text-secondary group-hover:text-primary transition-colors" />
                    {history.length > 0 && (
                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary rounded-full text-xs flex items-center justify-center text-white font-bold">
                            {history.length}
                        </span>
                    )}
                </motion.button>
            </header>

            {/* Main Content */}
            <main className="relative z-10 flex-1 flex flex-col items-center px-4 pb-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="w-full max-w-lg glass-panel-solid rounded-3xl p-8 space-y-8"
                >
                    {/* Avatar Section */}
                    <div className="min-h-[280px] flex items-center justify-center">
                        <AnimatePresence mode="wait">
                            {result ? (
                                <motion.div
                                    key="result"
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    className="flex flex-col items-center"
                                >
                                    <AnimalAvatar animal={result.animal} emotion={result.emotion} />
                                </motion.div>
                            ) : isProcessing ? (
                                <motion.div
                                    key="processing"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="flex flex-col items-center space-y-4"
                                >
                                    <div className="w-52 h-52 rounded-full glass-panel flex items-center justify-center">
                                        <div className="typing-indicator flex items-center gap-1">
                                            <span /><span /><span />
                                        </div>
                                    </div>
                                    <p className="text-text-secondary animate-pulse">Analyzing sound...</p>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="placeholder"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="w-52 h-52 rounded-full glass-panel border-2 border-dashed border-glass-border flex flex-col items-center justify-center"
                                >
                                    <span className="text-6xl mb-2">🐾</span>
                                    <p className="text-text-muted text-sm">Waiting for input...</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Translation Result */}
                    <AnimatePresence>
                        {result && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="text-center space-y-4"
                            >
                                <motion.div
                                    className="glass-panel rounded-2xl p-6"
                                    initial={{ scale: 0.9 }}
                                    animate={{ scale: 1 }}
                                >
                                    <h2 className="text-2xl md:text-3xl font-bold text-text-primary leading-tight mb-4">
                                        "{result.translation}"
                                    </h2>
                                    <div className="flex items-center justify-center gap-4 text-sm">
                                        <span className="flex items-center gap-1 text-primary">
                                            <Zap className="w-4 h-4" />
                                            {Math.round(result.confidence * 100)}% confidence
                                        </span>
                                        {result.audio_url && (
                                            <button
                                                onClick={() => playAudio(result.audio_url)}
                                                className="flex items-center gap-1 text-text-secondary hover:text-primary transition-colors"
                                            >
                                                <Volume2 className="w-4 h-4" />
                                                Replay
                                            </button>
                                        )}
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Tab Switcher */}
                    <div className="flex items-center justify-center">
                        <div className="glass-panel rounded-xl p-1 flex">
                            <button
                                onClick={() => setActiveTab('record')}
                                className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'record'
                                        ? 'bg-primary text-white'
                                        : 'text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                Record
                            </button>
                            <button
                                onClick={() => setActiveTab('demo')}
                                className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'demo'
                                        ? 'bg-primary text-white'
                                        : 'text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                Try Demo
                            </button>
                        </div>
                    </div>

                    {/* Input Section */}
                    <div className="border-t border-glass-border pt-6">
                        <AnimatePresence mode="wait">
                            {activeTab === 'record' ? (
                                <motion.div
                                    key="record"
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: 20 }}
                                >
                                    <AudioRecorder
                                        onRecordingComplete={handleRecordingComplete}
                                        isProcessing={isProcessing}
                                    />
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="demo"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                >
                                    <DemoSoundSelector
                                        onSelectDemo={handleDemoSelect}
                                        isProcessing={isProcessing}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </motion.div>
            </main>

            {/* Footer */}
            <footer className="relative z-10 py-6 text-center">
                <div className="flex items-center justify-center gap-6 text-text-muted text-sm">
                    <span>Built for Techfest IIT Bombay</span>
                    <span className="w-1 h-1 bg-text-muted rounded-full" />
                    <a
                        href="https://github.com/JSR2406/zoolingo-"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 hover:text-primary transition-colors"
                    >
                        <Github className="w-4 h-4" />
                        GitHub
                        <ExternalLink className="w-3 h-3" />
                    </a>
                </div>
            </footer>

            {/* History Panel */}
            <HistoryPanel
                history={history}
                onPlayAudio={playAudio}
                onClearHistory={clearHistory}
                isOpen={isHistoryOpen}
                onClose={() => setIsHistoryOpen(false)}
            />
        </div>
    );
}

function App() {
    return (
        <ToastProvider>
            <AppContent />
        </ToastProvider>
    );
}

export default App;
