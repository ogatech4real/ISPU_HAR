import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import LabelEncoder

# =========================
# CONFIG
# =========================

INPUT_FILE = "processed/cleaned_dataset.csv"
OUTPUT_DIR = "processed"

WINDOW_SIZE = 120   # ~2 seconds
STEP = 60           # 50% overlap

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# LOAD DATA
# =========================

df = pd.read_csv(INPUT_FILE)

print("Loaded dataset:", df.shape)

# =========================
# MERGE IDLE CLASSES
# =========================

df["label"] = df["label"].apply(
    lambda x: "idle" if "idle" in x else x
)

print("\nLabel distribution after merge:")
print(df["label"].value_counts())

# =========================
# FEATURE SELECTION
# =========================

feature_cols = [
    "acc_x", "acc_y", "acc_z",
    "gyro_x", "gyro_y", "gyro_z"
]

# =========================
# WINDOWING
# =========================

X = []
y = []

for label in df["label"].unique():
    df_label = df[df["label"] == label]

    data = df_label[feature_cols].values

    for i in range(0, len(data) - WINDOW_SIZE, STEP):
        window = data[i:i+WINDOW_SIZE]

        # Skip corrupted windows
        if np.isnan(window).any():
            continue

        X.append(window)
        y.append(label)

X = np.array(X)
y = np.array(y)

print("\nWindowed data shape:", X.shape)

# =========================
# LABEL ENCODING
# =========================

le = LabelEncoder()
y_encoded = le.fit_transform(y)

print("\nClasses:", list(le.classes_))

# Save label mapping
label_map = dict(zip(le.classes_, range(len(le.classes_))))
print("\nLabel mapping:", label_map)

# =========================
# NORMALISATION
# =========================

mean = X.mean(axis=(0,1))
std = X.std(axis=(0,1)) + 1e-6

X = (X - mean) / std

# =========================
# SAVE OUTPUT
# =========================

np.save(os.path.join(OUTPUT_DIR, "X.npy"), X)
np.save(os.path.join(OUTPUT_DIR, "y.npy"), y_encoded)

# Save metadata
np.save(os.path.join(OUTPUT_DIR, "mean.npy"), mean)
np.save(os.path.join(OUTPUT_DIR, "std.npy"), std)

# Save label names
with open(os.path.join(OUTPUT_DIR, "labels.txt"), "w") as f:
    for l in le.classes_:
        f.write(l + "\n")

print("\nSaved:")
print("X.npy, y.npy, mean.npy, std.npy, labels.txt")