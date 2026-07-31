import json
import os

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import layers

# =========================
# REPRODUCIBILITY
# =========================

SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODEL_DIR = os.path.join(DATA_DIR, "model")

os.makedirs(MODEL_DIR, exist_ok=True)

X_PATH = os.path.join(PROCESSED_DIR, "X.npy")
Y_PATH = os.path.join(PROCESSED_DIR, "y.npy")

HISTORY_PATH = os.path.join(
    MODEL_DIR,
    "ispu_history_logits_conv3_24.json"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "ispu_model_logits_conv3_24.keras"
)

FEATURES_PATH = os.path.join(
    PROCESSED_DIR,
    "features_ispu_logits_conv3_24.npy"
)

LABELS_PATH = os.path.join(
    PROCESSED_DIR,
    "labels_ispu_logits_conv3_24.npy"
)

# =========================
# LOAD DATA
# =========================

if not os.path.exists(X_PATH):
    raise FileNotFoundError(f"Input data not found: {X_PATH}")

if not os.path.exists(Y_PATH):
    raise FileNotFoundError(f"Label data not found: {Y_PATH}")

X = np.load(X_PATH)
y = np.load(Y_PATH)

print("X shape:", X.shape)
print("y shape:", y.shape)

if X.ndim != 3:
    raise ValueError(
        f"Expected X shape (samples, 120, 6), but received {X.shape}"
    )

if X.shape[1:] != (120, 6):
    raise ValueError(
        f"Expected input window shape (120, 6), but received {X.shape[1:]}"
    )

if y.ndim != 1:
    y = y.reshape(-1)

if len(X) != len(y):
    raise ValueError(
        f"X and y contain different sample counts: {len(X)} and {len(y)}"
    )

X = X.astype(np.float32)
y = y.astype(np.int32)

# =========================
# CLASS WEIGHTS
# =========================

classes = np.unique(y)

if len(classes) != 5:
    raise ValueError(
        f"Expected 5 activity classes, but found {len(classes)}: {classes}"
    )

weights = compute_class_weight(
    class_weight="balanced",
    classes=classes,
    y=y
)

class_weight = {
    int(class_id): float(weight)
    for class_id, weight in zip(classes, weights)
}

print("Classes:", classes)
print("Class weights:", class_weight)

# =========================
# TRAIN / TEST SPLIT
# =========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=SEED
)

print("Training samples:", X_train.shape)
print("Test samples:", X_test.shape)

# =========================
# MODEL
# =========================

inputs = tf.keras.Input(
    shape=(120, 6),
    name="sensor_input"
)

x = layers.Conv1D(
    filters=16,
    kernel_size=5,
    activation="relu",
    name="conv1"
)(inputs)

x = layers.MaxPooling1D(
    pool_size=2,
    name="pool1"
)(x)

x = layers.Conv1D(
    filters=32,
    kernel_size=3,
    activation="relu",
    name="conv2"
)(x)

x = layers.MaxPooling1D(
    pool_size=2,
    name="pool2"
)(x)

x = layers.Conv1D(
    filters=24,
    kernel_size=3,
    activation="relu",
    name="conv3"
)(x)

x = layers.GlobalAveragePooling1D(
    name="global_average_pool"
)(x)

feature_layer = layers.Dense(
    units=32,
    activation="relu",
    name="feature_layer"
)(x)

# Raw logits are used instead of softmax.
# Argmax(logits) produces the same predicted class as argmax(softmax(logits)).
outputs = layers.Dense(
    units=5,
    activation=None,
    name="logits"
)(feature_layer)

# =========================
# MODEL
# =========================

inputs = tf.keras.Input(
    shape=(120, 6),
    name="sensor_input"
)

x = layers.Conv1D(
    filters=16,
    kernel_size=5,
    activation="relu",
    name="conv1"
)(inputs)

x = layers.MaxPooling1D(
    pool_size=2,
    name="pool1"
)(x)

x = layers.Conv1D(
    filters=32,
    kernel_size=3,
    activation="relu",
    name="conv2"
)(x)

x = layers.MaxPooling1D(
    pool_size=2,
    name="pool2"
)(x)

# Reduced from 32 to 24 filters to lower ISPU scratch
# and activation-memory requirements.
x = layers.Conv1D(
    filters=24,
    kernel_size=3,
    activation="relu",
    name="conv3"
)(x)

x = layers.GlobalAveragePooling1D(
    name="global_average_pool"
)(x)

feature_layer = layers.Dense(
    units=32,
    activation="relu",
    name="feature_layer"
)(x)

outputs = layers.Dense(
    units=5,
    activation=None,
    name="logits"
)(feature_layer)

model = tf.keras.Model(
    inputs=inputs,
    outputs=outputs,
    name="ispu_har_logits_conv3_24_model"
)

model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=1e-3
    ),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(
        from_logits=True
    ),
    metrics=["accuracy"]
)

model.summary()

# =========================
# TRAIN
# =========================

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=6,
        restore_best_weights=True
    ),
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        patience=3,
        factor=0.3,
        min_lr=1e-6
    )
]

history = model.fit(
    X_train,
    y_train,
    validation_split=0.2,
    epochs=40,
    batch_size=64,
    class_weight=class_weight,
    callbacks=callbacks,
    verbose=1
)

# =========================
# SAVE TRAINING HISTORY
# =========================

serializable_history = {
    key: [float(value) for value in values]
    for key, values in history.history.items()
}

with open(HISTORY_PATH, "w", encoding="utf-8") as file:
    json.dump(
        serializable_history,
        file,
        indent=2
    )

print(f"[OK] ISPU training history saved to: {HISTORY_PATH}")

# =========================
# EVALUATION
# =========================

loss, accuracy = model.evaluate(
    X_test,
    y_test,
    verbose=0
)

print(f"\nISPU test loss: {loss:.6f}")
print(f"ISPU test accuracy: {accuracy:.6f}")

logits = model.predict(
    X_test,
    batch_size=64,
    verbose=0
)

y_pred = np.argmax(
    logits,
    axis=1
)

print("\nClassification Report:\n")
print(
    classification_report(
        y_test,
        y_pred,
        digits=4,
        zero_division=0
    )
)

print("Confusion Matrix:\n")
print(
    confusion_matrix(
        y_test,
        y_pred
    )
)

# =========================
# FEATURE EXPORT FOR t-SNE
# =========================

feature_model = tf.keras.Model(
    inputs=model.inputs,
    outputs=model.get_layer("feature_layer").output
)

features = feature_model.predict(
    X,
    batch_size=64,
    verbose=0
)

np.save(
    FEATURES_PATH,
    features.astype(np.float32)
)

np.save(
    LABELS_PATH,
    y
)

print(f"[OK] ISPU features saved to: {FEATURES_PATH}")
print(f"[OK] ISPU labels saved to: {LABELS_PATH}")

# =========================
# SAVE MODEL
# =========================

model.save(MODEL_PATH)

print(f"[OK] ISPU logits model saved to: {MODEL_PATH}")