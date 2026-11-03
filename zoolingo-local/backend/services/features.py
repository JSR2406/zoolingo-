"""
ZooLingo feature extractor.

Produces a 195-dimensional float32 feature vector from an audio file:

- MFCC-40: per-coefficient mean (40) + std (40) = 80
- Delta-MFCC-40: per-coefficient mean (40) + std (40) = 80
- Spectral centroid: mean (1) + std (1) + IQR (1) = 3
- Spectral bandwidth: mean (1) + std (1) + IQR (1) = 3
- Spectral rolloff: mean (1) + std (1) + IQR (1) = 3
- Zero crossing rate: mean (1) + std (1) + IQR (1) = 3
- RMS energy: mean (1) + std (1) + IQR (1) = 3
- Spectral flatness: mean (1) + std (1) + IQR (1) = 3
- Spectral contrast: per-band mean (7) = 7
- Pitch via YIN: mean (1) + std (1) = 2
- Onset strength: mean (1) + count (1) = 2
- Energy bands: low (1) + mid (1) + high (1) = 3

Total: 80 + 80 + 3 + 3 + 3 + 3 + 3 + 3 + 7 + 2 + 2 + 3 = 195
"""

import numpy as np

try:
    import librosa
    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False

SAMPLE_RATE = 22050
N_MFCC = 40
N_CONTRAST_BANDS = 7
DURATION = 3.0


def _iqr(x):
    """Interquartile range."""
    return float(np.percentile(x, 75) - np.percentile(x, 25))


def extract(path, sr=SAMPLE_RATE, duration=DURATION):
    """
    Extract a 195-dimensional float32 feature vector from an audio file.

    Args:
        path: Path to audio file (.wav, .mp3, etc.)
        sr: Target sample rate
        duration: Max duration in seconds

    Returns:
        numpy array of shape (195,) with dtype float32, or None on failure
    """
    if not _HAS_LIBROSA:
        raise ImportError("librosa is required for feature extraction. "
                          "Install with: pip install librosa")

    try:
        y, sr = librosa.load(path, sr=sr, duration=duration)
        if y is None or len(y) < sr * 0.5:
            return None

        # ---- MFCC-40: mean (40) + std (40) = 80 ----
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)

        # ---- Delta-MFCC-40: mean (40) + std (40) = 80 ----
        delta_mfcc = librosa.feature.delta(mfcc)
        delta_mfcc_mean = np.mean(delta_mfcc, axis=1)
        delta_mfcc_std = np.std(delta_mfcc, axis=1)

        # ---- Spectral features: mean + std + IQR each = 3 x 5 = 15 ----
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        rms = librosa.feature.rms(y=y)[0]
        flatness = librosa.feature.spectral_flatness(y=y)[0]

        centroid_stats = [float(np.mean(centroid)), float(np.std(centroid)), _iqr(centroid)]
        bandwidth_stats = [float(np.mean(bandwidth)), float(np.std(bandwidth)), _iqr(bandwidth)]
        rolloff_stats = [float(np.mean(rolloff)), float(np.std(rolloff)), _iqr(rolloff)]
        zcr_stats = [float(np.mean(zcr)), float(np.std(zcr)), _iqr(zcr)]
        rms_stats = [float(np.mean(rms)), float(np.std(rms)), _iqr(rms)]
        flatness_stats = [float(np.mean(flatness)), float(np.std(flatness)), _iqr(flatness)]

        # ---- Spectral contrast: per-band mean = 7 ----
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=N_CONTRAST_BANDS)
        contrast_means = [float(np.mean(contrast[i])) for i in range(N_CONTRAST_BANDS)]

        # ---- Pitch via YIN: mean + std = 2 ----
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        if pitch_values:
            pitch_mean = float(np.mean(pitch_values))
            pitch_std = float(np.std(pitch_values))
        else:
            pitch_mean = 0.0
            pitch_std = 0.0

        # ---- Onset strength: mean + count = 2 ----
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_mean = float(np.mean(onset_env))
        onset_count = int(np.sum(onset_env > np.mean(onset_env)))

        # ---- Energy bands: low + mid + high = 3 ----
        total_energy = np.sum(rms ** 2) + 1e-10
        low_band = float(np.sum(rms[:len(rms) // 3] ** 2) / total_energy)
        mid_band = float(np.sum(rms[len(rms) // 3:2 * len(rms) // 3] ** 2) / total_energy)
        high_band = float(np.sum(rms[2 * len(rms) // 3:] ** 2) / total_energy)

        # ---- Concatenate all features (195 total) ----
        features = np.concatenate([
            mfcc_mean,                    # 40
            mfcc_std,                     # 40
            delta_mfcc_mean,              # 40
            delta_mfcc_std,               # 40
            centroid_stats,               # 3
            bandwidth_stats,              # 3
            rolloff_stats,                # 3
            zcr_stats,                    # 3
            rms_stats,                    # 3
            flatness_stats,               # 3
            contrast_means,               # 7
            [pitch_mean, pitch_std],      # 2
            [onset_mean, float(onset_count)],  # 2
            [low_band, mid_band, high_band],   # 3
        ]).astype(np.float32)

        assert features.shape[0] == 195, f"Expected 195 features, got {features.shape[0]}"
        return features

    except Exception as e:
        print(f"WARNING: could not extract features from {path}: {e}")
        return None


def extract_dict(path, sr=SAMPLE_RATE, duration=DURATION):
    """
    Extract features and return as a dict compatible with the legacy classifier.

    Returns:
        dict with feature_vector (195-dim float32) and scalar features,
        or None on failure
    """
    vec = extract(path, sr=sr, duration=duration)
    if vec is None:
        return None

    # Map vector positions to named scalar features for backward compatibility
    idx = 0
    mfcc_mean = vec[idx:idx + 40]; idx += 40
    mfcc_std = vec[idx:idx + 40]; idx += 40
    delta_mfcc_mean = vec[idx:idx + 40]; idx += 40
    delta_mfcc_std = vec[idx:idx + 40]; idx += 40
    centroid_mean, centroid_std, centroid_iqr = vec[idx:idx + 3]; idx += 3
    bandwidth_mean, bandwidth_std, bandwidth_iqr = vec[idx:idx + 3]; idx += 3
    rolloff_mean, rolloff_std, rolloff_iqr = vec[idx:idx + 3]; idx += 3
    zcr_mean, zcr_std, zcr_iqr = vec[idx:idx + 3]; idx += 3
    rms_mean, rms_std, rms_iqr = vec[idx:idx + 3]; idx += 3
    flatness_mean, flatness_std, flatness_iqr = vec[idx:idx + 3]; idx += 3
    contrast_means = vec[idx:idx + 7]; idx += 7
    pitch_mean, pitch_std = vec[idx:idx + 2]; idx += 2
    onset_mean, onset_count = vec[idx:idx + 2]; idx += 2
    low_band, mid_band, high_band = vec[idx:idx + 3]; idx += 3

    return {
        "feature_vector": vec,
        "mfcc_mean": float(np.mean(mfcc_mean)),
        "mfcc_std": float(np.mean(mfcc_std)),
        "spectral_centroid": centroid_mean,
        "spectral_centroid_std": centroid_std,
        "zero_crossing_rate": zcr_mean,
        "spectral_rolloff": rolloff_mean,
        "rms_energy": rms_mean,
        "spectral_bandwidth": bandwidth_mean,
        "estimated_pitch": pitch_mean,
        "estimated_pitch_std": pitch_std,
        "onset_count": onset_count,
        "onset_strength_std": onset_mean,
        "energy_low_band": low_band,
        "energy_mid_band": mid_band,
        "energy_high_band": high_band,
    }