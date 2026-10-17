import React from 'react';
import { Languages } from 'lucide-react';

// English + Hindi MVP
const LANGUAGES = [
    { code: 'hi-IN', label: 'हिंदी', full: 'Hindi' },
    { code: 'en-IN', label: 'English', full: 'English' },
];

const LanguageSelector = ({ value, onChange }) => {
    return (
        <div className="flex items-center gap-2">
            <Languages className="w-4 h-4 text-primary" />
            <div className="glass-panel rounded-xl p-1 flex">
                {LANGUAGES.map(lang => {
                    const active = value === lang.code;
                    return (
                        <button
                            key={lang.code}
                            onClick={() => onChange(lang.code)}
                            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                active
                                    ? 'bg-primary text-white'
                                    : 'text-text-secondary hover:text-text-primary'
                            }`}
                        >
                            {lang.label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default LanguageSelector;
export { LANGUAGES };