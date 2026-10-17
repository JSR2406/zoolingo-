import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, ChevronDown, ChevronUp, Search, Filter } from 'lucide-react';

// Comprehensive demo sounds for all animals and emotions
const DEMO_SOUNDS = [
    // Dogs - All expressions
    { id: 'dog-happy', animal: 'Dog', emotion: 'Happy', label: 'Happy Dog', emoji: '🐶', description: 'Joyful barking', color: 'from-amber-400 to-yellow-500' },
    { id: 'dog-angry', animal: 'Dog', emotion: 'Angry', label: 'Angry Dog', emoji: '🐶', description: 'Aggressive growling', color: 'from-red-500 to-rose-600' },
    { id: 'dog-sad', animal: 'Dog', emotion: 'Sad', label: 'Sad Dog', emoji: '🐶', description: 'Whimpering sounds', color: 'from-blue-400 to-indigo-500' },
    { id: 'dog-hungry', animal: 'Dog', emotion: 'Hungry', label: 'Hungry Dog', emoji: '🐶', description: 'Begging whines', color: 'from-orange-400 to-amber-500' },
    { id: 'dog-excited', animal: 'Dog', emotion: 'Excited', label: 'Excited Dog', emoji: '🐶', description: 'Hyper barking', color: 'from-pink-400 to-rose-500' },
    { id: 'dog-scared', animal: 'Dog', emotion: 'Scared', label: 'Scared Dog', emoji: '🐶', description: 'Fearful whimpers', color: 'from-purple-400 to-violet-500' },
    { id: 'dog-playful', animal: 'Dog', emotion: 'Playful', label: 'Playful Dog', emoji: '🐶', description: 'Play bow sounds', color: 'from-green-400 to-emerald-500' },
    { id: 'dog-curious', animal: 'Dog', emotion: 'Curious', label: 'Curious Dog', emoji: '🐶', description: 'Inquisitive sounds', color: 'from-cyan-400 to-teal-500' },

    // Cats - All expressions
    { id: 'cat-happy', animal: 'Cat', emotion: 'Happy', label: 'Happy Cat', emoji: '🐱', description: 'Content purring', color: 'from-amber-400 to-yellow-500' },
    { id: 'cat-angry', animal: 'Cat', emotion: 'Angry', label: 'Angry Cat', emoji: '🐱', description: 'Hissing sounds', color: 'from-red-500 to-rose-600' },
    { id: 'cat-sad', animal: 'Cat', emotion: 'Sad', label: 'Sad Cat', emoji: '🐱', description: 'Mournful meows', color: 'from-blue-400 to-indigo-500' },
    { id: 'cat-hungry', animal: 'Cat', emotion: 'Hungry', label: 'Hungry Cat', emoji: '🐱', description: 'Demanding meows', color: 'from-orange-400 to-amber-500' },
    { id: 'cat-excited', animal: 'Cat', emotion: 'Excited', label: 'Excited Cat', emoji: '🐱', description: 'Chittering sounds', color: 'from-pink-400 to-rose-500' },
    { id: 'cat-scared', animal: 'Cat', emotion: 'Scared', label: 'Scared Cat', emoji: '🐱', description: 'Alarmed yowls', color: 'from-purple-400 to-violet-500' },
    { id: 'cat-demanding', animal: 'Cat', emotion: 'Demanding', label: 'Demanding Cat', emoji: '🐱', description: 'Persistent meows', color: 'from-rose-400 to-pink-500' },
    { id: 'cat-curious', animal: 'Cat', emotion: 'Curious', label: 'Curious Cat', emoji: '🐱', description: 'Trilling sounds', color: 'from-cyan-400 to-teal-500' },

    // Cows
    { id: 'cow-happy', animal: 'Cow', emotion: 'Happy', label: 'Happy Cow', emoji: '🐮', description: 'Contented moo', color: 'from-amber-400 to-yellow-500' },
    { id: 'cow-hungry', animal: 'Cow', emotion: 'Hungry', label: 'Hungry Cow', emoji: '🐮', description: 'Hungry mooing', color: 'from-orange-400 to-amber-500' },
    { id: 'cow-angry', animal: 'Cow', emotion: 'Angry', label: 'Angry Cow', emoji: '🐮', description: 'Agitated sounds', color: 'from-red-500 to-rose-600' },
    { id: 'cow-sad', animal: 'Cow', emotion: 'Sad', label: 'Sad Cow', emoji: '🐮', description: 'Lonely mooing', color: 'from-blue-400 to-indigo-500' },
    { id: 'cow-calm', animal: 'Cow', emotion: 'Calm', label: 'Calm Cow', emoji: '🐮', description: 'Peaceful sounds', color: 'from-green-400 to-emerald-500' },

    // Lions
    { id: 'lion-happy', animal: 'Lion', emotion: 'Happy', label: 'Happy Lion', emoji: '🦁', description: 'Satisfied rumble', color: 'from-amber-400 to-yellow-500' },
    { id: 'lion-angry', animal: 'Lion', emotion: 'Angry', label: 'Roaring Lion', emoji: '🦁', description: 'Mighty roar', color: 'from-red-500 to-rose-600' },
    { id: 'lion-hungry', animal: 'Lion', emotion: 'Hungry', label: 'Hungry Lion', emoji: '🦁', description: 'Hunting calls', color: 'from-orange-400 to-amber-500' },
    { id: 'lion-proud', animal: 'Lion', emotion: 'Proud', label: 'Proud Lion', emoji: '🦁', description: 'Majestic roar', color: 'from-yellow-400 to-orange-500' },
    { id: 'lion-sad', animal: 'Lion', emotion: 'Sad', label: 'Sad Lion', emoji: '🦁', description: 'Low rumbles', color: 'from-blue-400 to-indigo-500' },

    // Birds
    { id: 'bird-happy', animal: 'Bird', emotion: 'Happy', label: 'Happy Bird', emoji: '🐦', description: 'Cheerful chirps', color: 'from-amber-400 to-yellow-500' },
    { id: 'bird-singing', animal: 'Bird', emotion: 'Singing', label: 'Singing Bird', emoji: '🐦', description: 'Beautiful melody', color: 'from-pink-400 to-rose-500' },
    { id: 'bird-hungry', animal: 'Bird', emotion: 'Hungry', label: 'Hungry Bird', emoji: '🐦', description: 'Begging chirps', color: 'from-orange-400 to-amber-500' },
    { id: 'bird-alert', animal: 'Bird', emotion: 'Alert', label: 'Alert Bird', emoji: '🐦', description: 'Alarm calls', color: 'from-red-500 to-rose-600' },
    { id: 'bird-scared', animal: 'Bird', emotion: 'Scared', label: 'Scared Bird', emoji: '🐦', description: 'Distress calls', color: 'from-purple-400 to-violet-500' },

    // Horses
    { id: 'horse-happy', animal: 'Horse', emotion: 'Happy', label: 'Happy Horse', emoji: '🐴', description: 'Joyful neighing', color: 'from-amber-400 to-yellow-500' },
    { id: 'horse-excited', animal: 'Horse', emotion: 'Excited', label: 'Excited Horse', emoji: '🐴', description: 'Excited whinnies', color: 'from-pink-400 to-rose-500' },
    { id: 'horse-angry', animal: 'Horse', emotion: 'Angry', label: 'Angry Horse', emoji: '🐴', description: 'Snorting sounds', color: 'from-red-500 to-rose-600' },
    { id: 'horse-hungry', animal: 'Horse', emotion: 'Hungry', label: 'Hungry Horse', emoji: '🐴', description: 'Eager nickering', color: 'from-orange-400 to-amber-500' },
    { id: 'horse-calm', animal: 'Horse', emotion: 'Calm', label: 'Calm Horse', emoji: '🐴', description: 'Soft snorts', color: 'from-green-400 to-emerald-500' },

    // Elephants
    { id: 'elephant-happy', animal: 'Elephant', emotion: 'Happy', label: 'Happy Elephant', emoji: '🐘', description: 'Trumpet of joy', color: 'from-amber-400 to-yellow-500' },
    { id: 'elephant-angry', animal: 'Elephant', emotion: 'Angry', label: 'Angry Elephant', emoji: '🐘', description: 'Warning trumpet', color: 'from-red-500 to-rose-600' },
    { id: 'elephant-sad', animal: 'Elephant', emotion: 'Sad', label: 'Sad Elephant', emoji: '🐘', description: 'Mournful calls', color: 'from-blue-400 to-indigo-500' },
    { id: 'elephant-hungry', animal: 'Elephant', emotion: 'Hungry', label: 'Hungry Elephant', emoji: '🐘', description: 'Rumbling sounds', color: 'from-orange-400 to-amber-500' },

    // Sheep
    { id: 'sheep-happy', animal: 'Sheep', emotion: 'Happy', label: 'Happy Sheep', emoji: '🐑', description: 'Content bleating', color: 'from-amber-400 to-yellow-500' },
    { id: 'sheep-scared', animal: 'Sheep', emotion: 'Scared', label: 'Scared Sheep', emoji: '🐑', description: 'Panic bleating', color: 'from-purple-400 to-violet-500' },
    { id: 'sheep-hungry', animal: 'Sheep', emotion: 'Hungry', label: 'Hungry Sheep', emoji: '🐑', description: 'Hungry baas', color: 'from-orange-400 to-amber-500' },

    // Goats
    { id: 'goat-happy', animal: 'Goat', emotion: 'Happy', label: 'Happy Goat', emoji: '🐐', description: 'Happy bleating', color: 'from-amber-400 to-yellow-500' },
    { id: 'goat-mischievous', animal: 'Goat', emotion: 'Mischievous', label: 'Mischievous Goat', emoji: '🐐', description: 'Playful sounds', color: 'from-pink-400 to-rose-500' },
    { id: 'goat-angry', animal: 'Goat', emotion: 'Angry', label: 'Angry Goat', emoji: '🐐', description: 'Aggressive bleats', color: 'from-red-500 to-rose-600' },

    // Pigs
    { id: 'pig-happy', animal: 'Pig', emotion: 'Happy', label: 'Happy Pig', emoji: '🐷', description: 'Content oinking', color: 'from-amber-400 to-yellow-500' },
    { id: 'pig-hungry', animal: 'Pig', emotion: 'Hungry', label: 'Hungry Pig', emoji: '🐷', description: 'Eager squeals', color: 'from-orange-400 to-amber-500' },
    { id: 'pig-curious', animal: 'Pig', emotion: 'Curious', label: 'Curious Pig', emoji: '🐷', description: 'Sniffing sounds', color: 'from-cyan-400 to-teal-500' },

    // Chickens
    { id: 'chicken-happy', animal: 'Chicken', emotion: 'Happy', label: 'Happy Chicken', emoji: '🐔', description: 'Content clucking', color: 'from-amber-400 to-yellow-500' },
    { id: 'chicken-scared', animal: 'Chicken', emotion: 'Scared', label: 'Scared Chicken', emoji: '🐔', description: 'Alarm clucking', color: 'from-purple-400 to-violet-500' },
    { id: 'chicken-bossy', animal: 'Chicken', emotion: 'Bossy', label: 'Bossy Chicken', emoji: '🐔', description: 'Assertive bawks', color: 'from-rose-400 to-pink-500' },

    // Ducks
    { id: 'duck-happy', animal: 'Duck', emotion: 'Happy', label: 'Happy Duck', emoji: '🦆', description: 'Cheerful quacking', color: 'from-amber-400 to-yellow-500' },
    { id: 'duck-demanding', animal: 'Duck', emotion: 'Demanding', label: 'Demanding Duck', emoji: '🦆', description: 'Loud quacks', color: 'from-rose-400 to-pink-500' },

    // Monkeys
    { id: 'monkey-happy', animal: 'Monkey', emotion: 'Happy', label: 'Happy Monkey', emoji: '🐵', description: 'Joyful chattering', color: 'from-amber-400 to-yellow-500' },
    { id: 'monkey-mischievous', animal: 'Monkey', emotion: 'Mischievous', label: 'Mischievous Monkey', emoji: '🐵', description: 'Playful sounds', color: 'from-pink-400 to-rose-500' },
    { id: 'monkey-angry', animal: 'Monkey', emotion: 'Angry', label: 'Angry Monkey', emoji: '🐵', description: 'Aggressive screech', color: 'from-red-500 to-rose-600' },

    // Parrots
    { id: 'parrot-happy', animal: 'Parrot', emotion: 'Happy', label: 'Happy Parrot', emoji: '🦜', description: 'Cheerful sounds', color: 'from-amber-400 to-yellow-500' },
    { id: 'parrot-chatty', animal: 'Parrot', emotion: 'Chatty', label: 'Chatty Parrot', emoji: '🦜', description: 'Talkative sounds', color: 'from-green-400 to-emerald-500' },
    { id: 'parrot-angry', animal: 'Parrot', emotion: 'Angry', label: 'Angry Parrot', emoji: '🦜', description: 'Loud squawks', color: 'from-red-500 to-rose-600' },

    // Wolves
    { id: 'wolf-happy', animal: 'Wolf', emotion: 'Happy', label: 'Happy Wolf', emoji: '🐺', description: 'Pack howling', color: 'from-amber-400 to-yellow-500' },
    { id: 'wolf-aggressive', animal: 'Wolf', emotion: 'Aggressive', label: 'Aggressive Wolf', emoji: '🐺', description: 'Threatening growl', color: 'from-red-500 to-rose-600' },
    { id: 'wolf-lonely', animal: 'Wolf', emotion: 'Lonely', label: 'Lonely Wolf', emoji: '🐺', description: 'Lone howl', color: 'from-blue-400 to-indigo-500' },
    { id: 'wolf-hungry', animal: 'Wolf', emotion: 'Hungry', label: 'Hungry Wolf', emoji: '🐺', description: 'Hunting calls', color: 'from-orange-400 to-amber-500' },
];

// Get unique animals and emotions for filtering
const UNIQUE_ANIMALS = [...new Set(DEMO_SOUNDS.map(s => s.animal))];
const UNIQUE_EMOTIONS = [...new Set(DEMO_SOUNDS.map(s => s.emotion))];

const DemoSoundSelector = ({ onSelectDemo, isProcessing }) => {
    const [expanded, setExpanded] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedAnimal, setSelectedAnimal] = useState('');
    const [selectedEmotion, setSelectedEmotion] = useState('');

    // Filter sounds based on search and filters
    const filteredSounds = DEMO_SOUNDS.filter(sound => {
        const matchesSearch = searchTerm === '' ||
            sound.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
            sound.description.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesAnimal = selectedAnimal === '' || sound.animal === selectedAnimal;
        const matchesEmotion = selectedEmotion === '' || sound.emotion === selectedEmotion;
        return matchesSearch && matchesAnimal && matchesEmotion;
    });

    // Show limited sounds when collapsed
    const displayedSounds = expanded ? filteredSounds : filteredSounds.slice(0, 8);
    const hasMore = filteredSounds.length > 8;

    return (
        <div className="w-full space-y-4">
            {/* Search and Filter Bar */}
            <div className="space-y-3">
                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input
                        type="text"
                        placeholder="Search demo sounds..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 rounded-xl bg-white/5 border border-glass-border text-text-primary placeholder-text-muted focus:outline-none focus:border-primary transition-colors"
                    />
                </div>

                {/* Filters */}
                <div className="flex gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-text-muted" />
                    </div>

                    {/* Animal Filter */}
                    <select
                        value={selectedAnimal}
                        onChange={(e) => setSelectedAnimal(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-white/5 border border-glass-border text-text-secondary text-sm focus:outline-none focus:border-primary cursor-pointer"
                    >
                        <option value="">All Animals</option>
                        {UNIQUE_ANIMALS.map(animal => (
                            <option key={animal} value={animal}>{animal}</option>
                        ))}
                    </select>

                    {/* Emotion Filter */}
                    <select
                        value={selectedEmotion}
                        onChange={(e) => setSelectedEmotion(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-white/5 border border-glass-border text-text-secondary text-sm focus:outline-none focus:border-primary cursor-pointer"
                    >
                        <option value="">All Emotions</option>
                        {UNIQUE_EMOTIONS.map(emotion => (
                            <option key={emotion} value={emotion}>{emotion}</option>
                        ))}
                    </select>

                    {/* Clear filters */}
                    {(searchTerm || selectedAnimal || selectedEmotion) && (
                        <button
                            onClick={() => {
                                setSearchTerm('');
                                setSelectedAnimal('');
                                setSelectedEmotion('');
                            }}
                            className="px-3 py-1.5 rounded-lg text-xs text-red-400 hover:text-red-300 transition-colors"
                        >
                            Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Results count */}
            <p className="text-xs text-text-muted">
                Showing {displayedSounds.length} of {filteredSounds.length} demo sounds
            </p>

            {/* Demo Sound Grid */}
            <div className="grid grid-cols-2 gap-2.5 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
                <AnimatePresence>
                    {displayedSounds.map((sound, index) => (
                        <motion.button
                            key={sound.id}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ delay: index * 0.02 }}
                            whileHover={{ scale: isProcessing ? 1 : 1.02 }}
                            whileTap={{ scale: isProcessing ? 1 : 0.98 }}
                            onClick={() => !isProcessing && onSelectDemo(sound)}
                            disabled={isProcessing}
                            className={`
                                relative overflow-hidden p-3 rounded-xl border border-glass-border
                                hover:border-white/20 transition-all duration-200
                                text-left group
                                ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                        >
                            {/* Background gradient overlay */}
                            <div className={`absolute inset-0 bg-gradient-to-br ${sound.color} opacity-5 group-hover:opacity-15 transition-opacity`} />

                            <div className="relative z-10 flex items-center gap-2">
                                <span className="text-2xl flex-shrink-0">{sound.emoji}</span>
                                <div className="flex-1 min-w-0">
                                    <p className="font-semibold text-text-primary text-xs truncate">
                                        {sound.label}
                                    </p>
                                    <p className="text-[10px] text-text-muted truncate">
                                        {sound.description}
                                    </p>
                                </div>
                                <div className="w-6 h-6 rounded-full flex items-center justify-center bg-white/5 group-hover:bg-white/10 transition-colors flex-shrink-0">
                                    <Play className="w-3 h-3 text-white fill-current" />
                                </div>
                            </div>
                        </motion.button>
                    ))}
                </AnimatePresence>
            </div>

            {/* Expand/Collapse Button */}
            {hasMore && (
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="w-full py-2 flex items-center justify-center gap-2 text-sm text-primary hover:text-primary-light transition-colors"
                >
                    {expanded ? (
                        <>
                            <ChevronUp className="w-4 h-4" />
                            Show Less
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-4 h-4" />
                            Show All {filteredSounds.length} Demos
                        </>
                    )}
                </button>
            )}

            <p className="text-xs text-text-muted text-center">
                Select any demo to hear your pet's translation
            </p>
        </div>
    );
};

export default DemoSoundSelector;
export { DEMO_SOUNDS, UNIQUE_ANIMALS, UNIQUE_EMOTIONS };
