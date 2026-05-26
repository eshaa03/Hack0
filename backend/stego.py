import numpy as np
from PIL import Image
import librosa
import soundfile as sf
from typing import Optional


class StegoManager:
    HEADER_MAGIC = b"H0SG"
    HEADER_SIZE = 12
    LEGACY_END_MARKER_BITS = "1" * 64

    def __init__(self):
        pass

    def _pack_payload(self, data: bytes) -> bytes:
        return self.HEADER_MAGIC + len(data).to_bytes(8, "big") + data

    def _unpack_payload(self, payload: bytes) -> Optional[bytes]:
        if len(payload) < self.HEADER_SIZE or not payload.startswith(self.HEADER_MAGIC):
            return None

        payload_len = int.from_bytes(payload[4:12], "big")
        end_index = self.HEADER_SIZE + payload_len
        if end_index > len(payload):
            return None
        return payload[self.HEADER_SIZE:end_index]

    def _bytes_to_bits(self, data: bytes) -> str:
        return "".join(format(byte, "08b") for byte in data)

    def replace_lsb(self, value: int, bit: str) -> int:
        value = int(value)
        value = value & ~1
        if bit == "1":
            value |= 1
        return value

    def embed_image_lsb(self, image_path: str, data: bytes, output_path: str, bits: int = 1) -> bool:
        """LSB steganography for images."""
        try:
            img = Image.open(image_path).convert("RGB")
            pixels = np.array(img)

            binary_data = self._bytes_to_bits(self._pack_payload(data))
            if len(binary_data) > pixels.size:
                print("Carrier image too small to hold payload.")
                return False

            data_index = 0
            new_pixels = pixels.copy()

            for i in range(pixels.shape[0]):
                for j in range(pixels.shape[1]):
                    for k in range(3):
                        if data_index < len(binary_data):
                            new_pixels[i, j, k] = self.replace_lsb(new_pixels[i, j, k], binary_data[data_index])
                            data_index += 1
                        if data_index >= len(binary_data):
                            break
                    if data_index >= len(binary_data):
                        break
                if data_index >= len(binary_data):
                    break

            Image.fromarray(new_pixels.astype(np.uint8)).save(output_path)
            return True
        except Exception as e:
            print(f"Stego embed error: {e}")
            return False

    def extract_image_lsb(self, image_path: str, output_path: str) -> Optional[bytes]:
        """Extract from image LSB."""
        try:
            img = Image.open(image_path).convert("RGB")
            pixels = np.array(img)

            collected = bytearray()
            legacy_bits = ""
            expected_total = None

            for i in range(pixels.shape[0]):
                for j in range(pixels.shape[1]):
                    for k in range(3):
                        bit = str(pixels[i, j, k] & 1)
                        legacy_bits += bit
                        if len(legacy_bits) % 8 != 0:
                            continue

                        collected.append(int(legacy_bits[-8:], 2))

                        if expected_total is None and len(collected) >= self.HEADER_SIZE:
                            if bytes(collected[:4]) == self.HEADER_MAGIC:
                                payload_len = int.from_bytes(collected[4:12], "big")
                                expected_total = self.HEADER_SIZE + payload_len

                        if expected_total is not None and len(collected) >= expected_total:
                            unpacked = self._unpack_payload(bytes(collected[:expected_total]))
                            if unpacked is None:
                                return None
                            with open(output_path, "wb") as f:
                                f.write(unpacked)
                            return unpacked

                        if legacy_bits[-64:] == self.LEGACY_END_MARKER_BITS:
                            legacy_payload = bytes(
                                int(legacy_bits[idx:idx + 8], 2)
                                for idx in range(0, len(legacy_bits) - 64, 8)
                            )
                            with open(output_path, "wb") as f:
                                f.write(legacy_payload)
                            return legacy_payload

            return None
        except Exception as e:
            print(f"Stego extract error: {e}")
            return None

    def embed_audio_lsb(self, audio_path: str, data: bytes, output_path: str, bits: int = 1) -> bool:
        """LSB for audio by embedding in samples."""
        try:
            y, sr = sf.read(audio_path, dtype="int16")
            original_shape = y.shape
            flat_y = y.reshape(-1).astype(np.int32)
            binary_data = self._bytes_to_bits(self._pack_payload(data))

            if len(binary_data) > len(flat_y):
                print("Carrier audio too small to hold payload.")
                return False

            data_index = 0
            new_y = flat_y.copy()

            for i in range(len(new_y)):
                if data_index < len(binary_data):
                    new_y[i] = self.replace_lsb(new_y[i], binary_data[data_index])
                    data_index += 1
                if data_index >= len(binary_data):
                    break

            sf.write(output_path, new_y.astype(np.int16).reshape(original_shape), sr, subtype="PCM_16")
            return True
        except Exception as e:
            print(f"Stego embed audio error: {e}")
            return False

    def extract_audio_lsb(self, audio_path: str, output_path: str) -> Optional[bytes]:
        """Extract data hidden in audio LSB."""
        try:
            y, sr = sf.read(audio_path, dtype="int16")
            y_int = y.reshape(-1).astype(np.int32)

            collected = bytearray()
            legacy_bits = ""
            expected_total = None

            for val in y_int:
                bit = str(val & 1)
                legacy_bits += bit
                if len(legacy_bits) % 8 != 0:
                    continue

                collected.append(int(legacy_bits[-8:], 2))

                if expected_total is None and len(collected) >= self.HEADER_SIZE:
                    if bytes(collected[:4]) == self.HEADER_MAGIC:
                        payload_len = int.from_bytes(collected[4:12], "big")
                        expected_total = self.HEADER_SIZE + payload_len

                if expected_total is not None and len(collected) >= expected_total:
                    unpacked = self._unpack_payload(bytes(collected[:expected_total]))
                    if unpacked is None:
                        return None
                    with open(output_path, "wb") as f:
                        f.write(unpacked)
                    return unpacked

                if legacy_bits[-64:] == self.LEGACY_END_MARKER_BITS:
                    legacy_payload = bytes(
                        int(legacy_bits[idx:idx + 8], 2)
                        for idx in range(0, len(legacy_bits) - 64, 8)
                    )
                    with open(output_path, "wb") as f:
                        f.write(legacy_payload)
                    return legacy_payload

            return None
        except Exception as e:
            print(f"Stego extract audio error: {e}")
            return None

    def embed_file_append(self, file_path: str, data: bytes, output_path: str) -> bool:
        """Embed data by appending it to the end of a generic file."""
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            marker = b"<<HACK0_MARKER>>"
            combined = file_data + marker + self._pack_payload(data)

            with open(output_path, "wb") as f:
                f.write(combined)
            return True
        except Exception as e:
            print(f"Stego embed file error: {e}")
            return False

    def extract_file_append(self, file_path: str, output_path: str) -> Optional[bytes]:
        """Extract appended data from a generic file."""
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            marker = b"<<HACK0_MARKER>>"
            idx = file_data.rfind(marker)
            if idx == -1:
                return None

            extracted_data = file_data[idx + len(marker):]
            unpacked = self._unpack_payload(extracted_data)
            if unpacked is not None:
                extracted_data = unpacked

            with open(output_path, "wb") as f:
                f.write(extracted_data)
            return extracted_data
        except Exception as e:
            print(f"Stego extract file error: {e}")
            return None


stego_manager = StegoManager()
