import React from 'react';
import { motion } from 'framer-motion';

const AnimalAvatar = ({ animal, emotion }) => {
    // Comprehensive emoji mapping for all supported animals
    const getAvatar = () => {
        if (!animal) return "🐾";

        const map = {
            "Dog": "🐶",
            "Cat": "🐱",
            "Cow": "🐮",
            "Lion": "🦁",
            "Bird": "🐦",
            "Horse": "🐴",
            "Elephant": "🐘",
            "Sheep": "🐑",
            "Goat": "🐐",
            "Pig": "🐷",
            "Chicken": "🐔",
            "Duck": "🦆",
            "Monkey": "🐵",
            "Parrot": "🦜",
            "Wolf": "🐺",
            "Tiger": "🐯",
            "Bear": "🐻",
            "Rabbit": "🐰",
            "Fox": "🦊",
            "Deer": "🦌",
            "Frog": "🐸",
            "Snake": "🐍",
            "Turtle": "🐢",
            "Owl": "🦉",
            "Penguin": "🐧",
            "Dolphin": "🐬",
            "Whale": "🐳",
        };
        return map[animal] || "🐾";
    };

    // Comprehensive emotion configurations
    const getEmotionConfig = () => {
        const configs = {
            // Core emotions
            "Happy": {
                gradient: "from-yellow-400 via-amber-400 to-orange-400",
                bgGlow: "shadow-[0_0_60px_rgba(252,211,77,0.4)]",
                ringColor: "ring-yellow-400/50",
                animation: { y: [0, -10, 0] },
                label: "😊 Happy"
            },
            "Angry": {
                gradient: "from-red-400 via-red-500 to-rose-600",
                bgGlow: "shadow-[0_0_60px_rgba(239,68,68,0.4)]",
                ringColor: "ring-red-400/50",
                animation: { x: [-2, 2, -2, 2, 0] },
                label: "😠 Angry"
            },
            "Sad": {
                gradient: "from-blue-400 via-blue-500 to-indigo-500",
                bgGlow: "shadow-[0_0_60px_rgba(96,165,250,0.4)]",
                ringColor: "ring-blue-400/50",
                animation: { y: [0, 5, 0] },
                label: "😢 Sad"
            },
            "Hungry": {
                gradient: "from-orange-400 via-amber-500 to-yellow-500",
                bgGlow: "shadow-[0_0_60px_rgba(251,146,60,0.4)]",
                ringColor: "ring-orange-400/50",
                animation: { scale: [1, 1.05, 1] },
                label: "😋 Hungry"
            },
            "Pain": {
                gradient: "from-purple-400 via-violet-500 to-fuchsia-500",
                bgGlow: "shadow-[0_0_60px_rgba(167,139,250,0.4)]",
                ringColor: "ring-purple-400/50",
                animation: { rotate: [-3, 3, -3, 0] },
                label: "😿 Pain"
            },

            // Extended emotions
            "Excited": {
                gradient: "from-pink-400 via-rose-500 to-red-400",
                bgGlow: "shadow-[0_0_60px_rgba(244,114,182,0.4)]",
                ringColor: "ring-pink-400/50",
                animation: { y: [0, -15, 0], scale: [1, 1.1, 1] },
                label: "🤩 Excited"
            },
            "Scared": {
                gradient: "from-violet-400 via-purple-500 to-indigo-600",
                bgGlow: "shadow-[0_0_60px_rgba(139,92,246,0.4)]",
                ringColor: "ring-violet-400/50",
                animation: { x: [-3, 3, -3, 3, 0], scale: [1, 0.95, 1] },
                label: "😨 Scared"
            },
            "Curious": {
                gradient: "from-cyan-400 via-teal-500 to-emerald-500",
                bgGlow: "shadow-[0_0_60px_rgba(34,211,238,0.4)]",
                ringColor: "ring-cyan-400/50",
                animation: { rotate: [0, 15, -15, 0] },
                label: "🤔 Curious"
            },
            "Playful": {
                gradient: "from-green-400 via-emerald-500 to-teal-500",
                bgGlow: "shadow-[0_0_60px_rgba(52,211,153,0.4)]",
                ringColor: "ring-green-400/50",
                animation: { rotate: [-5, 5, -5, 5, 0], y: [0, -8, 0] },
                label: "😸 Playful"
            },
            "Calm": {
                gradient: "from-sky-400 via-blue-400 to-indigo-400",
                bgGlow: "shadow-[0_0_60px_rgba(56,189,248,0.4)]",
                ringColor: "ring-sky-400/50",
                animation: { scale: [1, 1.02, 1] },
                label: "😌 Calm"
            },
            "Demanding": {
                gradient: "from-rose-400 via-pink-500 to-fuchsia-500",
                bgGlow: "shadow-[0_0_60px_rgba(251,113,133,0.4)]",
                ringColor: "ring-rose-400/50",
                animation: { scale: [1, 1.08, 1], y: [0, -5, 0] },
                label: "😤 Demanding"
            },
            "Alert": {
                gradient: "from-amber-400 via-orange-500 to-red-500",
                bgGlow: "shadow-[0_0_60px_rgba(251,191,36,0.4)]",
                ringColor: "ring-amber-400/50",
                animation: { y: [0, -3, 0], scale: [1, 1.02, 1] },
                label: "🚨 Alert"
            },
            "Mischievous": {
                gradient: "from-fuchsia-400 via-pink-500 to-rose-500",
                bgGlow: "shadow-[0_0_60px_rgba(232,121,249,0.4)]",
                ringColor: "ring-fuchsia-400/50",
                animation: { rotate: [-8, 8, -8, 8, 0] },
                label: "😈 Mischievous"
            },
            "Proud": {
                gradient: "from-amber-500 via-yellow-500 to-orange-500",
                bgGlow: "shadow-[0_0_60px_rgba(245,158,11,0.4)]",
                ringColor: "ring-amber-500/50",
                animation: { scale: [1, 1.1, 1], y: [0, -5, 0] },
                label: "👑 Proud"
            },
            "Bossy": {
                gradient: "from-red-400 via-rose-500 to-pink-500",
                bgGlow: "shadow-[0_0_60px_rgba(251,113,133,0.4)]",
                ringColor: "ring-red-400/50",
                animation: { y: [0, -8, 0], rotate: [-2, 2, 0] },
                label: "👊 Bossy"
            },
            "Singing": {
                gradient: "from-violet-400 via-purple-400 to-pink-400",
                bgGlow: "shadow-[0_0_60px_rgba(196,181,253,0.4)]",
                ringColor: "ring-violet-400/50",
                animation: { scale: [1, 1.05, 0.98, 1.05, 1], y: [0, -3, 0] },
                label: "🎵 Singing"
            },
            "Chatty": {
                gradient: "from-emerald-400 via-green-500 to-teal-500",
                bgGlow: "shadow-[0_0_60px_rgba(52,211,153,0.4)]",
                ringColor: "ring-emerald-400/50",
                animation: { scale: [1, 1.02, 1], x: [-1, 1, -1, 1, 0] },
                label: "💬 Chatty"
            },
            "Aggressive": {
                gradient: "from-red-500 via-rose-600 to-red-700",
                bgGlow: "shadow-[0_0_60px_rgba(239,68,68,0.5)]",
                ringColor: "ring-red-500/50",
                animation: { x: [-4, 4, -4, 4, -2, 2, 0], scale: [1, 1.05, 1] },
                label: "💢 Aggressive"
            },
            "Lonely": {
                gradient: "from-slate-400 via-gray-500 to-slate-600",
                bgGlow: "shadow-[0_0_60px_rgba(148,163,184,0.4)]",
                ringColor: "ring-slate-400/50",
                animation: { y: [0, 3, 0], opacity: [1, 0.8, 1] },
                label: "😔 Lonely"
            },
        };

        return configs[emotion] || configs["Happy"];
    };

    const config = getEmotionConfig();

    return (
        <motion.div
            initial={{ scale: 0, opacity: 0, rotate: -180 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            transition={{
                type: "spring",
                stiffness: 200,
                damping: 15,
                duration: 0.6
            }}
            className="relative"
        >
            {/* Outer Glow Ring */}
            <motion.div
                className={`absolute inset-0 rounded-full bg-gradient-to-br ${config.gradient} opacity-20 blur-2xl`}
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />

            {/* Main Avatar Container */}
            <div className={`
                relative w-52 h-52 rounded-full 
                bg-gradient-to-br ${config.gradient}
                flex items-center justify-center
                ring-4 ${config.ringColor}
                ${config.bgGlow}
                transition-all duration-500
            `}>
                {/* Inner Glass Effect */}
                <div className="absolute inset-2 rounded-full bg-gradient-to-br from-white/20 to-transparent" />

                {/* Emoji Avatar */}
                <motion.span
                    className="text-8xl z-10 filter drop-shadow-lg"
                    animate={config.animation}
                    transition={{
                        repeat: Infinity,
                        duration: 2,
                        ease: "easeInOut"
                    }}
                >
                    {getAvatar()}
                </motion.span>

                {/* Sparkle Effects */}
                <motion.div
                    className="absolute top-4 right-6 w-3 h-3 bg-white rounded-full"
                    animate={{
                        scale: [0, 1, 0],
                        opacity: [0, 1, 0]
                    }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                    className="absolute bottom-8 left-4 w-2 h-2 bg-white rounded-full"
                    animate={{
                        scale: [0, 1, 0],
                        opacity: [0, 1, 0]
                    }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                />
                <motion.div
                    className="absolute top-12 left-8 w-2 h-2 bg-white rounded-full"
                    animate={{
                        scale: [0, 1, 0],
                        opacity: [0, 1, 0]
                    }}
                    transition={{ duration: 2, repeat: Infinity, delay: 1 }}
                />
                <motion.div
                    className="absolute bottom-12 right-8 w-2.5 h-2.5 bg-white rounded-full"
                    animate={{
                        scale: [0, 1, 0],
                        opacity: [0, 1, 0]
                    }}
                    transition={{ duration: 2, repeat: Infinity, delay: 1.5 }}
                />
            </div>

            {/* Animal & Emotion Label */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="absolute -bottom-4 left-1/2 transform -translate-x-1/2"
            >
                <div className={`
                    px-4 py-2 rounded-full 
                    bg-gradient-to-r ${config.gradient}
                    text-white text-sm font-bold
                    shadow-lg
                    whitespace-nowrap
                `}>
                    {animal} • {config.label}
                </div>
            </motion.div>
        </motion.div>
    );
};

export default AnimalAvatar;
