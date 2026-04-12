import os

class DataProcessor:
    def __init__(self):
        pass

    def text_to_binary(self, text: str) -> bytes:
        """Convert string text to a binary byte stream."""
        return text.encode('utf-8')

    def file_to_binary(self, file_path: str) -> bytes:
        """Read a file and convert it to a binary byte stream."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'rb') as f:
            return f.read()

    def binary_to_text(self, data: bytes) -> str:
        """Convert binary byte stream back to text."""
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return ""

    def save_binary_to_file(self, data: bytes, file_path: str):
        """Save a binary byte stream to a file."""
        with open(file_path, 'wb') as f:
            f.write(data)

data_processor = DataProcessor()
