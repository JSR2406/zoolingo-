import React, { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Volume2, History, Sparkles, Zap, Github, ExternalLink } from 'lucide-react';
import AudioRecorder from './components/AudioRecorder';
import AnimalAvatar from './components/AnimalAvatar';
import HistoryPanel from './components/HistoryPanel';
import DemoSoundSelector from './components/DemoSoundSelector';
import LanguageSelector from './components/LanguageSelector';
import ElevenLabsDemo from './components/ElevenLabsDemo';
import VoiceSelector from './components/VoiceSelector';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import AppShell from './layout/AppShell';
import Dashboard from './pages/Dashboard';
import Pets from './pages/Pets';
import Health from './pages/Health';
import CareSchedules from './pages/CareSchedules';
import VetDirectory from './pages/VetDirectory';
import Expert from './pages/Expert';

import { useToast } from './components/Toast';

// API base URL - adjust based on environment
export const API_BASE = import.meta.env.VITE_API_URL || '';

// Intense emotions map to the "_intense" demo audio variant
const INTENSE_EMOTIONS = new Set([
    'Angry', 'Excited', 'Scared', 'Pain', 'Aggressive',
    'Alert', 'Demanding', 'Bossy', 'Mischievous',
]);

const LANGUAGE_LABELS = {
    'hi-IN': 'हिंदी (Hindi)',
    'en-IN': 'English',
    // More Indian languages coming soon via SARVAM Samvaad:
    // 'ta-IN': 'தமிழ் (Tamil)',
    // 'bn-IN': 'বাংলা (Bengali)',
    // 'mr-IN': 'मराठी (Marathi)',
    // 'gu-IN': 'ગુજરાતી (Gujarati)',
    // 'te-IN': 'తెలుగు (Telugu)',
    // 'kn-IN': 'ಕನ್ನಡ (Kannada)',
    // 'ml-IN': 'മലയാളം (Malayalam)',
    // 'pa-IN': 'ਪੰਜਾਬੀ (Punjabi)',
};

function AppContent() {
    const [result, setResult] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [history, setHistory] = useState([]);
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('record'); // 'record' or 'demo'
    const [language, setLanguage] = useState('hi-IN');
    const [expectedSound, setExpectedSound] = useState(null);
    const [voice, setVoice] = useState('shubh');
    const [availableVoices, setAvailableVoices] = useState({});
    const [showDetails, setShowDetails] = useState(false);
    const audioRef = useRef(null);
    const toast = useToast();

    // Load available voices per language + keep voice valid when language changes
    useEffect(() => {
        fetch(`${API_BASE}/api/languages`)
            .then(res => res.json())
            .then(data => {
                if (!data.languages) return;
                const map = {};
                data.languages.forEach(l => { map[l.code] = l.voices || []; });
                setAvailableVoices(map);
                const targetVoices = map[language] || [];
                setVoice(prev => (targetVoices.includes(prev) ? prev : (targetVoices[0] || prev)));
            })
            .catch(() => {});
    }, [language]);

    const handleRecordingComplete = async (file) => {
        setIsProcessing(true);
        setResult(null);
        setExpectedSound(null);

        const formData = new FormData();
        formData.append("file", file);
        formData.append("language", language);
        formData.append("voice", voice);

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

    const playSound = useCallback((url) => {
        if (!url) return;
        const audio = new Audio(url.startsWith('http') ? url : `${API_BASE}${url}`);
        audio.play().catch(e => console.log("Sound play prevented:", e));
    }, []);

    // Play the canned animal vocalization immediately when a demo is selected
    const playDemoSample = useCallback((animal, emotion) => {
        const variant = INTENSE_EMOTIONS.has(emotion) ? 'intense' : 'calm';
        playSound(`/demo-audio/${animal.toLowerCase()}_${variant}.wav`);
    }, [playSound]);

    const handleDemoSelect = async (demo) => {
        setIsProcessing(true);
        setResult(null);
        setExpectedSound(null);

        // Play the animal's sample sound right away
        playDemoSample(demo.animal, demo.emotion);

        try {
            const response = await fetch(`${API_BASE}/api/demo/${demo.id}?language=${encodeURIComponent(language)}&voice=${encodeURIComponent(voice)}`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error(`Request failed: ${response.status}`);
            }

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

                // Auto-play the translated voice (fixes silent demo audio)
                if (data.data.audio_url) {
                    const audio = new Audio(`${API_BASE}${data.data.audio_url}`);
                    audioRef.current = audio;
                    audio.play().catch(e => console.log("Auto-play prevented:", e));
                }
            } else {
                throw new Error(data.message || "Demo processing failed");
            }
        } catch (error) {
            console.error("Demo Error:", error);
            toast.error("Demo Failed", "Could not load demo audio. Is the backend running?");
        } finally {
            setIsProcessing(false);
        }
    };

    // ElevenLabs demo mode: play the pre-recorded sound, then classify it live
    const handleElevenLabsPlay = async (sound) => {
        setIsProcessing(true);
        setResult(null);
        setExpectedSound(sound);

        try {
            const res = await fetch(`${API_BASE}${sound.url}`);
            if (!res.ok) throw new Error(`Sound fetch failed: ${res.status}`);
            const blob = await res.blob();

            // Play it audibly for the audience (real server URL so the E2E can assert it)
            const preview = new Audio(`${API_BASE}${sound.url}`);
            await preview.play().catch(e => console.log("Preview play prevented:", e));

            // Route the same audio through the real classification + translation pipeline
            const formData = new FormData();
            formData.append("file", new File([blob], sound.filename, { type: "audio/wav" }));
            formData.append("language", language);
            formData.append("voice", voice);

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
                setHistory(prev => [newResult, ...prev].slice(0, 20));
                toast.success("Translation Complete", `Your ${data.data.animal} is feeling ${data.data.emotion.toLowerCase()}!`);

                if (data.data.audio_url) {
                    const audio = new Audio(`${API_BASE}${data.data.audio_url}`);
                    audioRef.current = audio;
                    audio.play().catch(e => console.log("Auto-play prevented:", e));
                }
            } else {
                toast.error("Processing Failed", data.message || "Could not process the demo sound");
            }
        } catch (error) {
            console.error("ElevenLabs Demo Error:", error);
            toast.error("Demo Failed", "Could not play the ElevenLabs demo sound. Is the backend running?");
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
                    <span className="text-sm text-text-secondary">Powered by SARVAM AI</span>
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

                {/* Language Selector */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.25 }}
                    className="mt-4 flex flex-col items-center justify-center gap-3"
                >
                    <LanguageSelector value={language} onChange={setLanguage} />
                    <VoiceSelector
                        value={voice}
                        onChange={setVoice}
                        voices={availableVoices[language] || []}
                    />
                </motion.div>

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
                                        {result.language && (
                                            <span className="text-xs text-text-muted uppercase tracking-wide">
                                                {LANGUAGE_LABELS[result.language] || result.language}
                                            </span>
                                        )}
                                        {result.voice && (
                                            <span className="text-xs text-text-secondary flex items-center gap-1">
                                                <Mic className="w-3 h-3" />
                                                Voice: {result.voice}
                                            </span>
                                        )}
                                        {result.audio_url && (
                                            <button
                                                onClick={() => playAudio(result.audio_url)}
                                                className="flex items-center gap-1 text-text-secondary hover:text-primary transition-colors"
                                            >
                                                <Volume2 className="w-4 h-4" />
                                                Replay Voice
                                            </button>
                                        )}
                                        {result.demo_audio_url && (
                                            <button
                                                onClick={() => playSound(result.demo_audio_url)}
                                                className="flex items-center gap-1 text-text-secondary hover:text-primary transition-colors"
                                            >
                                                <Volume2 className="w-4 h-4" />
                                                Play Sample
                                            </button>
                                        )}
                                        {result.classifier && result.classifier !== "yamnet" && (
                                            <button
                                                onClick={() => setShowDetails(!showDetails)}
                                                className="flex items-center gap-1 text-text-secondary hover:text-primary transition-colors text-xs"
                                            >
                                                {showDetails ? '▲' : '▼'} Classification Details
                                            </button>
                                        )}
                                        {showDetails && result.animal_scores && (
                                            <motion.div
                                                initial={{ opacity: 0, height: 0 }}
                                                animate={{ opacity: 1, height: 'auto' }}
                                                exit={{ opacity: 0, height: 0 }}
                                                className="mt-3 space-y-1"
                                            >
                                                <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                                                    Top animal matches
                                                </p>
                                                {Object.entries(result.animal_scores).map(([animal, score]) => (
                                                    <div
                                                        key={animal}
                                                        className="flex items-center justify-between text-xs"
                                                    >
                                                        <span className="text-text-secondary">
                                                            {animal}
                                                        </span>
                                                        <div className="flex-1 mx-3 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                            <div
                                                                className="h-full bg-primary rounded-full"
                                                                style={{
                                                                    width: Math.min(100, (score / 10) * 100) + "%",
                                                                }}
                                                            />
                                                        </div>
                                                        <span className="w-8 text-right text-text-muted">
                                                            {score.toFixed(1)}
                                                        </span>
                                                    </div>
                                                ))}
                                            </motion.div>
                                        )}
                                    </div>
                                </motion.div>

                                {/* Expected vs Predicted (ElevenLabs demo) */}
                                {expectedSound && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="flex flex-wrap items-center justify-center gap-2 text-xs"
                                    >
                                        <span className="px-2.5 py-1 rounded-full bg-white/5 border border-glass-border text-text-secondary">
                                            Expected: <b className="text-text-primary">{expectedSound.label}</b>
                                        </span>
                                        <span className="text-text-muted">→</span>
                                        <span className="px-2.5 py-1 rounded-full bg-white/5 border border-glass-border text-text-secondary">
                                            Predicted: <b className="text-text-primary">{result.emotion}</b>
                                        </span>
                                    </motion.div>
                                )}
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
                                    <ElevenLabsDemo
                                        onPlaySound={handleElevenLabsPlay}
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
        <BrowserRouter>
            <Routes>
                <Route element={<AppShell />}>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/pets" element={<Pets />} />
                    <Route path="/health" element={<Health />} />
                    <Route path="/care-schedules" element={<CareSchedules />} />
                    <Route path="/vet-directory" element={<VetDirectory />} />
                    <Route path="/expert" element={<Expert />} />
                    <Route path="/translate" element={<AppContent />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

export default App;
