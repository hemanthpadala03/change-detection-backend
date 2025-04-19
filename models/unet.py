import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model

# Load model only once
model = load_model("models/unet_model.h5")

def run_unet(image1_path, image2_path, result_path):
    pad_width = 2

    def load_and_pad(filepath):
        img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        return np.pad(img, ((pad_width, pad_width), (pad_width, pad_width)), mode='constant'), img.shape

    img1_padded, orig_shape = load_and_pad(image1_path)
    img2_padded, _ = load_and_pad(image2_path)

    # Prepare test data
    test_data = []
    for i in range(pad_width, img1_padded.shape[0] - pad_width):
        for j in range(pad_width, img1_padded.shape[1] - pad_width):
            patch1 = img1_padded[i - pad_width:i + pad_width + 1, j - pad_width:j + pad_width + 1]
            patch2 = img2_padded[i - pad_width:i + pad_width + 1, j - pad_width:j + pad_width + 1]
            stacked = np.stack((patch1, patch2), axis=-1)
            test_data.append(stacked)

    X = np.array(test_data)
    preds = model.predict(X, batch_size=128, verbose=0)
    pred_map = (preds > 0.5).astype(np.uint8).reshape(orig_shape)

    # Invert the prediction map
    inverted_map = 1 - pred_map

    # Save result image (scale to 0-255 for visualization)
    cv2.imwrite(result_path, inverted_map * 255)