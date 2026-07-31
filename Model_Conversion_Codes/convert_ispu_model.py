import os

import numpy as np
import tensorflow as tf

# =========================
# CONFIGURATION
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "data",
    "model",
    "ispu_model_logits_conv3_24.keras"
)

X_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "X.npy"
)

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "data",
    "model",
    "ispu_model_int8_logits_conv3_24.tflite"
)

REP_SAMPLES = 1000
REP_SEED = 42

# =========================
# FILE VALIDATION
# =========================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Logits model not found: {MODEL_PATH}\n"
        "Run train_ispu_model.py first."
    )

if not os.path.exists(X_PATH):
    raise FileNotFoundError(
        f"Calibration dataset not found: {X_PATH}"
    )

# =========================
# LOAD MODEL AND DATA
# =========================

print("[INFO] Loading logits model...")
model = tf.keras.models.load_model(
    MODEL_PATH,
    compile=False
)

print("[INFO] Loading calibration dataset...")
X = np.load(X_PATH).astype(np.float32)

print("[INFO] Model input shape:", model.input_shape)
print("[INFO] Model output shape:", model.output_shape)
print("[INFO] Calibration data shape:", X.shape)

# =========================
# VALIDATION
# =========================

if X.ndim != 3:
    raise ValueError(
        f"Expected calibration data shape (N, 120, 6), received {X.shape}"
    )

if X.shape[1:] != (120, 6):
    raise ValueError(
        f"Expected calibration window shape (120, 6), received {X.shape[1:]}"
    )

if tuple(model.input_shape[1:]) != (120, 6):
    raise ValueError(
        f"Expected model input shape (120, 6), received {model.input_shape[1:]}"
    )

if model.output_shape[-1] != 5:
    raise ValueError(
        f"Expected 5 output classes, received {model.output_shape[-1]}"
    )

if len(X) == 0:
    raise ValueError("Calibration dataset is empty.")

# =========================
# REPRESENTATIVE DATASET
# =========================

def representative_data_gen():
    sample_count = min(REP_SAMPLES, len(X))

    rng = np.random.default_rng(REP_SEED)

    selected_indices = rng.choice(
        len(X),
        size=sample_count,
        replace=False
    )

    for index in selected_indices:
        sample = X[index:index + 1].astype(np.float32)
        yield [sample]

# =========================
# TFLITE CONVERTER
# =========================

converter = tf.lite.TFLiteConverter.from_keras_model(model)


converter.optimizations = [
    tf.lite.Optimize.DEFAULT
]

converter.representative_dataset = representative_data_gen

converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS_INT8
]

converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

# =========================
# CONVERT
# =========================

print("[INFO] Converting logits model to full INT8 TFLite...")

tflite_model = converter.convert()

# =========================
# SAVE
# =========================

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

with open(OUTPUT_PATH, "wb") as file:
    file.write(tflite_model)

print("[SUCCESS] INT8 logits model saved to:")
print(OUTPUT_PATH)
print("[INFO] Model size:", os.path.getsize(OUTPUT_PATH), "bytes")

# =========================
# INTERPRETER SANITY CHECK
# =========================

print("[INFO] Running TFLite interpreter sanity check...")

interpreter = tf.lite.Interpreter(
    model_path=OUTPUT_PATH
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

if len(input_details) != 1:
    raise ValueError(
        f"Expected one model input, found {len(input_details)}"
    )

if len(output_details) != 1:
    raise ValueError(
        f"Expected one model output, found {len(output_details)}"
    )

input_info = input_details[0]
output_info = output_details[0]

print("[INFO] Input shape:", input_info["shape"])
print("[INFO] Input dtype:", input_info["dtype"])
print("[INFO] Input quantization:", input_info["quantization"])

print("[INFO] Output shape:", output_info["shape"])
print("[INFO] Output dtype:", output_info["dtype"])
print("[INFO] Output quantization:", output_info["quantization"])

if input_info["dtype"] != np.int8:
    raise TypeError(
        f"Expected INT8 input, received {input_info['dtype']}"
    )

if output_info["dtype"] != np.int8:
    raise TypeError(
        f"Expected INT8 output, received {output_info['dtype']}"
    )

if tuple(input_info["shape"]) != (1, 120, 6):
    raise ValueError(
        f"Unexpected TFLite input shape: {input_info['shape']}"
    )

if output_info["shape"][-1] != 5:
    raise ValueError(
        f"Unexpected TFLite output shape: {output_info['shape']}"
    )

# =========================
# QUANTIZE SAMPLE
# =========================

sample = X[0:1].astype(np.float32)

input_scale, input_zero_point = input_info["quantization"]

if input_scale <= 0:
    raise ValueError(
        f"Invalid input quantization scale: {input_scale}"
    )

sample_quantized = np.clip(
    np.round(
        sample / input_scale + input_zero_point
    ),
    -128,
    127
).astype(np.int8)

# =========================
# RUN SAMPLE INFERENCE
# =========================

interpreter.set_tensor(
    input_info["index"],
    sample_quantized
)

interpreter.invoke()

output_quantized = interpreter.get_tensor(
    output_info["index"]
)

output_quantized = output_quantized.reshape(-1, 5)

# =========================
# DEQUANTIZE LOGITS
# =========================

output_scale, output_zero_point = output_info["quantization"]

if output_scale > 0:
    output_logits = (
        output_quantized.astype(np.float32)
        - output_zero_point
    ) * output_scale
else:
    output_logits = output_quantized.astype(np.float32)

prediction = int(
    np.argmax(
        output_logits,
        axis=1
    )[0]
)

print("[INFO] Quantized output shape:", output_quantized.shape)
print("[INFO] Dequantized logits:", output_logits[0])
print("[INFO] Sample prediction:", prediction)

print("[SUCCESS] Full INT8 conversion and sanity check completed.")