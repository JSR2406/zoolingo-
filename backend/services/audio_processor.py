import librosa
import numpy as np
import os

def load_and_preprocess_audio(file_path, duration=3, sr=22050):
    """
    Load audio file, denoise (simple), and extract MFCC features.
    """
    try:
        # Load audio
        y, sr = librosa.load(file_path, sr=sr, duration=duration)
        
        # Simple noise reduction (trim silence)
        y, _ = librosa.effects.trim(y)
        
        # Pad or truncate to ensure consistent length
        target_length = int(sr * duration)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)))
        else:
            y = y[:target_length]
            
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Return mean of MFCCs (simple feature vector)
        return np.mean(mfccs.T, axis=0)
        
    except Exception as e:
        print(f"Error processing audio: {e}")
        return None
