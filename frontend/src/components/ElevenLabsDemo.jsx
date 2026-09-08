import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ChevronDown, ChevronUp, Play, Zap } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

const EMOTION_EMOJI = {
    hunger: '🍖',
    pain: '⚠️',
    fear: '😨',
    playfulness: '🎾',
    attention: '👀',
    aggression: '😾',
};

const ElevenLabsDemo = ({ onPlaySound, isProcessing }) => {
    const [sounds, setSounds] = useState([]);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        fetch(`${API_BASE}/api/demo/sounds`)
            .then(res => res.json())
            .then(data => { if (!cancelled && data.sounds) setSounds(data.sounds); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, []);

    return (
        <div className="w-full space-y-3 border-t border-glass-border pt-4">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 py-3 rounded-xl glass-panel border border-glass-border hover:border-white/20 transition-colors group"
            >
                <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                    <Sparkles className="w-4 h-4 text-primary" />
                    ElevenLabs Demo Sounds
                    <span className="text-[10px] text-text-muted font-normal">(Dog &amp; Cat · 12)</span>
                </span>
                {open ? <ChevronUp className="w-4 h-4 text-text-secondary" /> : <ChevronDown className="w-4 h-4 text-text-secondary" />}
            </button>

            {open && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="overflow-hidden"
                >
                    <p className="text-[11px] text-text-muted mb-2">
                        Play the pre-recorded sound, then watch ZooLingo classify it live and translate it
                        in your selected language.
                    </p>
                    <div className="grid grid-cols-2 gap-2 max-h-[240px] overflow-y-auto pr-1 custom-scrollbar">
                        {sounds.map(sound => (
                            <motion.button
                                key={sound.filename}
                                whileHover={{ scale: isProcessing ? 1 : 1.02 }}
                                whileTap={{ scale: isProcessing ? 1 : 0.98 }}
                                onClick={() => !isProcessing && onPlaySound(sound)}
                                disabled={isProcessing}
                                className={`
                                    p-2.5 rounded-xl border border-glass-border text-left
                                    hover:border-white/20 transition-all duration-200 group
                                    ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                                `}
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-xl flex-shrink-0">
                                        {sound.species === 'dog' ? '🐶' : '🐱'}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-semibold text-text-primary text-xs truncate">
                                            {sound.label} {sound.animal}
                                        </p>
                                        <p className="text-[10px] text-text-muted truncate">
                                            {EMOTION_EMOJI[sound.emotion]} {sound.label}
                                        </p>
                                    </div>
                                    <div className="w-6 h-6 rounded-full flex items-center justify-center bg-white/5 group-hover:bg-white/10 transition-colors flex-shrink-0">
                                        <Play className="w-3 h-3 text-white fill-current" />
                                    </div>
                                </div>
                            </motion.button>
                        ))}
                    </div>
                    {sounds.length === 0 && (
                        <p className="text-xs text-text-muted text-center py-3">
                            No ElevenLabs sounds found. Run <code className="text-primary">python generate_elevenlabs_sounds.py</code>.
                        </p>
                    )}
                </motion.div>
            )}
        </div>
    );
};

export default ElevenLabsDemo;