import React from 'react';
import { Mic } from 'lucide-react';

const VoiceSelector = ({ value, onChange, voices = [], disabled }) => {
    if (!voices.length) return null;
    return (
        <div className="flex items-center gap-2">
            <Mic className="w-4 h-4 text-primary" />
            <div className="glass-panel rounded-xl p-1 flex">
                {voices.map(voice => {
                    const active = value === voice;
                    return (
                        <button
                            key={voice}
                            onClick={() => !disabled && onChange(voice)}
                            disabled={disabled}
                            className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all capitalize ${
                                active
                                    ? 'bg-primary text-white'
                                    : 'text-text-secondary hover:text-text-primary'
                            }`}
                        >
                            {voice}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default VoiceSelector;