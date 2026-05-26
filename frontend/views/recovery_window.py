from backend.crypto import crypto_manager  # type: ignore
from backend.stego import stego_manager  # type: ignore
from backend.blockchain import ledger  # type: ignore
from ai.ai import ai_manager  # type: ignore

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QInputDialog, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal
import os
import tempfile
import base64


class StegoExtractThread(QThread):
    finished = pyqtSignal(bytes, str)

    def __init__(self, stego_manager, carrier_file, extracted_path, parent=None):
        super().__init__(parent)
        self.stego_manager = stego_manager
        self.carrier_file = carrier_file
        self.extracted_path = extracted_path

    def run(self):
        try:
            extracted = None
            with open(self.carrier_file, "rb") as f:
                file_data = f.read()
            idx = file_data.rfind(b"<<HACK0_MARKER>>")

            if idx != -1:
                extracted = self.stego_manager.extract_file_append(self.carrier_file, self.extracted_path)
            elif self.carrier_file.lower().endswith(".wav"):
                extracted = self.stego_manager.extract_audio_lsb(self.carrier_file, self.extracted_path)
            elif self.carrier_file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                extracted = self.stego_manager.extract_image_lsb(self.carrier_file, self.extracted_path)
            else:
                extracted = self.stego_manager.extract_file_append(self.carrier_file, self.extracted_path)

            self.finished.emit(extracted or b"", "")
        except Exception as e:
            self.finished.emit(b"", str(e))


from frontend.views.base_window import BaseWindow  # type: ignore
from frontend.views.frontend_data import RECOVERY_PIPELINE  # type: ignore
from frontend.session import session  # type: ignore
from backend.encoder import encoder  # type: ignore
from typing import Any


RSA_ENCRYPTED_KEY_SIZE = 128
NONCE_SIZE = 12
MIN_PAYLOAD_SIZE = RSA_ENCRYPTED_KEY_SIZE + NONCE_SIZE


class RecoveryWindow(BaseWindow):
    PASSWORD_PAYLOAD_MAGIC = b"H0PW1"
    PASSWORD_SALT_SIZE = 16

    pipelineList: Any
    btnLoadKey: Any
    btnBrowseCarrier: Any
    processButton: Any
    backButton: Any
    statusLabel: Any
    rsaKeyStatus: Any
    carrierFileInput: Any
    rawPayloadInput: Any
    progressBar: Any
    previewText: Any

    def __init__(self):
        super().__init__("recovery.ui")
        self.setAcceptDrops(True)

        self.pipelineList.addItems(RECOVERY_PIPELINE)
        self.btnLoadKey.setText("Load or Paste Private Key")

        self.btnLoadKey.clicked.connect(self.load_private_key)
        self.btnBrowseCarrier.clicked.connect(self.browse_carrier)
        self.processButton.clicked.connect(self.start_recovery)
        self.backButton.clicked.connect(self.go_back)

        self.loaded_private_pem = None
        self.recovery_tempdir = None
        self.extracted_payload_path = None

    def decode_payload_text(self, value: str) -> bytes:
        value = value.strip()
        if value.startswith("HACK0B64:"):
            try:
                return base64.b64decode(value[len("HACK0B64:"):])
            except Exception:
                return value.encode("utf-8")
        if value.startswith("HACK0HEX:"):
            try:
                return bytes.fromhex(value[len("HACK0HEX:"):])
            except ValueError:
                return value.encode("utf-8")

        try:
            return bytes.fromhex(value)
        except ValueError:
            return value.encode("utf-8")

    def decode_payload_bytes(self, value: bytes) -> bytes:
        if value.startswith(b"HACK0B64:") or value.startswith(b"HACK0HEX:"):
            return self.decode_payload_text(value.decode("ascii"))

        try:
            text = value.decode("ascii").strip()
        except UnicodeDecodeError:
            return value

        if len(text) >= MIN_PAYLOAD_SIZE * 2 and len(text) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in text):
            try:
                return bytes.fromhex(text)
            except ValueError:
                return value
        return value

    def is_password_payload(self, payload: bytes) -> bool:
        min_size = len(self.PASSWORD_PAYLOAD_MAGIC) + self.PASSWORD_SALT_SIZE + NONCE_SIZE
        return payload.startswith(self.PASSWORD_PAYLOAD_MAGIC) and len(payload) > min_size

    def update_ui(self, message):
        self.statusLabel.setText(message)
        QApplication.processEvents()

    def highlight_pipeline_step(self, step_idx: int, progress: int):
        self.pipelineList.setCurrentRow(step_idx)
        self.progressBar.setValue(progress)

        from datetime import datetime

        item = self.pipelineList.item(step_idx)
        if item:
            text = item.text()
            if "] " in text:
                text = text.split("] ")[-1]
            item.setText(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

        QApplication.processEvents()

    def set_loaded_private_key(self, pem_bytes: bytes, source: str):
        normalized = pem_bytes.replace(b"\r\n", b"\n").strip() + b"\n"
        self.loaded_private_pem = normalized

        if hasattr(self, "rsaKeyStatus"):
            key_type = "Encrypted PEM" if b"ENCRYPTED PRIVATE KEY" in normalized else "PEM"
            self.rsaKeyStatus.setText(f"{key_type} loaded from {source}")
            self.rsaKeyStatus.setStyleSheet("color: green; font-weight: bold;")

    def paste_private_key(self):
        pem_text, ok = QInputDialog.getMultiLineText(
            self,
            "Paste RSA Private Key",
            "Paste the full private key text, including BEGIN/END lines:",
            "",
        )
        if not ok or not pem_text.strip():
            return

        pem_bytes = pem_text.encode("utf-8")
        if b"BEGIN" not in pem_bytes or b"PRIVATE KEY" not in pem_bytes:
            QMessageBox.warning(self, "Invalid Key", "That text does not look like a PEM private key.")
            return

        self.set_loaded_private_key(pem_bytes, "pasted text")

    def load_private_key(self):
        from frontend.session import session
        if not getattr(session, "step_up_cache", False):
            from backend.auth import auth_manager

            password, ok = QInputDialog.getText(self, "Step-Up Auth", "Classified Action: Enter your account password:", QLineEdit.Password)
            if not ok or not password:
                return
            if auth_manager.verify_password(password):
                session.step_up_cache = True
            else:
                QMessageBox.warning(self, "Verification Failed", "Incorrect password. Access denied.")
                return

        reply = QMessageBox.question(
            self,
            "Private Key Input",
            "How do you want to provide the private key?\n\nYes = Load .pem file\nNo = Paste PEM text",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Cancel:
            return
        if reply == QMessageBox.No:
            self.paste_private_key()
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select RSA Private Key",
            "",
            "PEM Files (*.pem);;All Files (*.*)",
        )
        if filename:
            with open(filename, "rb") as f:
                self.set_loaded_private_key(f.read(), os.path.basename(filename))

    def browse_carrier(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select carrier file (or standalone QR)",
            "",
            "All Files (*.*)",
        )
        if filename:
            self.carrierFileInput.setText(filename)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.carrierFileInput.setText(files[0])
            self.update_ui(f"Dropped carrier: {os.path.basename(files[0])}")

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow

        self.navigate_to(DashboardWindow)

    def begin_recovery_tempdir(self):
        self.cleanup_recovery_tempdir()
        self.recovery_tempdir = tempfile.TemporaryDirectory(prefix="hack0_recovery_")
        self.extracted_payload_path = os.path.join(self.recovery_tempdir.name, "extracted_payload.bin")

    def cleanup_recovery_tempdir(self):
        if self.recovery_tempdir is not None:
            self.recovery_tempdir.cleanup()
            self.recovery_tempdir = None
        self.extracted_payload_path = None

    def start_recovery(self):
        self.highlight_pipeline_step(0, 10)
        from frontend.session import session
        if not getattr(session, "step_up_cache", False):
            from backend.auth import auth_manager

            password, ok = QInputDialog.getText(self, "Step-Up Auth", "Data Extraction Security Check:\n\nEnter your account password:", QLineEdit.Password)
            if not ok or not password:
                return
            if auth_manager.verify_password(password):
                session.step_up_cache = True
            else:
                QMessageBox.warning(self, "Verification Failed", "Incorrect password. Access denied.")
                return
        carrier_file = self.carrierFileInput.text().strip()
        raw_hex = self.rawPayloadInput.toPlainText().strip()

        if not carrier_file and not raw_hex:
            QMessageBox.warning(self, "Input Required", "Please browse for a carrier file OR paste a raw payload.")
            return

        extracted = b""
        if raw_hex:
            self.update_ui("Using pasted raw payload...")
            extracted = self.decode_payload_text(raw_hex)
        else:
            if not os.path.exists(carrier_file):
                self.update_ui("Carrier file does not exist!")
                return

            self.update_ui("Extracting hidden data...")
            self.begin_recovery_tempdir()
            extracted_path = self.extracted_payload_path

            if carrier_file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                try:
                    import cv2  # type: ignore

                    img = cv2.imread(carrier_file)
                    if img is not None:
                        det = cv2.QRCodeDetector()
                        val, _, _ = det.detectAndDecode(img)
                        if val:
                            extracted = self.decode_payload_text(val)
                            self.update_ui("QR Code decoded directly from image!")
                except ImportError:
                    QMessageBox.critical(self, "Error", "OpenCV (cv2) not installed!")
                    return
                except Exception as e:
                    print("QR decode error:", e)

            if not extracted:
                self.processButton.setEnabled(False)
                self.update_ui("Extracting via Steganography... Please wait.")
                self.highlight_pipeline_step(1, 30)

                self.extract_thread = StegoExtractThread(stego_manager, carrier_file, extracted_path)
                self.extract_thread.finished.connect(lambda res, err: self.on_extract_finished(res, err, raw_hex))
                self.extract_thread.start()
                return

        self.on_extract_finished(extracted, "", raw_hex)

    def on_extract_finished(self, extracted: bytes, error: str, raw_hex: str):
        self.processButton.setEnabled(True)
        if error:
            self.update_ui(f"Extraction Error: {error}")
            self.cleanup_recovery_tempdir()
            return

        if extracted is None or len(extracted) == 0:
            self.update_ui("Extraction failed!")
            self.cleanup_recovery_tempdir()
            return

        final_payload = None
        if raw_hex:
            self.highlight_pipeline_step(1, 30)
            self.update_ui("Using raw hex payload...")
            final_payload = extracted
        else:
            if extracted.startswith(b"\x89PNG"):
                self.update_ui("Decoding intermediate QR PNG...")
                try:
                    import cv2  # type: ignore
                    import numpy as np

                    nparr = np.frombuffer(extracted, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if img is not None:
                        det = cv2.QRCodeDetector()
                        val, _, _ = det.detectAndDecode(img)
                        if val:
                            final_payload = self.decode_payload_text(val)
                            self.update_ui("QR Payload recovered.")
                except Exception as e:
                    print("CV2 error:", e)
            elif extracted.startswith(b"RIFF"):
                self.highlight_pipeline_step(1, 40)
                self.update_ui("Running AI Noise Cancellation on Audio Signal...")
                payload_path = self.extracted_payload_path or os.path.join(tempfile.gettempdir(), "hack0_recovery_payload.bin")
                denoised_y = ai_manager.reduce_noise(payload_path)

                target_decode_path = payload_path
                if denoised_y is not None:
                    import soundfile as sf

                    tempdir = self.recovery_tempdir.name if self.recovery_tempdir is not None else tempfile.gettempdir()
                    target_decode_path = os.path.join(tempdir, "extracted_data_clean.wav")
                    sf.write(target_decode_path, denoised_y, 44100, subtype="PCM_16")

                self.update_ui("Decoding WAV signal...")
                decoded_bytes = encoder.decode_from_audio(target_decode_path)
                if decoded_bytes:
                    final_payload = ai_manager.recover_errors(decoded_bytes)
                    self.update_ui("Audio payload recovered.")
            else:
                self.update_ui("Direct binary payload detected.")
                final_payload = self.decode_payload_bytes(extracted)

        if not final_payload and getattr(session, "payload_package", None) is not None:
            final_payload = session.payload_package
        elif not final_payload and getattr(session, "nonce", None) is not None and getattr(session, "encrypted_data", None) is not None:
            if getattr(session, "rsa_encrypted_key", None) is not None:
                final_payload = getattr(session, "rsa_encrypted_key") + getattr(session, "nonce") + getattr(session, "encrypted_data")
            else:
                final_payload = getattr(session, "nonce") + getattr(session, "encrypted_data")

        if not final_payload:
            self.update_ui("Failed to parse payload.")
            self.cleanup_recovery_tempdir()
            return

        assert isinstance(final_payload, bytes)
        if not self.is_password_payload(final_payload) and len(final_payload) < MIN_PAYLOAD_SIZE:
            self.update_ui("Invalid payload size!")
            self.cleanup_recovery_tempdir()
            return

        plaintext = None
        if self.is_password_payload(final_payload):
            salt_start = len(self.PASSWORD_PAYLOAD_MAGIC)
            salt = final_payload[salt_start:salt_start + self.PASSWORD_SALT_SIZE]
            nonce_start = salt_start + self.PASSWORD_SALT_SIZE
            nonce = final_payload[nonce_start:nonce_start + NONCE_SIZE]
            ciphertext = final_payload[nonce_start + NONCE_SIZE:]

            self.update_ui("Decrypting with recovery password...")
            self.highlight_pipeline_step(3, 60)
            recovery_password, ok = QInputDialog.getText(
                self,
                "Recovery Password",
                "Enter the same password you used during encryption:",
                QLineEdit.Password,
            )
            if not ok or not recovery_password:
                self.cleanup_recovery_tempdir()
                return

            self.highlight_pipeline_step(4, 75)
            plaintext = crypto_manager.decrypt_with_password(salt, nonce, ciphertext, recovery_password)
            if not plaintext:
                self.update_ui("Recovery password failed!")
                QMessageBox.critical(self, "Error", "Incorrect recovery password or damaged payload.")
                self.cleanup_recovery_tempdir()
                return
        else:
            enc_aes_key = final_payload[:RSA_ENCRYPTED_KEY_SIZE]
            nonce = final_payload[RSA_ENCRYPTED_KEY_SIZE:RSA_ENCRYPTED_KEY_SIZE + NONCE_SIZE]
            ciphertext = final_payload[RSA_ENCRYPTED_KEY_SIZE + NONCE_SIZE:]

            self.update_ui("Decrypting AES key...")
            self.highlight_pipeline_step(3, 60)

            if not self.loaded_private_pem:
                if hasattr(session, "private_pem") and session.private_pem:
                    self.loaded_private_pem = session.private_pem
                else:
                    self.update_ui("No private key loaded!")
                    QMessageBox.critical(self, "Error", "Load a valid private key first!")
                    self.cleanup_recovery_tempdir()
                    return

            try:
                pwd = ""
                if b"ENCRYPTED" in self.loaded_private_pem:
                    pwd, ok = QInputDialog.getText(
                        self,
                        "Private Key Password",
                        "Enter the password you set for this private key during encryption.\nThis is not your login/admin password unless you chose the same one:",
                        QLineEdit.Password,
                    )
                    if not ok:
                        self.cleanup_recovery_tempdir()
                        return

                recovered_aes_key = crypto_manager.decrypt_aes_key(
                    enc_aes_key, self.loaded_private_pem, pwd if pwd else None
                )
            except Exception:
                self.update_ui("Key Decryption Failed.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Could not unlock the private key or the extracted payload does not match this key.\n\n"
                    "If your password is correct, double-check that you are using the original embedded carrier file "
                    "and the matching private key from the same encryption run.",
                )
                self.cleanup_recovery_tempdir()
                return

            self.highlight_pipeline_step(4, 75)
            plaintext = crypto_manager.aes_gcm_decrypt(nonce, ciphertext, recovered_aes_key)
            if not plaintext:
                self.update_ui("AES tag verification failed!")
                self.cleanup_recovery_tempdir()
                return

        hash_input = ""
        reply = QMessageBox.question(
            self,
            "Verify Hash",
            "Do you have the generated Hash file (payload_hash.txt) to verify data integrity?\n\nClick 'Yes' to upload the file, 'No' to paste the hash directly, or 'Cancel' to skip.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )

        if reply == QMessageBox.Yes:
            hash_file, _ = QFileDialog.getOpenFileName(self, "Select Hash File", "", "Text Files (*.txt);;All Files (*.*)")
            if hash_file:
                try:
                    with open(hash_file, "r") as f:
                        hash_input = f.read().strip()
                except Exception:
                    pass
        elif reply == QMessageBox.No:
            text_input, ok = QInputDialog.getText(self, "Hash Verification", "Paste the SHA-3 hash:")
            if ok:
                hash_input = text_input.strip()

        if hash_input:
            expected_hash = hash_input.lower()
            actual_hash = ledger.compute_sha3_hash(plaintext)
            if expected_hash == actual_hash:
                QMessageBox.information(self, "Hash Match", "Authenticity Verified! Hash matches the decrypted data perfectly.")
            else:
                QMessageBox.warning(self, "Hash Mismatch", f"Integrity Failure!\nExpected: {expected_hash[:20]}...\nActual: {actual_hash[:20]}...")

        self.highlight_pipeline_step(2, 90)
        self.update_ui("Verifying with blockchain...")
        data_hash = ledger.compute_sha3_hash(plaintext)

        if not ledger.verify_hash(data_hash):
            QMessageBox.warning(self, "Warning", "Blockchain verification failed!")

        self.highlight_pipeline_step(5, 95)
        is_text = True
        text_content = ""
        try:
            text_content = plaintext.decode("utf-8")
        except UnicodeDecodeError:
            is_text = False

        if is_text:
            if hasattr(self, "previewText"):
                self.previewText.setPlainText(text_content)
        else:
            file_ext = ".bin"
            file_type = "Unknown Binary Data"

            if plaintext.startswith(b"\x89PNG\r\n\x1a\n"):
                file_ext, file_type = ".png", "PNG Image"
            elif plaintext.startswith(b"\xff\xd8\xff"):
                file_ext, file_type = ".jpg", "JPEG Image"
            elif plaintext.startswith(b"%PDF-"):
                file_ext, file_type = ".pdf", "PDF Document"
            elif plaintext.startswith(b"PK\x03\x04"):
                file_ext, file_type = ".zip", "ZIP Archive"
            elif plaintext.startswith(b"RIFF"):
                file_ext, file_type = ".wav", "WAV Audio"
            elif plaintext.startswith(b"ID3") or b"\xff\xfb" in plaintext[:4]:
                file_ext, file_type = ".mp3", "MP3 Audio"

            reply = QMessageBox.question(self, "Binary Data Detected", f"{file_type} detected.\nDo you want to download/save it?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                save_path, _ = QFileDialog.getSaveFileName(self, "Save Decrypted Data", f"decrypted_data{file_ext}", "All Files (*.*)")
                if save_path:
                    with open(save_path, "wb") as f:
                        f.write(plaintext)
                    QMessageBox.information(self, "Saved", f"Data saved to {save_path}")

            if hasattr(self, "previewText"):
                self.previewText.setPlainText(f"<{file_type} - Contents are binary>")

        self.update_ui("Recovery complete!")
        self.progressBar.setValue(100)
        self.cleanup_recovery_tempdir()
