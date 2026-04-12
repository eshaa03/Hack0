from backend.crypto import crypto_manager  # type: ignore
from backend.stego import stego_manager  # type: ignore
from backend.blockchain import ledger  # type: ignore
from ai.ai import ai_manager  # type: ignore

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QInputDialog, QLineEdit
import os
import time

from frontend.views.base_window import BaseWindow  # type: ignore
from frontend.views.frontend_data import RECOVERY_PIPELINE  # type: ignore
from frontend.session import session  # type: ignore
from backend.encoder import encoder  # type: ignore
from typing import Any

# Constants
RSA_KEY_SIZE = 256  # 2048-bit RSA
NONCE_SIZE = 12
MIN_PAYLOAD_SIZE = RSA_KEY_SIZE + NONCE_SIZE


class RecoveryWindow(BaseWindow):
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

        self.pipelineList.addItems(RECOVERY_PIPELINE)

        self.btnLoadKey.clicked.connect(self.load_private_key)
        self.btnBrowseCarrier.clicked.connect(self.browse_carrier)
        self.processButton.clicked.connect(self.start_recovery)
        self.backButton.clicked.connect(self.go_back)

        self.loaded_private_pem = None

    # ✅ Helper for UI updates
    def update_ui(self, message):
        self.statusLabel.setText(message)
        QApplication.processEvents()

    def load_private_key(self):
        from frontend.session import session
        if not getattr(session, 'step_up_cache', False):
            from backend.auth import auth_manager
            from PyQt5.QtWidgets import QInputDialog, QMessageBox
            code, ok = QInputDialog.getText(self, "Step-Up Auth", "Classified Action: Enter Offline TOTP or Online Code:")
            if not ok or not code:
                return
            if auth_manager.verify_mfa(code) or auth_manager.verify_emergency_code(code):
                session.step_up_cache = True
            else:
                QMessageBox.warning(self, "Verification Failed", "Access Denied.")
                return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select RSA Private Key",
            "",
            "PEM Files (*.pem);;All Files (*.*)"
        )
        if filename:
            with open(filename, "rb") as f:
                self.loaded_private_pem = f.read()

            if hasattr(self, 'rsaKeyStatus'):
                self.rsaKeyStatus.setText("Key Loaded Successfully!")
                self.rsaKeyStatus.setStyleSheet("color: green; font-weight: bold;")

    def browse_carrier(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select carrier file (or standalone QR)",
            "",
            "All Files (*.*)"
        )
        if filename:
            self.carrierFileInput.setText(filename)

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)

    def start_recovery(self):
        from frontend.session import session
        if not getattr(session, 'step_up_cache', False):
            from backend.auth import auth_manager
            code, ok = QInputDialog.getText(self, "Step-Up Auth", "Data Extraction Security Check:\n\nEnter your active Authenticator Code\nOR your Account Password:")
            if not ok or not code:
                return
            if auth_manager.verify_mfa(code) or auth_manager.verify_emergency_code(code) or auth_manager.verify_password(code):
                session.step_up_cache = True
            else:
                QMessageBox.warning(self, "Verification Failed", "Code expired or invalid. Access Denied.")
                return
        carrier_file = self.carrierFileInput.text().strip()
        raw_hex = self.rawPayloadInput.toPlainText().strip()

        if not carrier_file and not raw_hex:
            QMessageBox.warning(self, "Input Required",
                                "Please browse for a carrier file OR paste a raw Hex payload!")
            return

        extracted = b""

        # 🔹 RAW HEX MODE
        if raw_hex:
            self.update_ui("Using pasted raw payload...")
            try:
                extracted = bytes.fromhex(raw_hex)
            except ValueError:
                self.update_ui("Invalid hex payload!")
                QMessageBox.warning(self, "Invalid Hex",
                                    "The pasted payload must be valid hex data.")
                return

        else:
            # 🔹 FILE MODE
            if not os.path.exists(carrier_file):
                self.update_ui("Carrier file does not exist!")
                return

            self.update_ui("Extracting hidden data...")
            extracted_path = "extracted_data.bin"

            # 🔸 Try QR direct decode (Image)
            if carrier_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                try:
                    import cv2  # type: ignore
                    img = cv2.imread(carrier_file)
                    if img is not None:
                        det = cv2.QRCodeDetector()
                        val, _, _ = det.detectAndDecode(img)
                        if val:
                            try:
                                extracted = bytes.fromhex(val)
                            except ValueError:
                                extracted = val.encode('utf-8')
                            self.update_ui("QR Code decoded directly from image!")
                except ImportError:
                    QMessageBox.critical(self, "Error", "OpenCV (cv2) not installed!")
                    return
                except Exception as e:
                    print("QR decode error:", e)

            # 🔸 Normal extraction
            if not extracted:
                if carrier_file.endswith('.wav'):
                    self.update_ui("Sound/Wave Recognition Active...")
                    extracted = stego_manager.extract_audio_lsb(
                        carrier_file, extracted_path
                    )

                elif carrier_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    extracted = stego_manager.extract_image_lsb(
                        carrier_file, extracted_path
                    )

                else:
                    extracted = stego_manager.extract_file_append(
                        carrier_file, extracted_path
                    )

        # 🔴 Extraction validation
        if extracted is None or len(extracted) == 0:
            self.update_ui("Extraction failed!")
            return

        final_payload = None

        # 🔹 Detect payload type
        if raw_hex:
            self.update_ui("Using raw hex payload...")
            final_payload = extracted
        else:
            if extracted.startswith(b'\x89PNG'):
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
                            try:
                                final_payload = bytes.fromhex(val)
                            except ValueError:
                                final_payload = val.encode('utf-8')
                            self.update_ui("QR Payload recovered.")
                except Exception as e:
                    print("CV2 error:", e)

            elif extracted.startswith(b'RIFF'):
                self.update_ui("Running AI Noise Cancellation on Audio Signal...")
                denoised_y = ai_manager.reduce_noise("extracted_data.bin")
                
                target_decode_path = "extracted_data.bin"
                if denoised_y is not None:
                    import soundfile as sf
                    target_decode_path = "extracted_data_clean.wav"
                    sf.write(target_decode_path, denoised_y, 44100, subtype='PCM_16')
                    
                self.update_ui("Decoding WAV signal...")
                decoded_bytes = encoder.decode_from_audio(target_decode_path)
                if decoded_bytes:
                    final_payload = ai_manager.recover_errors(decoded_bytes)
                    self.update_ui("Audio payload recovered.")

            else:
                self.update_ui("Direct binary payload detected.")
                final_payload = extracted

        # 🔸 Fallback session (demo mode)
        if not final_payload and getattr(session, 'nonce', None) is not None and getattr(session, 'encrypted_data', None) is not None:
            print("Fallback to session payload.")
            if getattr(session, 'rsa_encrypted_key', None) is not None:
                final_payload = getattr(session, 'rsa_encrypted_key') + getattr(session, 'nonce') + getattr(session, 'encrypted_data')
            else:
                final_payload = getattr(session, 'nonce') + getattr(session, 'encrypted_data')

        if not final_payload:
            self.update_ui("Failed to parse payload.")
            return

        # 🔴 Payload size check
        assert isinstance(final_payload, bytes)
        if len(final_payload) < MIN_PAYLOAD_SIZE:
            self.update_ui("Invalid payload size!")
            return

        enc_aes_key = final_payload[:RSA_KEY_SIZE]
        nonce = final_payload[RSA_KEY_SIZE:RSA_KEY_SIZE + NONCE_SIZE]
        ciphertext = final_payload[RSA_KEY_SIZE + NONCE_SIZE:]

        self.update_ui("Decrypting AES key...")

        # 🔴 Private key check
        if not self.loaded_private_pem:
            if hasattr(session, 'private_pem') and session.private_pem:
                self.loaded_private_pem = session.private_pem
            else:
                self.update_ui("No private key loaded!")
                QMessageBox.critical(self, "Error",
                                     "Load a valid private key first!")
                return

        # 🔸 RSA decrypt
        try:
            recovered_aes_key = crypto_manager.rsa_decrypt_aes_key(
                enc_aes_key, self.loaded_private_pem
            )
        except Exception as e:
            self.update_ui("RSA Decryption Failed.")
            QMessageBox.critical(self, "Error", str(e))
            return

        # 🔸 AES decrypt
        plaintext = crypto_manager.aes_gcm_decrypt(
            nonce, ciphertext, recovered_aes_key
        )

        if not plaintext:
            self.update_ui("AES tag verification failed!")
            return

        # 🔸 Blockchain verify
        self.update_ui("Verifying with blockchain...")
        data_hash = ledger.compute_sha3_hash(plaintext)

        if not ledger.verify_hash(data_hash):
            QMessageBox.warning(self, "Warning",
                                "Blockchain verification failed!")

        # 🔸 Show output safely
        if hasattr(self, 'previewText'):
            self.previewText.setPlainText(
                plaintext.decode('utf-8', errors='ignore')
            )

        self.update_ui("Recovery complete!")
        self.progressBar.setValue(100)