import numpy as np
from PIL import Image

def replace_lsb(value, bit):
    value = value & ~1
    if bit == '1':
        value |= 1
    return value

pixels = np.zeros((10, 10, 3), dtype=np.uint8)
binary_data = '1' * 1000

data_index = 0
new_pixels = pixels.copy()

for i in range(pixels.shape[0]):
    for j in range(pixels.shape[1]):
        for k in range(3):
            if data_index < len(binary_data):
                new_pixels[i, j, k] = replace_lsb(new_pixels[i, j, k], binary_data[data_index])
                data_index += 1
            if data_index >= len(binary_data):
                break
        if data_index >= len(binary_data):
            break
    if data_index >= len(binary_data):
        break

print("Finished successfully")
