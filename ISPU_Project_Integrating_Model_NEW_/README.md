# Final ISPU Project Integrating the HAR Model

This folder contains the complete ISPU project integrating the trained Human Activity Recognition (HAR) model for the ISM330IS. It includes the custom application (main.c), generated ST Edge AI network files, build scripts, linker files, and deployment configuration required to build and program the ISPU.

## Target

- Sensor: ISM330IS
- Expansion board: X-NUCLEO-IKS5A1
- Host board: NUCLEO-F401RE
- Runtime: ST Edge AI ISPU runtime

## Input

- Shape: `1 x 120 x 6`
- Type: signed INT8
- Order: `acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z`
- Common runtime ODR: 52 Hz
- Runtime window: 120 samples, non-overlapping

## Classes

| ID | Class |
|---:|---|
| 0 | brushing |
| 1 | chopping |
| 2 | cleaning |
| 3 | idle |
| 4 | pick_drop |

## Output registers

| Register | Meaning |
|---|---|
| DOUT_00 | predicted class ID |
| DOUT_01 | winning raw INT8 score |
| DOUT_02..DOUT_06 | raw INT8 scores for classes 0..4 |
| DOUT_07 | status: 0 valid, 1 runtime error |

## Installation


## Build

From `ispu/make`:

```

Expected output:

```text
ispu/make/bin/ispu.json
```
