"""
ZooLingo training pipeline with ElevenLabs augmentation.

Focused on dogs and cats (MVP): 6 emotions x 2 species.
Primary dataset:  data/training/{dogs,cats}/...  (from scripts/download_datasets.sh)
Augmentation:    data/test/elevenlabs/{species}_{emotion}.wav  (ElevenLabs SFX)

TensorFlow is imported lazily so this module can be imported in the lite
environment (heuristic classifier fallback) without TF installed.
"""

import os

import numpy as np
import librosa

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)

SAMPLE_RATE = 22050
N_MFCC = 40
DURATION = 3.0

# The 6 focused emotions (ElevenLabs plan)
SIX_EMOTIONS = ["hunger", "pain", "fear", "playfulness", "attention", "aggression"]
EMOTION_MAP = {name: i for i, name in enumerate(SIX_EMOTIONS)}

CLASSIFIER_LABELS = {
    "hunger": "Hungry",
    "pain": "Pain",
    "fear": "Scared",
    "playfulness": "Playful",
    "attention": "Demanding",
    "aggression": "Aggressive",
}

SPECIES = ["dog", "cat"]


def default_elevenlabs_dir():
    return os.path.join(_REPO_ROOT, "data", "test", "elevenlabs")


def default_training_dir():
    return os.path.join(_REPO_ROOT, "data", "training")


def extract_features(file_path):
    """Return the mean MFCC-40 vector for a wav file, or None on failure."""
    try:
        y, sr = librosa.load(file_path, sr=SAMPLE_RATE, duration=DURATION)
        if y is None or len(y) < SAMPLE_RATE * 0.5:
            return None
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
        return np.mean(mfcc, axis=1)
    except Exception as e:
        print(f"   WARNING: could not load {file_path}: {e}")
        return None


def _emotion_label_from_name(name):
    """Map a folder/filename token to a 6-class label index (default hunger)."""
    lowered = name.lower()
    for emotion, idx in EMOTION_MAP.items():
        if emotion in lowered:
            return idx
    return EMOTION_MAP["hunger"]


def load_dataset(data_path=None):
    """
    Load dog/cat wav files from the training tree.

    Emotions are inferred from the subdirectory or filename (falls back to
    'hunger'). Returns (features, labels) aligned with EMOTION_MAP.
    """
    data_path = data_path or default_training_dir()
    print(f"Loading primary dataset from {data_path}...")
    features, labels = [], []

    for species in SPECIES:
        species_dir = os.path.join(data_path, species + "s")
        if not os.path.isdir(species_dir):
            print(f"   WARNING: training dir not found: {species_dir}")
            continue
        for root, _dirs, files in os.walk(species_dir):
            for fname in sorted(files):
                if not fname.lower().endswith((".wav", ".mp3", ".ogg", ".flac")):
                    continue
                path = os.path.join(root, fname)
                feats = extract_features(path)
                if feats is None:
                    continue
                features.append(feats)
                labels.append(_emotion_label_from_name(fname))
                print(f"   Loaded: {path}")

    return np.array(features), np.array(labels)


def load_elevenlabs_dataset(data_dir=None):
    """
    Load the ElevenLabs generated sounds for training augmentation.

    Expects {data_dir}/{species}_{emotion}.wav for species in (dog, cat)
    and emotion in the 6-class set. Returns (features, labels).
    """
    data_dir = data_dir or default_elevenlabs_dir()
    print("Loading ElevenLabs dataset...")

    features, labels = [], []
    for species in SPECIES:
        for emotion in SIX_EMOTIONS:
            file_path = os.path.join(data_dir, f"{species}_{emotion}.wav")
            if not os.path.exists(file_path):
                print(f"   WARNING: file not found: {file_path}")
                continue
            feats = extract_features(file_path)
            if feats is None:
                continue
            features.append(feats)
            labels.append(EMOTION_MAP[emotion])
            print(f"   Loaded: {species}_{emotion}.wav")

    return np.array(features), np.array(labels)


def build_model(input_shape, num_classes):
    """Small MLP classifier (TensorFlow assumed present)."""
    import tensorflow as tf
    from tensorflow.keras import layers, models

    model = models.Sequential(
        [
            layers.Input(shape=input_shape),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(64, activation="relu"),
            layers.Dense(num_classes, activation="softmax"),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train(epochs=50, batch_size=32, validation_split=0.2, use_elevenlabs=True):
    """Train the 6-class model with optional ElevenLabs augmentation."""
    import tensorflow as tf  # noqa: F401  (lazy import)

    X_primary, y_primary = load_dataset()
    print(f"\nPrimary dataset: {len(X_primary)} samples")

    X_elevenlabs, y_elevenlabs = (
        load_elevenlabs_dataset() if use_elevenlabs else (None, None)
    )
    print(
        f"ElevenLabs dataset: {len(X_elevenlabs) if isinstance(X_elevenlabs, np.ndarray) else 0} samples"
    )

    if isinstance(X_elevenlabs, np.ndarray) and len(X_elevenlabs) > 0:
        X = np.concatenate([X_primary, X_elevenlabs])
        y = np.concatenate([y_primary, y_elevenlabs])
        print(f"\nCombined dataset: {len(X)} samples")
    else:
        X, y = X_primary, y_primary
        print("\nUsing primary dataset only")

    if len(X) == 0:
        raise RuntimeError(
            "No training samples found. Download the DEMO-lite dog dataset "
            "(scripts/download_datasets.sh) and/or generate ElevenLabs sounds "
            "(python generate_elevenlabs_sounds.py)."
        )

    num_classes = len(SIX_EMOTIONS)
    input_shape = (N_MFCC,)
    model = build_model(input_shape, num_classes)
    model.summary()

    history = model.fit(
        X,
        y,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        verbose=1,
    )
    return model, history


def evaluate_elevenlabs(model):
    """Evaluate the trained model on the ElevenLabs test set (per emotion)."""
    X_test, y_test = load_elevenlabs_dataset()
    if len(X_test) == 0:
        print("No ElevenLabs test samples to evaluate.")
        return

    predictions = model.predict(X_test, verbose=0)
    predicted = np.argmax(predictions, axis=1)

    accuracy = np.mean(predicted == y_test)
    print(f"\nElevenLabs Test Accuracy: {accuracy:.2%}")

    for i, emotion in enumerate(SIX_EMOTIONS):
        mask = y_test == i
        if np.sum(mask) > 0:
            emotion_acc = np.mean(predicted[mask] == i)
            print(f"   {emotion.capitalize()}: {emotion_acc:.2%}")


def main():
    """Ensure 12 ElevenLabs sounds exist, train, then evaluate."""
    # Step 1: Generate ElevenLabs sounds if missing
    elevenlabs_dir = default_elevenlabs_dir()
    if (
        not os.path.isdir(elevenlabs_dir)
        or len([f for f in os.listdir(elevenlabs_dir) if f.endswith(".wav")]) < 12
    ):
        print("Generating ElevenLabs sounds for training...")
        import generate_elevenlabs_sounds

        if generate_elevenlabs_sounds.main() != 0:
            print("WARNING: ElevenLabs generation failed; continuing without it.")

    # Step 2: Train with augmentation
    print("\nTraining model with ElevenLabs augmentation...")
    model, _history = train(epochs=50, batch_size=32, use_elevenlabs=True)

    # Step 3: Evaluate on the ElevenLabs set
    print("\nEvaluating on ElevenLabs test set...")
    evaluate_elevenlabs(model)

    # Step 4: Persist
    out_path = os.path.join(_BACKEND_DIR, "models", "emotion_classifier.h5")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    model.save(out_path)
    print(f"\nModel saved to {out_path}")
    print("\nNext steps:")
    print("   1. python app.py")
    print("   2. cd frontend && npm run dev")
    print("   3. Use the ElevenLabs Demo Sounds (Dog & Cat) tab to test")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"ERROR: {e}")
        print("TensorFlow is not installed in this environment.")
        print("Install with: pip install tensorflow (use requirements-render.txt)")
    except RuntimeError as e:
        print(f"ERROR: {e}")
