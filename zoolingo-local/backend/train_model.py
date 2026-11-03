"""
ZooLingo training pipeline with honest held-out evaluation.

Focused on dogs and cats (MVP): 6 emotions x 2 species.
Primary dataset:  data/training/{dogs,cats}/...  (from scripts/download_datasets.sh)
TensorFlow is imported lazily so this module can be imported in the lite
environment (heuristic classifier fallback) without TF installed.
"""

import os

import numpy as np

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


def default_training_dir():
    return os.path.join(_REPO_ROOT, "data", "training")


def extract_features(file_path):
    """Return the mean MFCC-40 vector for a wav file, or None on failure."""
    try:
        import librosa

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


def _speaker_id_from_name(name):
    """Extract speaker ID from filename for speaker-disjoint splitting."""
    import re

    match = re.search(r"(?:cat|dog)_(\d+)", name)
    if match:
        return match.group(1)
    return "unknown"


def load_dataset(data_path=None):
    """
    Load dog/cat wav files from the training tree.

    Emotions are inferred from the subdirectory or filename (falls back to
    'hunger'). Returns (features, labels, speaker_ids) aligned with EMOTION_MAP.
    """
    data_path = data_path or default_training_dir()
    print(f"Loading primary dataset from {data_path}...")
    features, labels, speakers = [], [], []

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
                speakers.append(_speaker_id_from_name(fname))
                print(f"   Loaded: {path}")

    return np.array(features), np.array(labels), np.array(speakers)


def speaker_disjoint_split(X, y, speakers, test_size=0.2):
    """
    Split data into train/test with speaker-disjoint groups.
    Ensures no speaker appears in both train and test sets.
    """
    from sklearn.model_selection import train_test_split

    unique_speakers = np.unique(speakers)
    train_speakers, test_speakers = train_test_split(
        unique_speakers, test_size=test_size, random_state=42
    )

    train_mask = np.isin(speakers, train_speakers)
    test_mask = np.isin(speakers, test_speakers)

    return (X[train_mask], y[train_mask]), (X[test_mask], y[test_mask])


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


def train(epochs=50, batch_size=32, validation_split=0.2):
    """Train the 6-class model with speaker-disjoint split."""
    import tensorflow as tf  # noqa: F401  (lazy import)

    X, y, speakers = load_dataset()
    print(f"\nPrimary dataset: {len(X)} samples")

    if len(X) == 0:
        raise RuntimeError(
            "No training samples found. Download datasets "
            "(scripts/download_datasets.sh) before training."
        )

    # Speaker-disjoint split to prevent data leakage
    (X_train, y_train), (X_test, y_test) = speaker_disjoint_split(X, y, speakers)
    print(f"   Train samples: {len(X_train)}")
    print(f"   Test samples: {len(X_test)}")

    num_classes = len(SIX_EMOTIONS)
    input_shape = (N_MFCC,)
    model = build_model(input_shape, num_classes)
    model.summary()

    history = model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        verbose=1,
    )

    # Evaluate on held-out test set
    predictions = model.predict(X_test, verbose=0)
    predicted = np.argmax(predictions, axis=1)
    test_accuracy = np.mean(predicted == y_test)

    # Majority baseline
    majority_class = np.bincount(y_test).argmax()
    baseline_accuracy = np.mean(y_test == majority_class)
    print(f"\nHeld-out Test Accuracy: {test_accuracy:.2%}")
    print(f"Majority-class baseline: {baseline_accuracy:.2%}")
    print(f"Improvement over baseline: {(test_accuracy - baseline_accuracy):.2%}")

    return model, history, (X_test, y_test)


def main():
    """Train model with speaker-disjoint evaluation."""
    # Train with speaker-disjoint split
    print("\nTraining model with speaker-disjoint evaluation...")
    model, history, (X_test, y_test) = train(
        epochs=50, batch_size=32, validation_split=0.2
    )

    # Persist
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
        print("TensorFlow or scikit-learn not installed in this environment.")
        print("Install with: pip install tensorflow scikit-learn")
    except RuntimeError as e:
        print(f"ERROR: {e}")