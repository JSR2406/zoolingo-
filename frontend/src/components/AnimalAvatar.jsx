import React from 'react';
import { motion } from 'framer-motion';

const AnimalAvatar = ({ animal, emotion }) => {
    // Simple emoji mapping for demo purposes
    // In a real app, these could be SVG illustrations or Lottie animations
    const getAvatar = () => {
        if (!animal) return "🦁"; // Default

        const map = {
            "Dog": "🐶",
            "Cat": "🐱",
            "Cow": "🐮",
            "Lion": "🦁"
        };
        return map[animal] || "🐾";
    };

    const getEmotionColor = () => {
        const map = {
            "Happy": "bg-yellow-100 border-yellow-400",
            "Angry": "bg-red-100 border-red-400",
            "Sad": "bg-blue-100 border-blue-400",
            "Hungry": "bg-orange-100 border-orange-400",
            "Pain": "bg-purple-100 border-purple-400"
        };
        return map[emotion] || "bg-white border-gray-200";
    };

    return (
        <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`
        w-48 h-48 rounded-full border-4 flex items-center justify-center text-8xl shadow-xl
        ${getEmotionColor()}
      `}
        >
            <motion.span
                animate={emotion === "Happy" ? { y: [0, -10, 0] } : {}}
                transition={{ repeat: Infinity, duration: 2 }}
            >
                {getAvatar()}
            </motion.span>
        </motion.div>
    );
};

export default AnimalAvatar;
