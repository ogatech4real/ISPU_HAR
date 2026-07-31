import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# LOAD DATA
# =========================

X = np.load("processed/X.npy")
y = np.load("processed/y.npy")

# =========================
# LOAD MODEL
# =========================

model = tf.keras.models.load_model("MEM_STM/model/ispu_model.h5")

print("Model loaded successfully")

# =========================
# PREDICTION
# =========================

y_pred = model.predict(X, batch_size=64)
y_pred = np.argmax(y_pred, axis=1)

# =========================
# METRICS
# =========================

acc = accuracy_score(y, y_pred)

print("\nValidation Accuracy:", acc)

print("\nClassification Report:")
print(classification_report(y, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y, y_pred))