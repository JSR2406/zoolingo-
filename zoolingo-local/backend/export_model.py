"""
ZooLingo model export script.

Exports the trained Keras model to ONNX format for serverless deployment
without TensorFlow. Uses onnxruntime for inference.

Usage:
    python export_model.py

This reads models/emotion_classifier.h5 and writes models/emotion_classifier.onnx.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)

INPUT_MODEL = os.path.join(_BACKEND_DIR, "models", "emotion_classifier.h5")
OUTPUT_MODEL = os.path.join(_BACKEND_DIR, "models", "emotion_classifier.onnx")


def export_to_onnx():
    """Export Keras H5 model to ONNX format."""
    try:
        import tensorflow as tf
        import tf2onnx
    except ImportError as e:
        print("ERROR: Missing export dependencies: %s" % e)
        print("Install with: pip install tensorflow tf2onnx onnx")
        return 1

    if not os.path.exists(INPUT_MODEL):
        print("ERROR: Input model not found: %s" % INPUT_MODEL)
        print("Run train_eval.py first to train and save a model.")
        return 1

    print("Loading Keras model from %s..." % INPUT_MODEL)
    model = tf.keras.models.load_model(INPUT_MODEL)

    print("Converting to ONNX...")
    spec = (tf.TensorSpec((None, 195), tf.float32, name="input"),)
    output_path = OUTPUT_MODEL

    model_proto, _ = tf2onnx.convert.from_keras(
        model,
        input_signature=spec,
        opset=13,
        output_path=output_path,
    )

    print("ONNX model saved to %s" % output_path)
    print("Model inputs: %s" % [i.name for i in model_proto.graph.input])
    print("Model outputs: %s" % [o.name for o in model_proto.graph.output])

    return 0


if __name__ == "__main__":
    sys.exit(export_to_onnx())