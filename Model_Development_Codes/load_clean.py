import pandas as pd
import numpy as np
import glob
import os

# =========================
# CONFIG
# =========================

INPUT_PATH = "*.csv"
OUTPUT_DIR = "processed"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# LABEL PARSER
# =========================

def extract_label(filename):
    f = filename.lower()

    if "brush" in f:
        return "brushing"
    elif "chop" in f or "cut" in f:
        return "chopping"
    elif "clean" in f or "scrub" in f:
        return "cleaning"
    elif "pick" in f or "drop" in f:
        return "pick_drop"
    elif "idle" in f:
        # Keep orientation info if present
        if "flat" in f:
            return "idle_flat"
        elif "reverse" in f:
            return "idle_reverse"
        elif "sidea" in f:
            return "idle_sideA"
        elif "sideb" in f:
            return "idle_sideB"
        else:
            return "idle"
    else:
        return None

# =========================
# COLUMN NORMALISER
# =========================

def normalize_columns(df):
    df.columns = [c.strip().lower() for c in df.columns]

    col_map = {}

    for c in df.columns:
        if "acc" in c and "x" in c:
            col_map[c] = "acc_x"
        elif "acc" in c and "y" in c:
            col_map[c] = "acc_y"
        elif "acc" in c and "z" in c:
            col_map[c] = "acc_z"
        elif "gyro" in c and "x" in c:
            col_map[c] = "gyro_x"
        elif "gyro" in c and "y" in c:
            col_map[c] = "gyro_y"
        elif "gyro" in c and "z" in c:
            col_map[c] = "gyro_z"
        elif "time" in c:
            col_map[c] = "time"

    df = df.rename(columns=col_map)

    return df

# =========================
# UNIT CONVERSION
# =========================

def convert_units(df):
    # mg → g
    for c in ["acc_x", "acc_y", "acc_z"]:
        if c in df.columns:
            df[c] = df[c] / 1000.0

    # mdps → dps
    for c in ["gyro_x", "gyro_y", "gyro_z"]:
        if c in df.columns:
            df[c] = df[c] / 1000.0

    return df

# =========================
# CLEAN SINGLE FILE
# =========================

def process_file(filepath):
    df = pd.read_csv(filepath)

    df = normalize_columns(df)
    df = convert_units(df)

    label = extract_label(filepath)
    if label is None:
        return None

    df["label"] = label
    df["source"] = os.path.basename(filepath)

    # Keep only required columns
    required_cols = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z", "label"]

    df = df[[c for c in required_cols if c in df.columns]]

    # Drop NaNs
    df = df.dropna()

    return df

# =========================
# MAIN PIPELINE
# =========================

all_data = []

files = glob.glob(INPUT_PATH)

print(f"Found {len(files)} files")

for f in files:
    print(f"Processing: {f}")

    df = process_file(f)

    if df is not None and len(df) > 0:
        all_data.append(df)

# Combine all
df_all = pd.concat(all_data, ignore_index=True)

# =========================
# VALIDATION
# =========================

print("\nFinal dataset shape:", df_all.shape)
print("\nLabel distribution:")
print(df_all["label"].value_counts())

# =========================
# SAVE OUTPUT
# =========================

output_file = os.path.join(OUTPUT_DIR, "cleaned_dataset.csv")
df_all.to_csv(output_file, index=False)

print(f"\nSaved cleaned dataset to: {output_file}")