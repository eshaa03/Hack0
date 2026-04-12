




















































































































import numpy as np
from PIL import Image
import librosa
import soundfile as sf
from typing import Tuple, Optional

class StegoManager:
    def __init__(self):
        pass

    def embed_image_lsb(self, image_path: str, data: bytes, output_path: str, bits: int = 1) -> bool:
        '''LSB steganography for images'''
        try:
            img = Image.open(image_path).convert('RGB')
            pixels = np.array(img)

            binary_data = ''.join(format(byte, '08b') for byte in data)
            binary_data += '1' * 64  # End marker
            
            if len(binary_data) > pixels.size:
                print("Carrier image too small to hold payload.")
                return False

            data_index = 0
            new_pixels = pixels.copy()

            for i in range(pixels.shape[0]):
                for j in range(pixels.shape[1]):
                    for k in range(3):  # RGB
                        if data_index < len(binary_data):
                            new_pixels[i, j, k] = self.replace_lsb(new_pixels[i, j, k], binary_data[data_index])
                            data_index += 1
                        if data_index >= len(binary_data):
                            break
                    if data_index >= len(binary_data):
                        break
                if data_index >= len(binary_data):
                    break

            new_img = Image.fromarray(new_pixels.astype(np.uint8))
            new_img.save(output_path)
            return True
        except Exception as e:
            print(f'Stego embed error: {e}')
            return False

    def extract_image_lsb(self, image_path: str, output_path: str) -> Optional[bytes]:
        '''Extract from image LSB'''
        try:
            img = Image.open(image_path).convert('RGB')
            pixels = np.array(img)

            binary_data = ''
            end_found = False

            for i in range(pixels.shape[0]):
                for j in range(pixels.shape[1]):
                    for k in range(3):
                        binary_data += str(pixels[i, j, k] & 1)
                        if len(binary_data) % 8 == 0:
                            if binary_data[-64:] == '1' * 64:
                                end_found = True
                                break
                    if end_found:
                        break
                if end_found:
                    break

            bytes_data = bytes(int(binary_data[i:i+8], 2) for i in range(0, len(binary_data)-64, 8))
            with open(output_path, 'wb') as f:
                f.write(bytes_data)
            return bytes_data
        except Exception as e:
            print(f'Stego extract error: {e}')
            return None

    def embed_audio_lsb(self, audio_path: str, data: bytes, output_path: str, bits: int = 1) -> bool:
        '''LSB for audio - embed in samples'''
        try:
            y, sr = librosa.load(audio_path, sr=None)
            binary_data = ''.join(format(byte, '08b') for byte in data) + ('1' * 64)
            
            if len(binary_data) > len(y):
                print("Carrier audio too small to hold payload.")
                return False

            data_index = 0
            new_y = y.copy().astype(np.int16)

            for i in range(len(new_y)):
                if data_index < len(binary_data):
                    new_y[i] = self.replace_lsb(new_y[i], binary_data[data_index])
                    data_index += 1
                if data_index >= len(binary_data):
                    break

            sf.write(output_path, new_y, sr, subtype='PCM_16')
            return True
        except:
            return False

    def replace_lsb(self, value: int, bit: str) -> int:
        value = value & ~1  # Clear LSB
        if bit == '1':
            value |= 1
        return value

    def extract_audio_lsb(self, audio_path: str, output_path: str) -> Optional[bytes]:
        """Extract data hidden in audio LSB."""
        try:
            y, sr = librosa.load(audio_path, sr=None)
            binary_data = ''
            end_found = False

            y_int = y.astype(np.int16)
            for val in y_int:
                binary_data += str(val & 1)
                if len(binary_data) % 8 == 0:
                    if binary_data[-64:] == '1' * 64:
                        end_found = True
                        break
            
            bytes_data = bytes(int(binary_data[i:i+8], 2) for i in range(0, len(binary_data)-64, 8))
            with open(output_path, 'wb') as f:
                f.write(bytes_data)
            return bytes_data
        except Exception as e:
            print(f'Stego extract audio error: {e}')
            return None

    def embed_file_append(self, file_path: str, data: bytes, output_path: str) -> bool:
        """Embed data by appending it to the end of a generic file."""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Use a magic marker to find data later
            marker = b'<<HACK0_MARKER>>'
            combined = file_data + marker + data
            
            with open(output_path, 'wb') as f:
                f.write(combined)
            return True
        except Exception as e:
            print(f'Stego embed file error: {e}')
            return False

    def extract_file_append(self, file_path: str, output_path: str) -> Optional[bytes]:
        """Extract appended data from a generic file."""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            marker = b'<<HACK0_MARKER>>'
            idx = file_data.rfind(marker)
            if idx == -1:
                return None
            
            extracted_data = file_data[idx + len(marker):]
            with open(output_path, 'wb') as f:
                f.write(extracted_data)
            return extracted_data
        except Exception as e:
            print(f'Stego extract file error: {e}')
            return None

stego_manager = StegoManager()
