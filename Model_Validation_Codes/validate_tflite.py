import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score

X = np.load("processed/X.npy")
y = np.load("processed/y.npy")

interpreter = tf.lite.Interpreter(model_path="MEM_STM/model/model_quant.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

y_pred = []

for i in range(len(X)):
    x = X[i:i+1].astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], x)
    interpreter.invoke()

    output = interpreter.get_tensor(output_details[0]['index'])
    pred = np.argmax(output)

    y_pred.append(pred)

acc = accuracy_score(y, y_pred)

print("Fixed TFLite Accuracy:", acc)