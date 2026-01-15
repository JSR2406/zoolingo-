import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Volume2, Trash2, ChevronRight } from 'lucide-react';

const HistoryPanel = ({ history, onPlayAudio, onClearHistory, isOpen, onClose }) => {
    const getEmotionEmoji = (emotion) => {
        const map = {
            "Happy": "😊",
            "Angry": "😠",
            "Sad": "😢",
            "Hungry": "😋",
            "Pain": "😿"
        };
        return map[emotion] || "🐾";
    };

    const getAnimalEmoji = (animal) => {
        const map = {
            "Dog": "🐶",
            "Cat": "🐱",
            "Cow": "🐮",
            "Lion": "🦁"
        };
        return map[animal] || "🐾";
    };

    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="fixed right-0 top-0 h-full w-full max-w-md bg-bg-dark/95 backdrop-blur-xl border-l border-glass-border z-50 flex flex-col"
                    >
                        {/* Header */}
                        <div className="p-6 border-b border-glass-border">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Clock className="w-5 h-5 text-primary" />
                                    <h2 className="text-xl font-bold text-text-primary">Translation History</h2>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                                >
                                    <ChevronRight className="w-5 h-5 text-text-secondary" />
                                </button>
                            </div>
                            {history.length > 0 && (
                                <button
                                    onClick={onClearHistory}
                                    className="mt-3 flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Clear All
                                </button>
                            )}
                        </div>

                        {/* History List */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-3">
                            {history.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-center">
                                    <div className="text-6xl mb-4">🐾</div>
                                    <p className="text-text-secondary">No translations yet</p>
                                    <p className="text-text-muted text-sm">Record or upload animal sounds to get started</p>
                                </div>
                            ) : (
                                <AnimatePresence>
                                    {history.map((item, index) => (
                                        <motion.div
                                            key={item.id || index}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, x: -100 }}
                                            transition={{ delay: index * 0.05 }}
                                            className="glass-panel rounded-xl p-4 hover:bg-white/5 transition-colors"
                                        >
                                            <div className="flex items-start gap-3">
                                                {/* Animal Avatar */}
                                                <div className="text-3xl flex-shrink-0">
                                                    {getAnimalEmoji(item.animal)}
                                                </div>

                                                {/* Content */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-semibold text-text-primary">
                                                            {item.animal}
                                                        </span>
                                                        <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-text-secondary">
                                                            {getEmotionEmoji(item.emotion)} {item.emotion}
                                                        </span>
                                                        <span className="text-xs text-text-muted ml-auto">
                                                            {formatTime(item.timestamp)}
                                                        </span>
                                                    </div>
                                                    <p className="text-text-primary leading-relaxed">
                                                        "{item.translation}"
                                                    </p>
                                                    <div className="flex items-center gap-2 mt-2">
                                                        <span className="text-xs text-primary">
                                                            {Math.round(item.confidence * 100)}% confidence
                                                        </span>
                                                        {item.audio_url && (
                                                            <button
                                                                onClick={() => onPlayAudio(item.audio_url)}
                                                                className="ml-auto flex items-center gap-1 text-xs text-text-secondary hover:text-primary transition-colors"
                                                            >
                                                                <Volume2 className="w-3 h-3" />
                                                                Play
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            )}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

export default HistoryPanel;
