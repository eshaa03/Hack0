import numpy as np
import qrcode
from PIL import Image
import soundfile as sf
import librosa

class EncoderModule:
    def __init__(self):
        pass

    def encode_to_audio(self, data: bytes, output_path: str, sr: int = 44100):
        """Encode binary data into a mock audio signal (FSK/ASK mock or pure digital noise).
        Here we generate a simple audio signal representing the bytes.
        """
        # A simple method: mapping byte values to frequencies or just generating a noise signal
        # For a robust implementation, real modulation (like FSK) is needed.
        # This is a basic mock that creates a deterministic audio wave from bytes.
        
        # Fix mathematical resolution of FFT bins
        duration = len(data) * 0.1 # 100ms per byte to achieve 10Hz FFT resolution
        t = np.linspace(0, duration, int(sr * duration), False)
        
        # Create a base signal
        signal = np.zeros_like(t)
        samples_per_byte = int(sr * 0.1)
        
        for i, byte in enumerate(data):
            start = i * samples_per_byte
            end = start + samples_per_byte
            # Frequency based on byte value
            freq = 1000 + (byte * 10) 
            signal[start:end] = np.sin(2 * np.pi * freq * t[start:end])
            
        # Normalize
        # Normalize
        signal = signal / (np.max(np.abs(signal)) + 1e-9)
        sf.write(output_path, signal, sr, subtype='PCM_16')
        return output_path

    def decode_from_audio(self, input_path: str, sr: int = 44100):
        try:
            y, _sr = librosa.load(input_path, sr=sr)
            samples_per_byte = int(_sr * 0.1)
            num_bytes = len(y) // samples_per_byte
            
            data = bytearray()
            for i in range(num_bytes):
                start = i * samples_per_byte
                end = start + samples_per_byte
                segment = y[start:end]
                
                # Check if segment is completely silent
                if np.max(np.abs(segment)) < 1e-5:
                    break
                    
                fft_vals = np.abs(np.fft.rfft(segment))
                freqs = np.fft.rfftfreq(len(segment), 1/_sr)
                peak_freq = freqs[np.argmax(fft_vals)]
                
                byte_val = int(round((peak_freq - 1000) / 10))
                byte_val = max(0, min(255, byte_val))
                data.append(byte_val)
                
            return bytes(data)
        except Exception as e:
            print("Audio decode error:", e)
            return None

    def encode_to_qr(self, data: bytes, output_path: str):
        """Encode binary data into a QR Code image."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # QR codes have size limits, so we handle it as hex/base64 string format usually
        # But `add_data` handles bytes correctly in qrcode lib
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        return output_path

encoder = EncoderModule()
