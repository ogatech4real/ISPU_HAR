import tensorflow as tf
import numpy as np
import os

MODEL_PATH = "MEM_STM/model/full_model.h5"
X_PATH = "processed/X.npy"

model = tf.keras.models.load_model(MODEL_PATH)
X = np.load(X_PATH)

# IMPORTANT: Use more samples
REP_SAMPLES = 1000

def representative_data_gen():
    for i in range(REP_SAMPLES):
        sample = X[i:i+1]
        yield [sample.astype(np.float32)]

converter = tf.lite.TFLiteConverter.from_keras_model(model)

converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_data_gen

converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]

# KEY FIX: Keep float input (critical)
converter.inference_input_type = tf.float32
converter.inference_output_type = tf.float32

tflite_model = converter.convert()

with open("MEM_STM/model/model_quant.tflite", "wb") as f:
    f.write(tflite_model)

print("Saved FIXED model")