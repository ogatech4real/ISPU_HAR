import os

import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "data",
    "model",
    "ispu_model_int8_logits_conv3_24.tflite"
)

X_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "X.npy"
)

Y_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "y.npy"
)

# =========================
# FILE VALIDATION
# =========================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"INT8 logits model not found: {MODEL_PATH}\n"
        "Run convert_ispu_model.py first."
    )

if not os.path.exists(X_PATH):
    raise FileNotFoundError(
        f"Input dataset not found: {X_PATH}"
    )

if not os.path.exists(Y_PATH):
    raise FileNotFoundError(
        f"Label dataset not found: {Y_PATH}"
    )

# =========================
# LOAD DATA
# =========================

X = np.load(X_PATH).astype(np.float32)
y = np.load(Y_PATH)

if y.ndim != 1:
    y = y.reshape(-1)

y = y.astype(np.int32)

print("[INFO] Data loaded")
print("[INFO] X shape:", X.shape)
print("[INFO] y shape:", y.shape)

# =========================
# DATA VALIDATION
# =========================

if X.ndim != 3:
    raise ValueError(
        f"Expected X shape (N, 120, 6), received {X.shape}"
    )

if X.shape[1:] != (120, 6):
    raise ValueError(
        f"Expected input window shape (120, 6), received {X.shape[1:]}"
    )

if len(X) != len(y):
    raise ValueError(
        f"X and y have different sample counts: {len(X)} and {len(y)}"
    )

if len(X) == 0:
    raise ValueError("Validation dataset is empty.")

# =========================
# LOAD TFLITE INTERPRETER
# =========================

interpreter = tf.lite.Interpreter(
    model_path=MODEL_PATH
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

print("[INFO] Input details:", input_info)
print("[INFO] Output details:", output_info)

# =========================
# MODEL VALIDATION
# =========================

if input_info["dtype"] != np.int8:
    raise TypeError(
        f"Expected INT8 model input, received {input_info['dtype']}"
    )

if output_info["dtype"] != np.int8:
    raise TypeError(
        f"Expected INT8 model output, received {output_info['dtype']}"
    )

if tuple(input_info["shape"]) != (1, 120, 6):
    raise ValueError(
        f"Unexpected model input shape: {input_info['shape']}"
    )

if output_info["shape"][-1] != 5:
    raise ValueError(
        f"Expected 5 output classes, received shape {output_info['shape']}"
    )

# =========================
# QUANTIZATION PARAMETERS
# =========================

input_scale, input_zero_point = input_info["quantization"]
output_scale, output_zero_point = output_info["quantization"]

if input_scale <= 0:
    raise ValueError(
        f"Invalid input quantization scale: {input_scale}"
    )

print("[INFO] Input quantization:")
print("       scale =", input_scale)
print("       zero point =", input_zero_point)

print("[INFO] Output quantization:")
print("       scale =", output_scale)
print("       zero point =", output_zero_point)

# =========================
# INFERENCE LOOP
# =========================

y_pred = np.empty(len(X), dtype=np.int32)

for index in range(len(X)):

    sample_float = X[index:index + 1]

    # Quantize float input to INT8.
    sample_int8 = np.clip(
        np.round(
            sample_float / input_scale + input_zero_point
        ),
        -128,
        127
    ).astype(np.int8)

    interpreter.set_tensor(
        input_info["index"],
        sample_int8
    )

    interpreter.invoke()

    output_int8 = interpreter.get_tensor(
        output_info["index"]
    )

    output_int8 = output_int8.reshape(-1, 5)

    # Dequantisation is optional for argmax, but retained
    # so the values represent the model's raw output logits.
    if output_scale > 0:
        output_logits = (
            output_int8.astype(np.float32)
            - output_zero_point
        ) * output_scale
    else:
        output_logits = output_int8.astype(np.float32)

    y_pred[index] = int(
        np.argmax(
            output_logits,
            axis=1
        )[0]
    )

    if (index + 1) % 1000 == 0 or (index + 1) == len(X):
        print(
            f"[INFO] Processed {index + 1}/{len(X)} samples"
        )

# =========================
# EVALUATION
# =========================

accuracy = accuracy_score(
    y,
    y_pred
)

print("\n========================================")
print("ISPU INT8 LOGITS VALIDATION RESULTS")
print("========================================")

print(f"\nISPU INT8 accuracy: {accuracy:.6f}")

print("\nClassification Report:\n")
print(
    classification_report(
        y,
        y_pred,
        digits=4,
        zero_division=0
    )
)

print("Confusion Matrix:\n")
print(
    confusion_matrix(
        y,
        y_pred
    )
)

print("\n[SUCCESS] INT8 logits validation completed.")