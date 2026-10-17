"""
Real animal-sound classifier using Google's YAMNet (Apache-2.0).

YAMNet predicts 521 audio event classes from the AudioSet ontology, including
real dog (Bark, Bow-wow, Yip, Howl, Growling, Whimper), cat (Meow, Purr, Hiss,
Caterwaul) and other animal vocalisations. This module maps those sound events
to ZooLingo's animal + emotion labels so "processing audio" actually reflects
what was heard.

Falls back to the legacy heuristic classifier if YAMNet/TensorFlow is missing.
"""
import os
import csv
import logging
import numpy as np

logger = logging.getLogger(__name__)

# --- AudioSet -> ZooLingo animal mapping --------------------------------
# Each AudioSet display name votes for an animal. Lower-priority aliases
# (generic classes like "Canidae, dogs, wolves") are only used when the
# specific class is absent.
ANIMAL_CLASS_MAP = {
    "Dog": {
        "Dog": 1.0,
        "Bark": 1.0,
        "Bow-wow": 1.0,
        "Yip": 0.9,
        "Howl": 0.7,
        "Whimper (dog)": 0.9,
        "Canidae, dogs, wolves": 0.5,
    },
    "Cat": {
        "Cat": 1.0,
        "Meow": 1.0,
        "Purr": 0.9,
        "Hiss": 0.8,
        "Caterwaul": 0.9,
    },
    "Cow": {
        "Cattle, bovinae": 1.0,
        "Moo": 1.0,
    },
    "Pig": {
        "Pig": 1.0,
        "Oink": 0.9,
        "Grunt": 0.6,
    },
    "Horse": {
        "Horse": 1.0,
        "Neigh, whinny": 1.0,
    },
    "Sheep": {
        "Sheep": 1.0,
    },
    "Goat": {
        "Goat": 1.0,
    },
    "Chicken": {
        "Chicken, rooster": 1.0,
        "Cluck": 0.9,
        "Crowing, cock-a-doodle-doo": 1.0,
    },
    "Duck": {
        "Duck": 1.0,
        "Quack": 1.0,
    },
    "Bird": {
        "Bird": 1.0,
        "Bird vocalization, bird call, bird song": 1.0,
        "Squawk": 0.8,
        "Crow": 0.8,
        "Pigeon, dove": 0.7,
    },
    "Lion": {
        "Roaring cats (lions, tigers)": 1.0,
        "Roar": 1.0,
    },
    "Wolf": {
        "Canidae, dogs, wolves": 0.6,
        "Howl": 0.7,
    },
    "Turkey": {
        "Turkey": 1.0,
    },
    "Goose": {
        "Goose": 1.0,
    },
}

# --- AudioSet sound events -> ZooLingo emotions -------------------------
EMOTION_CLASS_MAP = {
    "Bark": {"Excited": 0.4, "Alert": 0.3, "Happy": 0.2, "Playful": 0.1},
    "Bow-wow": {"Excited": 0.4, "Happy": 0.3, "Alert": 0.3},
    "Yip": {"Excited": 0.7, "Playful": 0.3},
    "Howl": {"Lonely": 0.5, "Sad": 0.3, "Alert": 0.2},
    "Whimper (dog)": {"Sad": 0.5, "Scared": 0.3, "Pain": 0.2},
    "Whimper": {"Sad": 0.5, "Scared": 0.3, "Pain": 0.2},
    "Growling": {"Aggressive": 0.5, "Angry": 0.5},
    "Meow": {"Demanding": 0.4, "Hungry": 0.3, "Curious": 0.3},
    "Purr": {"Happy": 0.7, "Calm": 0.3},
    "Hiss": {"Aggressive": 0.5, "Scared": 0.3, "Angry": 0.2},
    "Caterwaul": {"Scared": 0.4, "Angry": 0.3, "Lonely": 0.3},
    "Moo": {"Calm": 0.4, "Curious": 0.3, "Demanding": 0.3},
    "Neigh, whinny": {"Excited": 0.5, "Alert": 0.3, "Happy": 0.2},
    "Cluck": {"Chatty": 0.4, "Curious": 0.3, "Happy": 0.3},
    "Crowing, cock-a-doodle-doo": {"Alert": 0.4, "Demanding": 0.3, "Excited": 0.3},
    "Quack": {"Chatty": 0.4, "Demanding": 0.3, "Curious": 0.3},
    "Squawk": {"Chatty": 0.4, "Demanding": 0.3, "Alert": 0.3},
    "Roar": {"Aggressive": 0.5, "Angry": 0.3, "Alert": 0.2},
    "Grunt": {"Curious": 0.4, "Hungry": 0.3, "Calm": 0.3},
    "Oink": {"Hungry": 0.4, "Happy": 0.3, "Excited": 0.3},
    # Generic animal sound -> neutral happy-ish default
    "Animal": {"Curious": 0.4, "Happy": 0.3, "Alert": 0.3},
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

# Fallback emotions when no event-level emotion was detected
DEFAULT_EMOTION = "Curious"


def _locate_class_map() -> str:
    """Locate the bundled YAMNet class map CSV."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "models", "yamnet_class_map.csv"),
        os.path.join(here, "..", "..", "models", "yamnet_class_map.csv"),
        os.path.join(here, "yamnet_class_map.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class YAMNetAnimalClassifier:
    """
    Real animal vocalisation classifier powered by YAMNet.

    Loads the TF-Hub YAMNet model lazily. If TensorFlow/TF-Hub is unavailable
    or the model cannot be loaded, raises ModuleNotFoundError/RuntimeError so
    callers can fall back to the legacy classifier.
    """

    MODEL_URL = "https://tfhub.dev/google/yamnet/1"
    SAMPLE_RATE = 16000

    def __init__(self, model_url=None, class_map_path=None):
        self.model_url = model_url or self.MODEL_URL
        self._model = None
        self._class_names = None
        class_map_path = class_map_path or _locate_class_map()
        self.class_map_path = class_map_path

    # -- lifecycle -------------------------------------------------------
    @property
    def available(self) -> bool:
        try:
            self._ensure_model()
            return True
        except Exception:
            return False

    def _ensure_model(self):
        if self._model is None:
            import tensorflow as tf
            import tensorflow_hub as hub

            os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
            tf.get_logger().setLevel("ERROR")
            self._model = hub.load(self.model_url)
            self._class_names = self._load_class_names()
            logger.info("YAMNet model loaded from %s", self.model_url)

    def _load_class_names(self):
        if not self.class_map_path or not os.path.exists(self.class_map_path):
            # Download the canonical class map when models/yamnet_class_map.csv
            # is missing so the service is self-sufficient.
            import urllib.request

            url = (
                "https://raw.githubusercontent.com/tensorflow/models/master/"
                "research/audioset/yamnet/yamnet_class_map.csv"
            )
            dest_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "models"
            )
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, "yamnet_class_map.csv")
            logger.info("Downloading YAMNet class map: %s", url)
            urllib.request.urlretrieve(url, dest)
            self.class_map_path = dest

        names = {}
        with open(self.class_map_path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) >= 3 and row[0].isdigit():
                    names[int(row[0])] = row[2]
        return names

    # -- inference -------------------------------------------------------
    def _load_audio(self, file_path):
        """Return float32 mono audio resampled to 16 kHz (webm/opus supported)."""
        import scipy.signal as sig
        from services.audio_processor import load_audio_to_numpy

        data, sr = load_audio_to_numpy(file_path, sr=self.SAMPLE_RATE)
        if data is None:
            return None
        data = data.astype(np.float32)
        if sr != self.SAMPLE_RATE:
            data = sig.resample_poly(data, self.SAMPLE_RATE, sr)
        return data

    def _audio_energy(self, data) -> float:
        if data is None or len(data) == 0:
            return 0.0
        return float(np.sqrt(np.mean(data**2)))

    def classify(self, file_path, top_k=10):
        """
        Classify an audio file into {animal, emotion, confidence, evidence}.

        Returns None if YAMNet cannot run (missing deps) or if the sound
        scores are essentially silence/unknown.
        """
        try:
            self._ensure_model()
        except Exception as exc:
            logger.warning("YAMNet unavailable: %s", exc)
            return None

        try:
            data = self._load_audio(file_path)
        except Exception as exc:
            logger.error("Failed to decode %s: %s", file_path, exc)
            return None

        if data is None or len(data) < self.SAMPLE_RATE // 10:
            logger.warning("Audio too short/empty: %s", file_path)
            return None

        scores, _embeddings, _spectrogram = self._model(data)
        frame_scores = scores.numpy()
        mean_scores = np.mean(frame_scores, axis=0)

        top_idx = np.argsort(mean_scores)[::-1][:top_k]
        evidence = []
        animal_votes = {}
        emotion_votes = {}

        for idx in top_idx:
            class_name = self._class_names.get(int(idx), "")
            score = float(mean_scores[idx])
            if score < 0.05:
                continue
            evidence.append({"class": class_name, "score": round(score, 4)})

            # animal votes
            for animal, aliases in ANIMAL_CLASS_MAP.items():
                weight = aliases.get(class_name)
                if weight:
                    animal_votes[animal] = (
                        animal_votes.get(animal, 0.0) + weight * score
                    )

            # emotion votes
            emotion_weights = EMOTION_CLASS_MAP.get(class_name)
            if emotion_weights:
                for emotion, w in emotion_weights.items():
                    emotion_votes[emotion] = emotion_votes.get(emotion, 0.0) + w * score

        if not animal_votes:
            logger.info("No animal sound events detected for %s", file_path)
            return None

        animal = max(animal_votes, key=animal_votes.get)
        animal_conf = round(min(0.99, animal_votes[animal]), 2)

        if emotion_votes:
            emotion = max(emotion_votes, key=emotion_votes.get)
        else:
            emotion = DEFAULT_EMOTION

        result = {
            "animal": animal,
            "emotion": emotion,
            "confidence": animal_conf,
            "classifier": "yamnet",
            "evidence": evidence,
        }
        logger.info(
            "YAMNet classify %s -> %s-%s (conf=%s)",
            os.path.basename(file_path),
            animal,
            emotion,
            animal_conf,
        )
        return result


# Global singleton
yamnet_classifier = YAMNetAnimalClassifier()
