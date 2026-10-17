/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'primary': '#10B981',
                'primary-dark': '#059669',
                'primary-light': '#34D399',
                'bg-dark': '#0F1419',
                'bg-card': 'rgba(30, 41, 59, 0.8)',
                'glass-border': 'rgba(255, 255, 255, 0.1)',
                'text-primary': '#F8FAFC',
                'text-secondary': '#94A3B8',
                'text-muted': '#64748B',
                // Emotion colors
                'emotion-happy': '#FCD34D',
                'emotion-angry': '#EF4444',
                'emotion-sad': '#60A5FA',
                'emotion-hungry': '#FB923C',
                'emotion-pain': '#A78BFA',
            },
            fontFamily: {
                'inter': ['Inter', 'sans-serif'],
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'bounce-in': 'bounce-in 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
                'fade-in-up': 'fade-in-up 0.5s ease-out forwards',
                'float': 'float 3s ease-in-out infinite',
                'spin-slow': 'spin 8s linear infinite',
            },
            keyframes: {
                'bounce-in': {
                    '0%': { transform: 'scale(0)', opacity: '0' },
                    '50%': { transform: 'scale(1.1)' },
                    '100%': { transform: 'scale(1)', opacity: '1' },
                },
                'fade-in-up': {
                    'from': { opacity: '0', transform: 'translateY(20px)' },
                    'to': { opacity: '1', transform: 'translateY(0)' },
                },
                'float': {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-10px)' },
                },
            },
            backdropBlur: {
                'xs': '2px',
            },
            boxShadow: {
                'glow-green': '0 0 20px rgba(16, 185, 129, 0.4), 0 0 40px rgba(16, 185, 129, 0.2)',
                'glow-red': '0 0 20px rgba(239, 68, 68, 0.4), 0 0 40px rgba(239, 68, 68, 0.2)',
            },
        },
    },
    plugins: [],
}
