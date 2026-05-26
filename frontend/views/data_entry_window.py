from backend.crypto import crypto_manager
from backend.blockchain import ledger
from backend.stego import stego_manager
from frontend.views.base_window import BaseWindow
from frontend.views.secure_sharing_window import SecureSharingWindow
from frontend.views.frontend_data import DATA_ENTRY_TEXT
from frontend.session import session
import os
import tempfile
import base64
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QThread, pyqtSignal
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_M

class StegoEmbedThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, stego_manager, carrier_file, temp_enc, out_file, default_ext, parent=None):
        super().__init__(parent)
        self.stego_manager = stego_manager
        self.carrier_file = carrier_file
        self.temp_enc = temp_enc
        self.out_file = out_file
        self.default_ext = default_ext
        
    def run(self):
        try:
            temp_data = open(self.temp_enc, 'rb').read()
            if self.default_ext == ".wav":
                success = self.stego_manager.embed_audio_lsb(self.carrier_file, temp_data, self.out_file)
            elif self.default_ext == ".png":
                success = self.stego_manager.embed_image_lsb(self.carrier_file, temp_data, self.out_file)
            else:
                success = self.stego_manager.embed_file_append(self.carrier_file, temp_data, self.out_file)
            self.finished.emit(success, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class DataEntryWindow(BaseWindow):
    PASSWORD_PAYLOAD_MAGIC = b"H0PW1"

    def __init__(self):
        super().__init__("data_entry.ui")
        self.setAcceptDrops(True)
        # Step 1: Crypto
        from datetime import datetime
        self.dataTextEdit.setPlainText(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] System initialized. Awaiting secure data entry...\n")
        from PyQt5.QtWidgets import QPushButton, QStyle
        from PyQt5.QtGui import QIcon, QPainter
        from PyQt5.QtCore import Qt
        
        def get_text_color_icon(standard_icon):
            pixmap = self.style().standardIcon(standard_icon).pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), Qt.white)
            painter.end()
            return QIcon(pixmap)

        self.fileButton.setIcon(get_text_color_icon(QStyle.SP_FileIcon))
        self.fileButton.clicked.connect(self.select_file)
        
        self.encryptButton.setIcon(get_text_color_icon(QStyle.SP_CommandLink))
        self.encryptButton.clicked.connect(self.encrypt_data)
        
        # Inject Save Key Button dynamically
        self.saveKeyButton = QPushButton("Save Private Key (.pem)")
        self.saveKeyButton.setIcon(get_text_color_icon(QStyle.SP_DialogSaveButton))
        self.saveKeyButton.hide()
        
        layout = self.encryptButton.parent().layout()
        if layout:
            idx = layout.indexOf(self.encryptButton)
            layout.insertWidget(idx + 1, self.saveKeyButton)
            
        self.saveKeyButton.clicked.connect(self.save_private_key)

        self.saveHashButton = QPushButton("Save Payload Hash (.txt)")
        self.saveHashButton.setIcon(get_text_color_icon(QStyle.SP_DialogSaveButton))
        self.saveHashButton.hide()
        if layout:
            idx2 = layout.indexOf(self.saveKeyButton)
            layout.insertWidget(idx2 + 1, self.saveHashButton)
        self.saveHashButton.clicked.connect(self.save_hash)
        
        # Step 2: Encoding
        self.encodingCombo.addItems(["QR Code Image", "Audio Signal (Wav)", "Base64 String", "Hexadecimal String", "None (Direct Embedding)"])
        self.encodingCombo.setCurrentText("None (Direct Embedding)")
        self.generateButton.setIcon(get_text_color_icon(QStyle.SP_BrowserReload))
        self.generateButton.clicked.connect(self.generate_encoding)
        
        # Step 3: Embedding
        self.embedButton.setIcon(get_text_color_icon(QStyle.SP_DriveCDIcon))
        self.embedButton.clicked.connect(self.embed_in_carrier)
        
        # Navigation
        self.qrButton.setIcon(get_text_color_icon(QStyle.SP_DialogApplyButton))
        self.qrButton.clicked.connect(self.go_to_sharing)
        
        self.backButton.setIcon(get_text_color_icon(QStyle.SP_ArrowBack))
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
            password, ok = QInputDialog.getText(self, "Step-Up Authentication", "Security Check:\n\nEnter your account password:", QLineEdit.Password)
            if not ok or not password:
                return
            if auth_manager.verify_password(password):
                session.step_up_cache = True
            else:
                QMessageBox.warning(self, "Verification Failed", "Incorrect password. Action blocked.")
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

        session.private_pem, session.public_pem = crypto_manager.generate_keypair()
        session.rsa_encrypted_key = crypto_manager.encrypt_aes_key(session.aes_key, session.public_pem)
        session.encryption_mode = "rsa"
        session.payload_package = session.rsa_encrypted_key + session.nonce + session.encrypted_data
        
        session.data_hash = ledger.compute_sha3_hash(plaintext)
        ledger.add_hash(session.data_hash)
        
        self.encryptedHexEdit.setText(session.encrypted_data.hex())
        self.keyHashLabel.setText(session.data_hash[:16] + '...')
        self.rsaTextEdit.setText(f"--- Public Key ---\n{session.public_pem.decode('utf-8')}\n--- Private Key ---\n{session.private_pem.decode('utf-8')}")
        self.statusLabel.setText("Data encrypted safely. Proceed to Step 2.")
        self.saveKeyButton.show()
        self.saveHashButton.show()

    def save_private_key(self):
        from frontend.session import session
        if not getattr(session, 'private_pem', None):
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save RSA Private Key", "my_key.pem", "PEM Files (*.pem)")
        if filename:
            with open(filename, 'wb') as f:
                f.write(session.private_pem)
            QMessageBox.information(self, "Key Secured", f"Your private key was saved to:\n{filename}\n\nLoad this .pem file in the Recovery window to decrypt your message.")

    def save_hash(self):
        from frontend.session import session
        if not getattr(session, 'data_hash', None):
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Payload Hash", "payload_hash.txt", "Text Files (*.txt)")
        if filename:
            with open(filename, 'w') as f:
                f.write(session.data_hash)
            QMessageBox.information(self, "Hash Saved", "Keep this hash safe to verify payload integrity during recovery!")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            filename = files[0]
            with open(filename, 'rb') as f:
                self.attached_data = f.read()
            self.statusLabel.setText(f"Dropped file attached: {os.path.basename(filename)}")
            self.dataTextEdit.setPlainText(f"[FILE ATTACHED: {os.path.basename(filename)}]")

    def generate_encoding(self):
        if not getattr(session, 'payload_package', None):
            self.statusLabel.setText("No data to encode! Please encrypt first.")
            return

        payload_data = session.payload_package
        enc_type = self.encodingCombo.currentText()
        
        if "QR" in enc_type:
            try:
                qr_payload = "HACK0B64:" + base64.b64encode(payload_data).decode("ascii")
                qr = QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=10, border=5)
                qr.add_data(qr_payload)
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
                self.qrPreview.clear()
                self.qrPreview.setPixmap(qr_pixmap.scaled(200, 200))
                self.statusLabel.setText("QR generated with encrypted nonce+data.")
            except Exception as e:
                err_name = e.__class__.__name__.lower()
                err_text = str(e).lower()
                if (
                    "overflow" in err_name
                    or "too large" in err_text
                    or "too long" in err_text
                    or "invalid version" in err_text
                    or "expected 1 to 40" in err_text
                ):
                    QMessageBox.warning(
                        self,
                        "Payload Too Large",
                        "This encrypted payload is too large for a single QR code.\n\n"
                        "Use Base64, Hexadecimal, or None (Direct Embedding) for larger payloads."
                    )
                    session.encoded_output_path = None
                    session.encoding_ext = None
                    self.qrPreview.clear()
                    self.qrPreview.setText("QR capacity exceeded\nUse Base64, Hexadecimal, or Direct Embedding.")
                    self.statusLabel.setText("QR Error: payload exceeds single-QR capacity. Choose another format.")
                else:
                    session.encoded_output_path = None
                    session.encoding_ext = None
                    QMessageBox.warning(self, "Encoding Error", f"Failed to generate QR:\n{str(e)}")
                return

        elif "Audio" in enc_type:
            try:
                if len(payload_data) > 500000:
                    QMessageBox.warning(self, "Payload Too Large", "Payload size may crash audio wave generation. Please use 'None (Direct Embedding)'.")
                    session.encoded_output_path = None
                    session.encoding_ext = None
                    return
                # Apply Forward Error Correction
                from ai.ai import ai_manager
                fec_payload = ai_manager.apply_fec(payload_data)
                
                from backend.encoder import encoder
                import tempfile
                fd, temp_path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                encoder.encode_to_audio(fec_payload, temp_path)
                with open(temp_path, "rb") as f:
                    session.encoded_output_path = f.read()
                session.encoding_ext = "wav"
                os.remove(temp_path)
                
                self.qrPreview.clear()
                self.qrPreview.setText("Audio waveform generated\nReady for steganography.")
                self.statusLabel.setText("Audio signal generated from encrypted data.")
            except Exception as e:
                session.encoded_output_path = None
                session.encoding_ext = None
                QMessageBox.warning(self, "Encoding Error", f"Audio encoding failed:\n{e}")
                return
        elif "Base64" in enc_type:
            b64_data = b"HACK0B64:" + base64.b64encode(payload_data)
            session.encoded_output_path = b64_data
            session.encoding_ext = "txt"
            self.qrPreview.clear()
            self.qrPreview.setText("Base64 String Generated\nReady for Steganography.")
            self.statusLabel.setText("Base64 encoding applied.")

        elif "Hexadecimal" in enc_type:
            hex_data = b"HACK0HEX:" + payload_data.hex().encode('ascii')
            session.encoded_output_path = hex_data
            session.encoding_ext = "txt"
            self.qrPreview.clear()
            self.qrPreview.setText("Hexadecimal String Generated\nReady for Steganography.")
            self.statusLabel.setText("Hexadecimal encoding applied.")

        else:
            session.encoded_output_path = payload_data
            session.encoding_ext = "bin"
            self.qrPreview.clear()
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
        if not carrier_file:
            return

        base_dir = os.path.dirname(carrier_file)
        base_name = os.path.splitext(os.path.basename(carrier_file))[0]

        if carrier_file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
            default_ext = ".wav"
        elif carrier_file.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.tiff')):
            default_ext = ".png"
        else:
            _, default_ext = os.path.splitext(carrier_file)

        suggested_path = self.next_available_path(base_dir, f"Hack0_embedded_{base_name}", default_ext)
        filter_label = f"{default_ext.upper().lstrip('.')} Files (*{default_ext});;All Files (*.*)" if default_ext else "All Files (*.*)"
        out_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Embedded Carrier As",
            suggested_path,
            filter_label
        )
        if not out_file:
            self.statusLabel.setText("Embedding cancelled. Choose a save location to continue.")
            return
        if default_ext and not os.path.splitext(out_file)[1]:
            out_file += default_ext

        embed_bytes = session.encoded_output_path
        temp_suffix = f".{session.encoding_ext}"
        if default_ext not in (".wav", ".png"):
            embed_bytes = session.payload_package
            temp_suffix = ".bin"

        fd, temp_enc = tempfile.mkstemp(suffix=temp_suffix)
        os.close(fd)
        with open(temp_enc, "wb") as f:
            f.write(embed_bytes)

        self.statusLabel.setText("Embedding in progress... Please wait.")
        self.embedButton.setEnabled(False)

        self.stego_thread = StegoEmbedThread(stego_manager, carrier_file, temp_enc, out_file, default_ext)
        self.stego_thread.finished.connect(lambda s, e: self.on_embed_finished(s, e, out_file, temp_enc))
        self.stego_thread.start()

    def next_available_path(self, directory, stem, extension):
        candidate = os.path.join(directory, stem + extension)
        if not os.path.exists(candidate):
            return candidate

        index = 2
        while True:
            candidate = os.path.join(directory, f"{stem}_{index}{extension}")
            if not os.path.exists(candidate):
                return candidate
            index += 1

    def on_embed_finished(self, success, err, out_file, temp_enc):
        import os
        from frontend.session import session
        
        self.embedButton.setEnabled(True)
        if os.path.exists(temp_enc):
            os.remove(temp_enc)
            
        if success:
            session.final_carrier_path = os.path.abspath(out_file)
            QMessageBox.information(self, "Success", f"Data embedded in carrier:\n{out_file}\n\nUse the private key file saved during encryption for recovery.")
            self.statusLabel.setText(f"Stego embedding complete: {os.path.basename(out_file)}")
            self.progressBar.setValue(100)
        else:
            self.statusLabel.setText("Embedding failed. Carrier may be too small or corrupted.")
            QMessageBox.warning(self, "Embedding Error", f"Embedding failed! {err}\nMake sure your carrier image/audio file is large enough to hold the payload.")
                
    def go_to_sharing(self):
        if not hasattr(session, 'final_carrier_path'):
             QMessageBox.warning(self, "Warning", "Please embed the encoding into a carrier first (Step 3).")
             return
        self.navigate_to(SecureSharingWindow)

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)
