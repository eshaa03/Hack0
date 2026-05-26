import numpy as np
import qrcode
from PIL import Image
import soundfile as sf
import librosa

class EncoderModule:
    def __init__(self):
        pass

    def encode_to_audio(self, data: bytes, output_path: str, sr: int = 44100):
        """Encode binary data into a mock audio signal efficiently (PCM Amplitude).
        Avoids massive memory allocations by using vectorised repeats instead of long FFT bins.
        """
        # Time-domain modulation: 1 byte = 4 samples to keep file small & memory safe
        samples_per_byte = 4
        
        # Convert bytes to numpy uint8 array
        arr = np.frombuffer(data, dtype=np.uint8)
        
        # Map 0-255 directly to Audio PCM floats [-1.0 to 1.0]
        norm_arr = (arr.astype(np.float32) / 127.5) - 1.0
        
        # Repeat each mapped float N times for signal integrity
        signal = np.repeat(norm_arr, samples_per_byte)
        
        # Output directly to WAV
        sf.write(output_path, signal, sr, subtype='PCM_16')
        return output_path

    def decode_from_audio(self, input_path: str, sr: int = 44100):
        try:
            # We use soundfile to prevent librosa normalizations dropping resolution
            y, _sr = sf.read(input_path)
            if len(y.shape) > 1:
                y = y[:, 0]  # Mono channel only
                
            samples_per_byte = 4
            num_bytes = len(y) // samples_per_byte
            
            # Truncate to exact multiple
            y_trunc = y[:num_bytes * samples_per_byte]
            
            # Reshape into chunks and mean pool
            segments = y_trunc.reshape(-1, samples_per_byte)
            means = np.mean(segments, axis=1)
            
            # Unmap back to 0-255 uint8 bounds
            decoded = np.round((means + 1.0) * 127.5).astype(int)
            decoded = np.clip(decoded, 0, 255).astype(np.uint8)
            
            return bytes(decoded)
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
