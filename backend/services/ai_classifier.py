import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Comprehensive list of supported animals and emotions
ANIMALS = [
    "Dog",
    "Cat",
    "Cow",
    "Lion",
    "Bird",
    "Horse",
    "Elephant",
    "Sheep",
    "Goat",
    "Pig",
    "Chicken",
    "Duck",
    "Monkey",
    "Parrot",
    "Wolf",
]

EMOTIONS = [
    "Happy",
    "Angry",
    "Sad",
    "Hungry",
    "Pain",
    "Excited",
    "Scared",
    "Curious",
    "Playful",
    "Calm",
    "Demanding",
    "Alert",
    "Mischievous",
    "Proud",
    "Bossy",
    "Singing",
    "Chatty",
    "Aggressive",
    "Lonely",
]

# Common emotions that work for most animals
COMMON_EMOTIONS = [
    "Happy",
    "Angry",
    "Sad",
    "Hungry",
    "Pain",
    "Excited",
    "Scared",
    "Curious",
]

# Animal-specific emotion preferences (used as priors, not random selection)
ANIMAL_EMOTION_WEIGHTS = {
    "Dog": {
        "Happy": 0.25,
        "Excited": 0.20,
        "Playful": 0.15,
        "Hungry": 0.10,
        "Sad": 0.10,
        "Scared": 0.10,
        "Curious": 0.05,
        "Angry": 0.05,
    },
    "Cat": {
        "Happy": 0.15,
        "Demanding": 0.20,
        "Angry": 0.15,
        "Curious": 0.15,
        "Hungry": 0.10,
        "Scared": 0.10,
        "Sad": 0.10,
        "Excited": 0.05,
    },
    "Cow": {
        "Calm": 0.25,
        "Happy": 0.20,
        "Hungry": 0.20,
        "Sad": 0.15,
        "Angry": 0.10,
        "Pain": 0.10,
    },
    "Lion": {
        "Proud": 0.25,
        "Angry": 0.20,
        "Hungry": 0.20,
        "Happy": 0.15,
        "Sad": 0.10,
        "Pain": 0.10,
    },
    "Bird": {
        "Happy": 0.20,
        "Singing": 0.20,
        "Alert": 0.15,
        "Hungry": 0.15,
        "Scared": 0.10,
        "Curious": 0.10,
        "Angry": 0.05,
        "Sad": 0.05,
    },
    "Horse": {
        "Happy": 0.20,
        "Calm": 0.20,
        "Excited": 0.15,
        "Hungry": 0.15,
        "Angry": 0.10,
        "Scared": 0.10,
        "Sad": 0.05,
        "Pain": 0.05,
    },
    "Elephant": {
        "Happy": 0.20,
        "Sad": 0.20,
        "Hungry": 0.20,
        "Angry": 0.15,
        "Pain": 0.15,
        "Calm": 0.10,
    },
    "Sheep": {"Happy": 0.30, "Scared": 0.30, "Hungry": 0.20, "Calm": 0.20},
    "Goat": {
        "Mischievous": 0.30,
        "Happy": 0.25,
        "Angry": 0.20,
        "Hungry": 0.15,
        "Curious": 0.10,
    },
    "Pig": {
        "Happy": 0.30,
        "Hungry": 0.30,
        "Curious": 0.20,
        "Excited": 0.10,
        "Calm": 0.10,
    },
    "Chicken": {
        "Happy": 0.25,
        "Scared": 0.25,
        "Bossy": 0.20,
        "Hungry": 0.15,
        "Alert": 0.15,
    },
    "Duck": {"Happy": 0.40, "Demanding": 0.30, "Curious": 0.15, "Scared": 0.15},
    "Monkey": {
        "Mischievous": 0.30,
        "Happy": 0.25,
        "Angry": 0.20,
        "Excited": 0.15,
        "Curious": 0.10,
    },
    "Parrot": {
        "Chatty": 0.30,
        "Happy": 0.25,
        "Angry": 0.20,
        "Excited": 0.15,
        "Demanding": 0.10,
    },
    "Wolf": {
        "Aggressive": 0.25,
        "Happy": 0.20,
        "Lonely": 0.20,
        "Hungry": 0.20,
        "Alert": 0.15,
    },
}

# Audio frequency characteristics for different animal types
ANIMAL_FREQUENCY_PROFILES = {
    "low": ["Cow", "Elephant", "Lion", "Horse"],
    "medium": ["Dog", "Wolf", "Pig", "Sheep", "Goat"],
    "high": ["Cat", "Bird", "Chicken", "Duck", "Monkey", "Parrot"],
}

# Emotions considered "high intensity" for calm/intense variant selection
INTENSE_EMOTIONS = {
    "Angry",
    "Excited",
    "Scared",
    "Pain",
    "Aggressive",
    "Alert",
    "Demanding",
    "Bossy",
    "Mischievous",
}

# Fallback emotions when no clear emotion was detected
DEFAULT_EMOTION = "Curious"


def _sigmoid(x):
    """Numerically stable sigmoid."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def _weighted_choice_deterministic(items, weights, seed_val=0):
    """
    Deterministic weighted selection using a seed derived from input features.
    Same input -> same output. No randomness.
    """
    rng = np.random.RandomState(int(seed_val) % (2**31))
    total = sum(weights)
    if total <= 0:
        return items[0]
    probs = [w / total for w in weights]
    return rng.choice(items, p=probs)


class EmotionClassifier:
    """
    Deterministic AI classifier for detecting animal type and emotion from
    audio features. Uses spectral analysis (centroid, ZCR, pitch, energy bands)
    to distinguish animals like Dog vs Cat, then classifies emotion from
    energy, pitch modulation, and temporal structure.

    Falls back to a trained TensorFlow model if available.
    """

    def __init__(self, model_path=None):
        self.model = None
        self.model_loaded = False

        if model_path is None:
            model_path = os.getenv("MODEL_PATH", "models/emotion_classifier.h5")

        if model_path and os.path.exists(model_path):
            try:
                import tensorflow as tf

                self.model = tf.keras.models.load_model(model_path)
                self.model_loaded = True
                logger.info(f"Loaded trained model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}. Using heuristic fallback.")
        else:
            logger.info(
                "No trained model found. Using deterministic heuristic classification."
            )

    def predict(self, features):
        """
        Predict animal and emotion from audio features.

        Args:
            features: Dict from audio_processor.load_and_preprocess_audio()
                      or a raw numpy feature vector.

        Returns:
            dict with animal, emotion, confidence, classifier ("yamnet"|"heuristic"|"model")
        """
        if self.model and self.model_loaded:
            try:
                if isinstance(features, dict):
                    feat_vec = features.get("feature_vector", None)
                else:
                    feat_vec = features

                if feat_vec is not None:
                    prediction = self.model.predict(
                        np.expand_dims(feat_vec, axis=0), verbose=0
                    )
                    return self._decode_prediction(prediction)
            except Exception as e:
                logger.error(f"Model prediction failed: {e}. Using heuristic fallback.")

        # Deterministic heuristic classification
        return self._heuristic_classify(features)

    def _heuristic_classify(self, features):
        """
        Deterministic, feature-based classification.

        Dog detection: lower spectral centroid, strong low-band energy,
                       periodic burst onsets, lower pitch variability.
        Cat detection: higher spectral centroid, strong pitch modulation
                       (formant sweeps), higher ZCR, vowel-like tonality.
        """
        try:
            if features is None:
                raise ValueError("Empty features")

            # Accept both dict and raw vector
            if isinstance(features, dict):
                f = features
                feat_vec = f.get("feature_vector", None)
            else:
                f = None
                feat_vec = np.asarray(features, dtype=np.float32)

            # Extract scalar features (with safe defaults)
            centroid = f.get("spectral_centroid", 1500.0) if f else 1500.0
            centroid_std = f.get("spectral_centroid_std", 200.0) if f else 200.0
            zcr = f.get("zero_crossing_rate", 0.1) if f else 0.1
            rolloff = f.get("spectral_rolloff", 3000.0) if f else 3000.0
            rms = f.get("rms_energy", 0.15) if f else 0.15
            bandwidth = f.get("spectral_bandwidth", 800.0) if f else 800.0
            pitch = f.get("estimated_pitch", 250.0) if f else 250.0
            pitch_std = f.get("estimated_pitch_std", 30.0) if f else 30.0
            onset_count = f.get("onset_count", 5) if f else 5
            onset_std = f.get("onset_strength_std", 0.1) if f else 0.1
            energy_low = f.get("energy_low_band", 0.4) if f else 0.4
            energy_mid = f.get("energy_mid_band", 0.35) if f else 0.35
            energy_high = f.get("energy_high_band", 0.25) if f else 0.25
            mfcc_mean = f.get("mfcc_mean", np.zeros(13)) if f else np.zeros(13)
            mfcc_std = f.get("mfcc_std", np.zeros(13)) if f else np.zeros(13)

            # ---- Step 1: Animal detection (deterministic, feature-based) ----
            animal_scores = {}

            # Base scores from frequency profile (pitch centroid)
            if centroid < 1200:
                pitch_category = "low"
            elif centroid < 2200:
                pitch_category = "medium"
            else:
                pitch_category = "high"

            for animal in ANIMALS:
                score = 0.0

                # Frequency profile match
                for category, animals in ANIMAL_FREQUENCY_PROFILES.items():
                    if animal in animals:
                        if pitch_category == category:
                            score += 2.5
                        else:
                            score += 0.3
                        break

                # Dog-specific signals
                if animal == "Dog":
                    # Dogs: strong low-band energy, lower centroid, bursty onsets
                    if energy_low > 0.35:
                        score += 2.0
                    if centroid < 1800:
                        score += 1.5
                    if onset_count >= 3:  # barks are repetitive/bursty
                        score += 1.0
                    if (
                        pitch_std < 60
                    ):  # dogs have relatively stable pitch within a bark
                        score += 1.0
                    if zcr < 0.18:  # less noisy than a meow's turbulent airflow
                        score += 0.5

                # Cat-specific signals
                elif animal == "Cat":
                    # Cats: higher centroid, strong pitch modulation (meow sweep),
                    # higher ZCR (turbulent), more high-band energy
                    if centroid > 1800:
                        score += 2.0
                    if pitch_std > 50:  # meows sweep up/down in pitch
                        score += 2.0
                    if zcr > 0.12:
                        score += 1.0
                    if energy_high > 0.20:
                        score += 1.0
                    if 0.5 < rolloff < 4500:
                        score += 0.5

                # Cow
                elif animal == "Cow":
                    if centroid < 1000:
                        score += 2.0
                    if energy_low > 0.45:
                        score += 1.5
                    if pitch_std < 40:
                        score += 1.0

                # Lion
                elif animal == "Lion":
                    if centroid < 1100:
                        score += 2.0
                    if rms > 0.18:  # loud, powerful
                        score += 1.5
                    if onset_count <= 4:  # fewer, more powerful roars
                        score += 1.0

                # Bird
                elif animal == "Bird":
                    if centroid > 2500:
                        score += 2.0
                    if zcr > 0.15:
                        score += 1.0
                    if onset_count > 6:  # rapid chirps
                        score += 1.5

                # Horse
                elif animal == "Horse":
                    if 800 < centroid < 1600:
                        score += 1.5
                    if energy_mid > 0.35:
                        score += 1.0
                    if pitch < 300:
                        score += 1.0

                # Elephant
                elif animal == "Elephant":
                    if centroid < 900:
                        score += 2.5
                    if energy_low > 0.50:
                        score += 1.5

                # Sheep
                elif animal == "Sheep":
                    if 1000 < centroid < 1800:
                        score += 1.5
                    if onset_count >= 2 and onset_count <= 6:
                        score += 1.0

                # Goat
                elif animal == "Goat":
                    if 1000 < centroid < 2000:
                        score += 1.5
                    if zcr > 0.12:
                        score += 1.0

                # Pig
                elif animal == "Pig":
                    if centroid < 1400:
                        score += 1.5
                    if energy_low > 0.40:
                        score += 1.0
                    if onset_std > 0.1:  # grunts are irregular
                        score += 1.0

                # Chicken
                elif animal == "Chicken":
                    if centroid > 2000:
                        score += 1.5
                    if zcr > 0.15:
                        score += 1.0
                    if onset_count > 5:
                        score += 1.0

                # Duck
                elif animal == "Duck":
                    if 1500 < centroid < 2500:
                        score += 1.5
                    if zcr > 0.12:
                        score += 1.0

                # Monkey
                elif animal == "Monkey":
                    if centroid > 1800:
                        score += 1.5
                    if pitch_std > 40:
                        score += 1.0
                    if onset_count > 4:
                        score += 1.0

                # Parrot
                elif animal == "Parrot":
                    if centroid > 2000:
                        score += 1.5
                    if zcr > 0.14:
                        score += 1.0

                # Wolf
                elif animal == "Wolf":
                    if centroid < 1300:
                        score += 1.5
                    if energy_low > 0.35:
                        score += 1.0
                    if onset_count <= 3:  # howls are long, few onsets
                        score += 1.0

                # MFCC shape match (simple: use mfcc mean magnitude as additional signal)
                mfcc_mag = float(np.mean(np.abs(mfcc_mean)))
                score += min(1.0, mfcc_mag * 0.05)

                animal_scores[animal] = score

            # Select best animal deterministically
            best_animal = max(animal_scores, key=animal_scores.get)
            best_score = animal_scores[best_animal]
            total_score = (
                sum(animal_scores.values()) if sum(animal_scores.values()) > 0 else 1.0
            )
            animal_confidence = min(0.98, 0.55 + (best_score / total_score) * 0.40)

            # ---- Step 2: Emotion detection (deterministic, feature-based) ----
            emotion = self._classify_emotion_deterministic(
                best_animal,
                centroid,
                centroid_std,
                zcr,
                rolloff,
                rms,
                bandwidth,
                pitch,
                pitch_std,
                onset_count,
                onset_std,
                energy_low,
                energy_mid,
                energy_high,
                mfcc_std,
            )

            # ---- Step 3: Confidence ----
            # Higher confidence when features are clear (high energy, distinct spectral shape)
            clarity = min(0.20, rms * 2.0 + bandwidth * 0.0001)
            confidence = min(0.98, animal_confidence * 0.6 + clarity * 0.4)

            return {
                "animal": best_animal,
                "emotion": emotion,
                "confidence": round(confidence, 2),
                "classifier": "heuristic",
                "animal_scores": {
                    k: round(v, 2)
                    for k, v in sorted(animal_scores.items(), key=lambda x: -x[1])[:5]
                },
            }

        except Exception as e:
            logger.error(f"Heuristic classification failed: {e}")
            return self._fallback_classify()

    def _classify_emotion_deterministic(
        self,
        animal,
        centroid,
        centroid_std,
        zcr,
        rolloff,
        rms,
        bandwidth,
        pitch,
        pitch_std,
        onset_count,
        onset_std,
        energy_low,
        energy_mid,
        energy_high,
        mfcc_std,
    ):
        """
        Classify emotion deterministically from audio features.

        Intensity mapping:
        - High energy + high pitch modulation + many onsets -> Excited / Angry / Aggressive
        - Low energy + low centroid + few onsets -> Sad / Calm / Pain
        - Moderate energy + steady pitch -> Happy / Hungry / Curious
        - High ZCR + high centroid -> Alert / Scared / Demanding
        """
        # Compute intensity from energy and onset activity
        intensity_score = (
            rms * 2.0
            + min(1.0, onset_count / 10.0) * 1.5
            + min(1.0, pitch_std / 80.0) * 1.0
        )

        if intensity_score > 2.2:
            intensity = "high"
        elif intensity_score > 1.1:
            intensity = "medium"
        else:
            intensity = "low"

        # Base emotion probabilities by intensity
        intensity_emotion_map = {
            "high": {
                "Angry": 0.22,
                "Excited": 0.20,
                "Aggressive": 0.14,
                "Scared": 0.12,
                "Pain": 0.10,
                "Demanding": 0.10,
                "Alert": 0.08,
                "Happy": 0.04,
            },
            "medium": {
                "Happy": 0.20,
                "Hungry": 0.18,
                "Curious": 0.15,
                "Playful": 0.14,
                "Excited": 0.10,
                "Demanding": 0.10,
                "Mischievous": 0.06,
                "Chatty": 0.07,
            },
            "low": {
                "Calm": 0.25,
                "Sad": 0.22,
                "Happy": 0.18,
                "Hungry": 0.15,
                "Curious": 0.10,
                "Lonely": 0.05,
                "Pain": 0.05,
            },
        }

        base_probs = intensity_emotion_map.get(
            intensity, intensity_emotion_map["medium"]
        )

        # Animal-specific emotion priors
        animal_weights = ANIMAL_EMOTION_WEIGHTS.get(animal, {})

        # Feature-based adjustments
        adjustments = {}

        # High pitch modulation -> Excited, Scared, Demanding
        if pitch_std > 70:
            adjustments["Excited"] = adjustments.get("Excited", 0) + 0.10
            adjustments["Scared"] = adjustments.get("Scared", 0) + 0.08
            adjustments["Demanding"] = adjustments.get("Demanding", 0) + 0.06

        # Low centroid + low energy -> Sad, Calm, Pain
        if centroid < 1200 and rms < 0.10:
            adjustments["Sad"] = adjustments.get("Sad", 0) + 0.12
            adjustments["Calm"] = adjustments.get("Calm", 0) + 0.08
            adjustments["Pain"] = adjustments.get("Pain", 0) + 0.06

        # Many onsets + high energy -> Playful, Excited, Angry
        if onset_count > 6 and rms > 0.15:
            adjustments["Playful"] = adjustments.get("Playful", 0) + 0.10
            adjustments["Excited"] = adjustments.get("Excited", 0) + 0.08
            adjustments["Angry"] = adjustments.get("Angry", 0) + 0.06

        # High ZCR -> Alert, Scared
        if zcr > 0.16:
            adjustments["Alert"] = adjustments.get("Alert", 0) + 0.08
            adjustments["Scared"] = adjustments.get("Scared", 0) + 0.06

        # Merge base probs with animal weights and adjustments
        final_probs = {}
        all_emotions = (
            set(base_probs.keys())
            | set(animal_weights.keys())
            | set(adjustments.keys())
        )

        for emotion in all_emotions:
            base = base_probs.get(emotion, 0.04)
            animal_w = animal_weights.get(emotion, 0.05)
            adj = adjustments.get(emotion, 0.0)
            # Weighted blend: base (40%) + animal prior (40%) + feature adjustment (20%)
            final_probs[emotion] = base * 0.4 + animal_w * 0.4 + adj * 0.2

        # Normalize
        total = sum(final_probs.values())
        if total <= 0:
            return DEFAULT_EMOTION
        final_probs = {k: v / total for k, v in final_probs.items()}

        # Deterministic selection using feature-derived seed
        seed_val = int((centroid * 10) + (pitch * 10) + (rms * 1000) + (zcr * 1000))
        emotions = list(final_probs.keys())
        probs = list(final_probs.values())

        return _weighted_choice_deterministic(emotions, probs, seed_val)

    def _fallback_classify(self):
        """Pure fallback when all else fails (deterministic, no randomness)."""
        # Use a fixed seed based on a hash of constants for determinism
        animal = ANIMALS[0]  # Dog as safest fallback
        emotions = list(ANIMAL_EMOTION_WEIGHTS.get(animal, {}).keys())
        probs = list(ANIMAL_EMOTION_WEIGHTS.get(animal, {}).values())
        emotion = _weighted_choice_deterministic(emotions, probs, seed_val=42)

        return {
            "animal": animal,
            "emotion": emotion,
            "confidence": 0.65,
            "classifier": "heuristic",
            "animal_scores": {},
        }

    def _decode_prediction(self, prediction):
        """Decode model prediction to animal and emotion."""
        try:
            if isinstance(prediction, (tuple, list)) and len(prediction) >= 2:
                animal_pred = prediction[0]
                emotion_pred = prediction[1]

                animal_idx = int(np.argmax(animal_pred))
                emotion_idx = int(np.argmax(emotion_pred))

                animal_conf = float(np.max(animal_pred))
                emotion_conf = float(np.max(emotion_pred))
                confidence = (animal_conf + emotion_conf) / 2
            else:
                flat_pred = np.array(prediction).flatten()

                num_animals = len(ANIMALS)
                num_emotions = len(COMMON_EMOTIONS)

                if len(flat_pred) >= num_animals + num_emotions:
                    animal_idx = int(np.argmax(flat_pred[:num_animals]))
                    emotion_idx = int(
                        np.argmax(flat_pred[num_animals : num_animals + num_emotions])
                    )
                    confidence = float(np.max(flat_pred))
                else:
                    animal_idx = int(np.argmax(flat_pred)) % num_animals
                    emotion_idx = int(np.argmax(flat_pred)) % num_emotions
                    confidence = float(np.max(flat_pred))

            return {
                "animal": ANIMALS[animal_idx % len(ANIMALS)],
                "emotion": COMMON_EMOTIONS[emotion_idx % len(COMMON_EMOTIONS)],
                "confidence": round(min(0.99, confidence), 2),
                "classifier": "model",
            }

        except Exception as e:
            logger.error(f"Error decoding prediction: {e}")
            return self._fallback_classify()

    @staticmethod
    def get_supported_animals():
        """Return list of all supported animals."""
        return ANIMALS.copy()

    @staticmethod
    def get_supported_emotions():
        """Return list of all supported emotions."""
        return EMOTIONS.copy()

    @staticmethod
    def get_common_emotions():
        """Return list of common emotions applicable to most animals."""
        return COMMON_EMOTIONS.copy()


# Global classifier instance
classifier = EmotionClassifier()
