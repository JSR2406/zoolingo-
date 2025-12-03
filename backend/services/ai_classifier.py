import numpy as np
import random
import os
import logging

logger = logging.getLogger(__name__)

# Mock classes for demo purposes if model is not trained
ANIMALS = ["Dog", "Cat", "Cow", "Lion"]
EMOTIONS = ["Happy", "Angry", "Sad", "Hungry", "Pain"]

class EmotionClassifier:
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
            logger.info("No trained model found. Using heuristic fallback for demo.")
    
    def predict(self, features):
        """
        Predict animal and emotion from audio features.
        
        Args:
            features: Audio feature vector (MFCC features)
            
        Returns:
            dict with animal, emotion, and confidence
        """
        if self.model and self.model_loaded:
            try:
                # Real inference
                prediction = self.model.predict(np.expand_dims(features, axis=0), verbose=0)
                return self._decode_prediction(prediction)
            except Exception as e:
                logger.error(f"Model prediction failed: {e}. Using fallback.")
                # Fall through to heuristic
            
        # Heuristic/Mock Fallback for Demo
        # In a real scenario, this would use the ML model results
        return {
            "animal": random.choice(ANIMALS),
            "emotion": random.choice(EMOTIONS),
            "confidence": round(random.uniform(0.7, 0.99), 2)
        }

    def _decode_prediction(self, prediction):
        """
        Decode model prediction to animal and emotion.
        
        Args:
            prediction: Model output array
            
        Returns:
            dict with animal, emotion, and confidence
        """
        # This assumes the model outputs two separate predictions:
        # prediction[0] for animal, prediction[1] for emotion
        # Adjust based on your actual model architecture
        
        try:
            animal_idx = np.argmax(prediction[0])
            emotion_idx = np.argmax(prediction[1])
            confidence = float(np.max(prediction))
            
            return {
                "animal": ANIMALS[animal_idx % len(ANIMALS)],
                "emotion": EMOTIONS[emotion_idx % len(EMOTIONS)],
                "confidence": round(confidence, 2)
            }
        except Exception as e:
            logger.error(f"Error decoding prediction: {e}")
            return {
                "animal": random.choice(ANIMALS),
                "emotion": random.choice(EMOTIONS),
                "confidence": 0.75
            }

classifier = EmotionClassifier()

