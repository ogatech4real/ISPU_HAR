import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import os

# =========================
# LOAD DATA
# =========================

X = np.load("processed/X.npy")
y = np.load("processed/y.npy")

print("X shape:", X.shape)
print("y shape:", y.shape)

# =========================
# TRAIN / TEST SPLIT
# =========================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# =========================
# MODEL ARCHITECTURE
# =========================

input_shape = X_train.shape[1:]  # (120, 6)

model = models.Sequential()

# --- Block 1 ---
model.add(layers.Conv1D(64, kernel_size=5, activation='relu', input_shape=input_shape))
model.add(layers.BatchNormalization())
model.add(layers.MaxPooling1D(2))

# --- Block 2 ---
model.add(layers.Conv1D(128, kernel_size=3, activation='relu'))
model.add(layers.BatchNormalization())
model.add(layers.MaxPooling1D(2))

# --- Block 3 ---
model.add(layers.Conv1D(256, kernel_size=3, activation='relu'))
model.add(layers.BatchNormalization())
model.add(layers.MaxPooling1D(2))

# --- Temporal abstraction ---
model.add(layers.GlobalAveragePooling1D())

# --- Dense head ---
model.add(layers.Dense(128, activation='relu'))
model.add(layers.Dropout(0.3))

model.add(layers.Dense(64, activation='relu'))
model.add(layers.Dropout(0.3))

# --- Output ---
model.add(layers.Dense(5, activation='softmax'))

model.summary()

# =========================
# COMPILE
# =========================

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# =========================
# CALLBACKS
# =========================

callbacks = [
    tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True),
    tf.keras.callbacks.ReduceLROnPlateau(patience=4, factor=0.3)
]

# =========================
# TRAIN
# =========================

history = model.fit(
    X_train, y_train,
    validation_split=0.2,
    epochs=50,
    batch_size=64,
    callbacks=callbacks
)

# =========================
# EVALUATE
# =========================

loss, acc = model.evaluate(X_test, y_test)
print("\nTest Accuracy:", acc)

# =========================
# REPORT
# =========================

y_pred = model.predict(X_test)
y_pred = np.argmax(y_pred, axis=1)

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# =========================
# SAVE MODEL
# =========================

os.makedirs("MEM_STM/model", exist_ok=True)

model.save("MEM_STM/model/full_model.h5")

print("\nModel saved to MEM_STM/model/full_model.h5")