import librosa
import numpy as np
from typing import Optional

try:
    from reedsolo import RSCodec
    rs = RSCodec(10) # 10 ECC symbols
except ImportError:
    rs = None

class AIManager:
    def __init__(self):
        self.fec_available = rs is not None

    def reduce_noise(self, audio_path: str) -> Optional[np.ndarray]:
        '''Mock AI noise reduction with librosa'''
        try:
            y, sr = librosa.load(audio_path, sr=None)
            # Simple spectral gating mock denoising
            S = np.abs(librosa.stft(y))
            # Relaxed spectral filtering threshold to preserve FSK structural harmonics
            mask = S > 0.02 * np.max(S)
            denoised_S = S * mask
            denoised = librosa.istft(denoised_S)
            return denoised
        except Exception as e:
            print(f'AI noise reduction error: {e}')
            return None

    def detect_signal(self, audio_path: str) -> float:
        '''Signal detection score'''
        try:
            y, sr = librosa.load(audio_path, sr=None)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            score = np.mean(np.abs(mfccs))
            return float(score)
        except:
            return 0.0

    def apply_fec(self, data: bytes) -> bytes:
        """Applies Reed-Solomon Forward Error Correction."""
        if rs:
            return bytes(rs.encode(data))
        return data

    def recover_errors(self, data: bytes) -> bytes:
        """Real AI-assisted error correction (Reed-Solomon/Forward Error Correction)."""
        if rs:
            try:
                decoded, _, _ = rs.decode(bytearray(data))
                return bytes(decoded)
            except Exception:
                return data
        return data

    def evaluate_quality(self, audio_path: str) -> dict:
        """Evaluate signal quality including noise level and decoding reliability."""
        try:
            y, sr = librosa.load(audio_path, sr=None)
            signal_power = np.mean(y ** 2)
            noise_power = np.var(y) # Mock estimation of noise variance
            
            # Prevent log10 of 0
            if noise_power == 0 or signal_power == 0:
                snr_db = float('inf')
            else:
                snr_db = 10 * np.log10(signal_power / noise_power)
                
            reliability = min(max(snr_db / 30.0, 0), 1.0) * 100 # 0-100% score
            
            return {
                "noise_level": noise_power,
                "snr_db": snr_db,
                "embedding_strength": signal_power,
                "decoding_reliability": reliability
            }
        except Exception as e:
            return {
                "error": str(e),
                "decoding_reliability": 0.0
            }

    def recommend_stego_format(self, payload_length_bytes: int) -> dict:
        """
        AI intelligently recommends the best Encoding and Carrier format based on the exact payload size.
        """
        kb_size = payload_length_bytes / 1024.0
        
        if kb_size < 10:
            rec = "Encoding: Raw Binary | Carrier: PNG Image"
            reason = "Payload size is minimal. Standard image LSB provides maximum stealth."
        elif kb_size <= 500:
            rec = "Encoding: Raw Binary | Carrier: WAV Audio or High-Res Image"
            reason = "Medium payload size requires massive pixel counts. A WAV carrier is safer."
        else:
            rec = "Encoding: Raw Binary | Carrier: Appended Binary (.exe, .pdf)"
            reason = "Massive payload. Standard LSB will crash or distort. Append to a large file instead."
            
        return {
            "recommendation": rec,
            "reason": reason,
            "size_kb": kb_size
        }

ai_manager = AIManager()
