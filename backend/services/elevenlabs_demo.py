"""
ElevenLabs dog/cat demo sounds metadata.

Focused on dogs and cats only (MVP): 6 emotions x 2 species = 12 sounds.
These are pre-generated into config.ELEVENLABS_DEMO_DIR by
`backend/generate_elevenlabs_sounds.py` and exposed via
`GET /api/demo/sounds` for the demo selector + training augmentation.
"""

# The 6 emotions (plan keys) mapped to the runtime classifier's labels
EMOTION_KEYS = ["hunger", "pain", "fear", "playfulness", "attention", "aggression"]

CLASSIFIER_LABEL = {
    "hunger": "Hungry",
    "pain": "Pain",
    "fear": "Scared",
    "playfulness": "Playful",
    "attention": "Demanding",
    "aggression": "Aggressive",
}

EMOTION_DISPLAY = {
    "hunger": "Hungry",
    "pain": "Pain",
    "fear": "Scared",
    "playfulness": "Playful",
    "attention": "Attention",
    "aggression": "Aggressive",
}

SPECIES = ["dog", "cat"]

SPECIES_DISPLAY = {"dog": "Dog", "cat": "Cat"}

HINDI_ANIMAL = {"dog": "कुत्ता", "cat": "बिल्ली"}

# Sound-effect prompts tuned for realistic single-animal vocalizations
SOUND_PROMPTS = {
    "dog": {
        "hunger": "A hungry dog whining and softly barking, pleading for food, realistic single dog",
        "pain": "A dog whimpering in pain with distressed yelps and whines",
        "fear": "A scared dog whining and yelping anxiously, high pitched fearful barking",
        "playfulness": "A happy playful dog barking excitedly with joyful yips and short barks",
        "attention": "A dog barking insistently with short sharp barks, wanting attention",
        "aggression": "An aggressive dog growling and barking fiercely, threatening and menacing",
    },
    "cat": {
        "hunger": "A hungry cat meowing loudly and persistently, seeking food",
        "pain": "A cat crying in pain, distressed meowing and yowling",
        "fear": "A scared cat hissing and yowling in fear, defensive",
        "playfulness": "A playful cat chirping and meowing happily, excited",
        "attention": "A cat meowing insistently and repeatedly, demanding attention",
        "aggression": "An aggressive cat hissing and growling fiercely, territorial",
    },
}

# Expected translations (reference for the demo; runtime translations come from
# ZooLingo's SARVAM LLM + TTS pipeline)
EXPECTED_TRANSLATIONS = {
    "hunger": {
        "en": "Your {animal} is hungry and looking for food!",
        "hi": "आपका {animal} भूखा है और खाना ढूंढ रहा है!",
    },
    "pain": {
        "en": "Your {animal} seems to be in pain or discomfort.",
        "hi": "आपका {animal} दर्द या बेचैनी में लग रहा है।",
    },
    "fear": {
        "en": "Your {animal} is feeling scared or anxious.",
        "hi": "आपका {animal} डरा हुआ या चिंतित महसूस कर रहा है।",
    },
    "playfulness": {
        "en": "Your {animal} is excited and wants to play!",
        "hi": "आपका {animal} उत्साहित है और खेलना चाहता है!",
    },
    "attention": {
        "en": "Your {animal} wants your attention.",
        "hi": "आपका {animal} आपका ध्यान चाहता है।",
    },
    "aggression": {
        "en": "Warning: Your {animal} is feeling defensive.",
        "hi": "चेतावनी: आपका {animal} रक्षात्मक महसूस कर रहा है।",
    },
}


def all_sounds():
    """Build the 12-sound metadata list (dog + cat x 6 emotions)."""
    sounds = []
    for species in SPECIES:
        for emotion in EMOTION_KEYS:
            sounds.append(
                {
                    "species": species,
                    "animal": SPECIES_DISPLAY[species],
                    "emotion": emotion,
                    "label": EMOTION_DISPLAY[emotion],
                    "classifier_label": CLASSIFIER_LABEL[emotion],
                    "filename": f"{species}_{emotion}.wav",
                    "prompt": SOUND_PROMPTS[species][emotion],
                    "expected_en": EXPECTED_TRANSLATIONS[emotion]["en"].format(
                        animal=SPECIES_DISPLAY[species]
                    ),
                    "expected_hi": EXPECTED_TRANSLATIONS[emotion]["hi"].format(
                        animal=HINDI_ANIMAL[species]
                    ),
                }
            )
    return sounds
