import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Try to import librosa, but don't fail if not available
try:
    import librosa

    LIBROSA_AVAILABLE = True
    logger.info("Librosa audio processing available")
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("Librosa not available. Audio processing will use fallback mode.")


def load_audio_to_numpy(file_path, sr=22050):
    """
    Load audio (including WebM/Opus from mic recordings) to a mono float32
    numpy array resampled to `sr`. Returns (y, sr) or (None, sr) on failure.
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if LIBROSA_AVAILABLE and ext not in (".webm", ".opus"):
            y, actual_sr = librosa.load(file_path, sr=sr, mono=True)
            return y, sr
        # WebM/Opus (and any other unsupported container) via PyAV + numpy
        import av
        import numpy as np

        container = av.open(file_path)
        stream = container.streams.audio[0]
        frames = []
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=sr)
        for frame in container.decode(stream):
            for out_frame in resampler.resample(frame):
                arr = out_frame.to_ndarray()
                if arr.ndim > 1:
                    arr = arr[0]
                frames.append(arr)
        container.close()
        if not frames:
            logger.warning("No audio frames decoded from %s", file_path)
            return None, sr
        y = np.concatenate(frames)
        return y.astype(np.float32), sr
    except Exception as e:
        logger.error(f"Error loading audio {file_path}: {e}")
        return None, sr


def load_and_preprocess_audio(file_path, duration=3, sr=22050):
    """
    Load audio file, denoise (simple), and extract comprehensive audio features.

    Args:
        file_path: Path to the audio file
        duration: Maximum duration to process in seconds
        sr: Sample rate for processing

    Returns:
        Dict with MFCC features + spectral features for animal/emotion classification
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return None

        # Load raw audio
        if LIBROSA_AVAILABLE:
            y, _ = _load_raw_audio(file_path, duration, sr)
        else:
            y, _ = load_audio_to_numpy(file_path, sr=sr)

        if y is None or len(y) == 0:
            logger.warning("Empty audio file")
            return _generate_mock_features(file_path)

        # Simple noise reduction (trim silence)
        if LIBROSA_AVAILABLE:
            y, _ = librosa.effects.trim(y, top_db=25)

        if len(y) == 0:
            logger.warning("Audio file contains only silence")
            return _generate_mock_features(file_path)

        # Pad or truncate to ensure consistent length
        target_length = int(sr * duration)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)))
        else:
            y = y[:target_length]

        # Extract comprehensive features
        features = _extract_all_features(y, sr)

        logger.info(
            f"Extracted audio features: "
            f"centroid={features['spectral_centroid']:.1f}Hz, "
            f"zcr={features['zero_crossing_rate']:.3f}, "
            f"rms={features['rms_energy']:.3f}, "
            f"rolloff={features['spectral_rolloff']:.1f}Hz"
        )
        return features

    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return _generate_mock_features(file_path)


def _load_raw_audio(file_path, duration, sr):
    """Load raw audio waveform using librosa or PyAV fallback."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".webm", ".opus"):
        return load_audio_to_numpy(file_path, sr=sr)
    y, _ = librosa.load(file_path, sr=sr, duration=duration, mono=True)
    return y, sr


def _extract_all_features(y, sr):
    """Extract a comprehensive feature set for deterministic animal classification."""
    features = {}

    # ---- MFCCs (timbre / vocal tract shape) ----
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    features["mfcc_mean"] = np.mean(mfccs.T, axis=0)
    features["mfcc_std"] = np.std(mfccs.T, axis=0)

    # ---- Spectral Centroid (brightness / "piercingness") ----
    # Dog barks: lower centroid; Cat meows: higher, more modulated centroid
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    features["spectral_centroid"] = float(np.mean(centroid))
    features["spectral_centroid_std"] = float(np.std(centroid))

    # ---- Zero Crossing Rate (voicing / noisiness) ----
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features["zero_crossing_rate"] = float(np.mean(zcr))
    features["zero_crossing_rate_std"] = float(np.std(zcr))

    # ---- Spectral Rolloff (frequency below which X% of energy lies) ----
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    features["spectral_rolloff"] = float(np.mean(rolloff))
    features["spectral_rolloff_std"] = float(np.std(rolloff))

    # ---- RMS Energy (loudness / intensity) ----
    rms = librosa.feature.rms(y=y)[0]
    features["rms_energy"] = float(np.mean(rms))
    features["rms_energy_std"] = float(np.std(rms))

    # ---- Spectral Bandwidth (spread of spectrum) ----
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    features["spectral_bandwidth"] = float(np.mean(bandwidth))

    # ---- Spectral Contrast (distinctness of peaks vs valleys) ----
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    features["spectral_contrast_mean"] = float(np.mean(contrast))
    features["spectral_contrast_std"] = float(np.std(contrast))

    # ---- Fundamental frequency estimate (pitch) via autocorrelation ----
    features["estimated_pitch"] = _estimate_pitch(y, sr)
    features["estimated_pitch_std"] = _estimate_pitch_std(y, sr)

    # ---- Onset strength (temporal burstiness - bark vs meow) ----
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    features["onset_strength_mean"] = float(np.mean(onset_env))
    features["onset_strength_std"] = float(np.std(onset_env))
    features["onset_count"] = int(
        len(librosa.onset.onset_detect(y=y, sr=sr, units="frames"))
    )

    # ---- Temporal structure: energy in low/mid/high frequency bands ----
    stft = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    low_mask = freqs < 500
    mid_mask = (freqs >= 500) & (freqs < 2000)
    high_mask = freqs >= 2000
    total_energy = np.sum(stft) + 1e-9
    features["energy_low_band"] = float(np.sum(stft[low_mask]) / total_energy)
    features["energy_mid_band"] = float(np.sum(stft[mid_mask]) / total_energy)
    features["energy_high_band"] = float(np.sum(stft[high_mask]) / total_energy)

    # Flatten into a single feature vector for ML compatibility
    feature_vector = []
    feature_vector.extend(features["mfcc_mean"])
    feature_vector.extend(features["mfcc_std"])
    feature_vector.extend(
        [
            features["spectral_centroid"],
            features["spectral_centroid_std"],
            features["zero_crossing_rate"],
            features["zero_crossing_rate_std"],
            features["spectral_rolloff"],
            features["spectral_rolloff_std"],
            features["rms_energy"],
            features["rms_energy_std"],
            features["spectral_bandwidth"],
            features["spectral_contrast_mean"],
            features["spectral_contrast_std"],
            features["estimated_pitch"],
            features["estimated_pitch_std"],
            features["onset_strength_mean"],
            features["onset_strength_std"],
            float(features["onset_count"]),
            features["energy_low_band"],
            features["energy_mid_band"],
            features["energy_high_band"],
        ]
    )
    features["feature_vector"] = np.array(feature_vector, dtype=np.float32)

    return features


def _estimate_pitch(y, sr):
    """Estimate fundamental frequency using autocorrelation (fallback if librosa pitch fails)."""
    try:
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
        # Take the strongest pitch per frame
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        if pitch_values:
            return float(np.median(pitch_values))
    except Exception:
        pass
    return 0.0


def _estimate_pitch_std(y, sr):
    """Estimate pitch variability (cats modulate pitch more than dogs)."""
    try:
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        if len(pitch_values) > 1:
            return float(np.std(pitch_values))
    except Exception:
        pass
    return 0.0


def _generate_mock_features(file_path):
    """
    Generate deterministic mock features when librosa is unavailable.
    Uses file properties for consistency (same file -> same features).
    """
    try:
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 1000
        seed = (file_size % 10000) + (hash(file_path) % 1000)
        rng = np.random.RandomState(seed)

        features = {
            "mfcc_mean": rng.randn(13) * 5,
            "mfcc_std": rng.rand(13) * 2,
            "spectral_centroid": float(rng.uniform(800, 3000)),
            "spectral_centroid_std": float(rng.uniform(100, 500)),
            "zero_crossing_rate": float(rng.uniform(0.05, 0.25)),
            "zero_crossing_rate_std": float(rng.uniform(0.01, 0.1)),
            "spectral_rolloff": float(rng.uniform(2000, 5000)),
            "spectral_rolloff_std": float(rng.uniform(200, 800)),
            "rms_energy": float(rng.uniform(0.05, 0.3)),
            "rms_energy_std": float(rng.uniform(0.01, 0.1)),
            "spectral_bandwidth": float(rng.uniform(500, 1500)),
            "spectral_contrast_mean": float(rng.uniform(5, 20)),
            "spectral_contrast_std": float(rng.uniform(1, 5)),
            "estimated_pitch": float(rng.uniform(150, 400)),
            "estimated_pitch_std": float(rng.uniform(10, 80)),
            "onset_strength_mean": float(rng.uniform(0.1, 0.8)),
            "onset_strength_std": float(rng.uniform(0.05, 0.3)),
            "onset_count": int(rng.randint(1, 20)),
            "energy_low_band": float(rng.uniform(0.1, 0.6)),
            "energy_mid_band": float(rng.uniform(0.2, 0.5)),
            "energy_high_band": float(rng.uniform(0.1, 0.4)),
        }
        feature_vector = []
        feature_vector.extend(features["mfcc_mean"])
        feature_vector.extend(features["mfcc_std"])
        feature_vector.extend(
            [
                features["spectral_centroid"],
                features["spectral_centroid_std"],
                features["zero_crossing_rate"],
                features["zero_crossing_rate_std"],
                features["spectral_rolloff"],
                features["spectral_rolloff_std"],
                features["rms_energy"],
                features["rms_energy_std"],
                features["spectral_bandwidth"],
                features["spectral_contrast_mean"],
                features["spectral_contrast_std"],
                features["estimated_pitch"],
                features["estimated_pitch_std"],
                features["onset_strength_mean"],
                features["onset_strength_std"],
                float(features["onset_count"]),
                features["energy_low_band"],
                features["energy_mid_band"],
                features["energy_high_band"],
            ]
        )
        features["feature_vector"] = np.array(feature_vector, dtype=np.float32)
        return features
    except Exception as e:
        logger.error(f"Mock feature generation failed: {e}")
        return {
            "mfcc_mean": np.zeros(13),
            "mfcc_std": np.zeros(13),
            "spectral_centroid": 1500.0,
            "spectral_centroid_std": 200.0,
            "zero_crossing_rate": 0.1,
            "zero_crossing_rate_std": 0.05,
            "spectral_rolloff": 3000.0,
            "spectral_rolloff_std": 300.0,
            "rms_energy": 0.15,
            "rms_energy_std": 0.05,
            "spectral_bandwidth": 800.0,
            "spectral_contrast_mean": 10.0,
            "spectral_contrast_std": 2.0,
            "estimated_pitch": 250.0,
            "estimated_pitch_std": 30.0,
            "onset_strength_mean": 0.3,
            "onset_strength_std": 0.1,
            "onset_count": 5,
            "energy_low_band": 0.4,
            "energy_mid_band": 0.35,
            "energy_high_band": 0.25,
            "feature_vector": np.zeros(55, dtype=np.float32),
        }


def get_audio_duration(file_path):
    """
    Get the duration of an audio file.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in seconds, or None if unable to determine
    """
    try:
        if LIBROSA_AVAILABLE:
            duration = librosa.get_duration(path=file_path)
            return duration
        else:
            file_size = os.path.getsize(file_path)
            estimated_duration = file_size / (128 * 1024 / 8)
            return min(estimated_duration, 30)
    except Exception as e:
        logger.error(f"Could not get audio duration: {e}")
        return None
