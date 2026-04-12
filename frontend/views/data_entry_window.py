from backend.crypto import crypto_manager
from backend.blockchain import ledger
from backend.stego import stego_manager
from frontend.views.base_window import BaseWindow
from frontend.views.secure_sharing_window import SecureSharingWindow
from frontend.views.frontend_data import DATA_ENTRY_TEXT
from frontend.session import session
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit
from PyQt5.QtGui import QPixmap
from qrcode import QRCode

class DataEntryWindow(BaseWindow):
    def __init__(self):
        super().__init__("data_entry.ui")
        # Step 1: Crypto
        self.dataTextEdit.setPlainText(DATA_ENTRY_TEXT)
        self.fileButton.clicked.connect(self.select_file)
        self.encryptButton.clicked.connect(self.encrypt_data)
        
        # Inject Save Key Button dynamically
        from PyQt5.QtWidgets import QPushButton
        self.saveKeyButton = QPushButton("Save Private Key (.pem)")
        self.saveKeyButton.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold; padding: 5px;")
        self.saveKeyButton.hide()
        
        layout = self.encryptButton.parent().layout()
        if layout:
            idx = layout.indexOf(self.encryptButton)
            layout.insertWidget(idx + 1, self.saveKeyButton)
        self.saveKeyButton.clicked.connect(self.save_private_key)
        
        # Step 2: Encoding
        self.encodingCombo.addItems(["QR Code Image", "Audio Signal (Wav)", "None (Direct Embedding)"])
        self.generateButton.clicked.connect(self.generate_encoding)
        
        # Step 3: Embedding
        self.embedButton.clicked.connect(self.embed_in_carrier)
        
        # Navigation
        self.qrButton.clicked.connect(self.go_to_sharing)
        self.backButton.clicked.connect(self.go_back)

    def select_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select File or QR Code", "", "All Files (*.*);;Image/QR Codes (*.png *.jpg *.bmp)")
        if filename:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                try:
                    import cv2
                    img = cv2.imread(filename)
                    if img is not None:
                        det = cv2.QRCodeDetector()
                        val, _, _ = det.detectAndDecode(img)
                        if val:
                            reply = QMessageBox.question(self, "QR Code Detected!", 
                                                         f"I detected a QR Code in this image!\n\nExtracted Text:\n'{val[:50]}...'\n\nDo you want to extract and use this text as your data payload? (Click No to just attach the image file as normal)",
                                                         QMessageBox.Yes | QMessageBox.No)
                            if reply == QMessageBox.Yes:
                                self.dataTextEdit.setPlainText(val)
                                self.statusLabel.setText("QR Code data extracted successfully into text box.")
                                if hasattr(self, 'attached_data'):
                                    del self.attached_data
                                return
                except Exception as e:
                    print("QR reading fallback skipped:", e)
                    
            with open(filename, 'rb') as f:
                self.attached_data = f.read()
            self.statusLabel.setText(f"File attached: {os.path.basename(filename)}")
            self.dataTextEdit.setPlainText(f"[FILE ATTACHED: {os.path.basename(filename)}]")

    def encrypt_data(self):
        from frontend.session import session
        if not getattr(session, 'step_up_cache', False):
            from backend.auth import auth_manager
            code, ok = QInputDialog.getText(self, "Step-Up Authentication", "Security Check:\n\nEnter your active Authenticator Code\nOR your Account Password:")
            if not ok or not code:
                return
            if auth_manager.verify_mfa(code) or auth_manager.verify_emergency_code(code) or auth_manager.verify_password(code):
                session.step_up_cache = True
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Verification Failed", "Code expired or invalid. Action blocked.")
                return
        plaintext_text = self.dataTextEdit.toPlainText()
        if plaintext_text.startswith("[FILE ATTACHED:"):
            plaintext = getattr(self, 'attached_data', b"")
        else:
            plaintext = plaintext_text.encode('utf-8')
            
        if not plaintext:
             self.statusLabel.setText("Please enter data or attach a file.")
             return
             
        session.plaintext = plaintext
        session.aes_key = os.urandom(32)
        session.nonce, session.encrypted_data = crypto_manager.aes_gcm_encrypt(plaintext, session.aes_key)
        
        session.private_pem, session.public_pem = crypto_manager.generate_rsa_keypair()
        session.rsa_encrypted_key = crypto_manager.rsa_encrypt_aes_key(session.aes_key, session.public_pem)
        
        session.data_hash = ledger.compute_sha3_hash(plaintext)
        ledger.add_hash(session.data_hash)
        
        self.encryptedHexEdit.setText(session.encrypted_data.hex())
        self.keyHashLabel.setText(session.data_hash[:16] + '...')
        self.rsaTextEdit.setText(f"--- Public Key ---\n{session.public_pem.decode('utf-8')}\n--- Private Key ---\n{session.private_pem.decode('utf-8')}")
        self.statusLabel.setText("Data encrypted safely. Proceed to Step 2.")
        self.saveKeyButton.show()

    def save_private_key(self):
        if not getattr(session, 'private_pem', None):
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save RSA Private Key", "my_key.pem", "PEM Files (*.pem)")
        if filename:
            with open(filename, 'wb') as f:
                f.write(session.private_pem)
            QMessageBox.information(self, "Key Secured", f"Your private key was saved to:\n{filename}\n\nYou MUST use this file from the Recovery window to decrypt your message!")

    def generate_encoding(self):
        if not hasattr(session, 'encrypted_data') or not session.nonce or not hasattr(session, 'rsa_encrypted_key'):
            self.statusLabel.setText("No data to encode! Please encrypt first.")
            return

        # Concatenate: RSA_Encrypted_AES_Key (256 bytes) + Nonce (12 bytes) + Ciphertext (N bytes)
        payload_data = session.rsa_encrypted_key + session.nonce + session.encrypted_data
        enc_type = self.encodingCombo.currentText()
        
        if "QR" in enc_type:
            qr = QRCode(version=None, box_size=10, border=5)
            qr.add_data(payload_data.hex())
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            import io
            from PyQt5.QtGui import QPixmap

            byte_stream = io.BytesIO()
            qr_img.save(byte_stream, format="PNG")
            session.encoded_output_path = byte_stream.getvalue()
            session.encoding_ext = "png"
            
            qr_pixmap = QPixmap()
            qr_pixmap.loadFromData(byte_stream.getvalue())
            self.qrPreview.setPixmap(qr_pixmap.scaled(200, 200))
            self.statusLabel.setText("QR generated with encrypted nonce+data.")
        elif "Audio" in enc_type:
            from backend.encoder import encoder
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            encoder.encode_to_audio(payload_data, temp_path)
            with open(temp_path, "rb") as f:
                session.encoded_output_path = f.read()
            session.encoding_ext = "wav"
            os.remove(temp_path)
            
            self.qrPreview.setText("🎵 Audio Waveform Generated 🎵\nReady for Steganography.")
            self.statusLabel.setText("Audio signal generated from encrypted data.")
        else:
            session.encoded_output_path = payload_data
            session.encoding_ext = "bin"
            self.qrPreview.setText("Raw Binary Selected\n(No intermediate encoding applied)")
            self.statusLabel.setText("Raw payload ready.")
            
        import math
        bytes_len = len(session.encoded_output_path)
        bits_len = bytes_len * 8 + 64
        pixels_needed = bits_len // 3 + 1
        dim = int(math.sqrt(pixels_needed))
        seconds_needed = bits_len / 44100.0
        
        hint = f"\n[Required Carrier: Image > {dim}x{dim}px | Audio > {seconds_needed:.1f}s]"
        self.statusLabel.setText(self.statusLabel.text() + hint)

        self.progressBar.setValue(50)

    def embed_in_carrier(self):
        if not hasattr(session, 'encoded_output_path') or not session.encoded_output_path:
            self.statusLabel.setText("Generate encoding in Step 2 first!")
            return
            
        carrier_file, _ = QFileDialog.getOpenFileName(self, "Select carrier image/audio to embed into", "", "All Files (*.*)")
        if carrier_file:
            temp_enc = f"temp_enc.{session.encoding_ext}"
            with open(temp_enc, "wb") as f:
                f.write(session.encoded_output_path)
            
            # Write to the same directory as the chosen carrier, guaranteeing lossless format
            base_dir = os.path.dirname(carrier_file)
            base_name = os.path.splitext(os.path.basename(carrier_file))[0]
            
            if carrier_file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                 out_file = os.path.join(base_dir, "Hack0_embedded_" + base_name + ".wav")
                 success = stego_manager.embed_audio_lsb(carrier_file, open(temp_enc, 'rb').read(), out_file)
            elif carrier_file.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff')):
                 out_file = os.path.join(base_dir, "Hack0_embedded_" + base_name + ".png")
                 success = stego_manager.embed_image_lsb(carrier_file, open(temp_enc, 'rb').read(), out_file)
            else:
                 out_file = os.path.join(base_dir, "Hack0_embedded_" + os.path.basename(carrier_file))
                 success = stego_manager.embed_file_append(carrier_file, open(temp_enc, 'rb').read(), out_file)
                 
            os.remove(temp_enc)
            
            if success:
                session.final_carrier_path = os.path.abspath(out_file)
                QMessageBox.information(self, "Success", f"Data beautifully embedded in carrier - saved as:\n{out_file}")
                self.statusLabel.setText(f"Stego embedding complete!")
                self.progressBar.setValue(100)
            else:
                self.statusLabel.setText("Embedding failed. Carrier may be too small or corrupted.")
                QMessageBox.warning(self, "Embedding Error", "Embedding failed! Make sure your carrier image/audio file is large enough to hold the payload.")
                
    def go_to_sharing(self):
        if not hasattr(session, 'final_carrier_path'):
             QMessageBox.warning(self, "Warning", "Please embed the encoding into a carrier first (Step 3).")
             return
        self.navigate_to(SecureSharingWindow)

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)
