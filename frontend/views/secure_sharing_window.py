from PyQt5.QtWidgets import QMessageBox
from frontend.views.base_window import BaseWindow
import os

class SecureSharingWindow(BaseWindow):
    def __init__(self):
        super().__init__("secure_sharing.ui")
        from PyQt5.QtWidgets import QStyle
        
        from PyQt5.QtGui import QIcon, QPainter
        from PyQt5.QtCore import Qt
        
        def get_text_color_icon(standard_icon):
            pixmap = self.style().standardIcon(standard_icon).pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), Qt.white)
            painter.end()
            return QIcon(pixmap)
            
        self.exportButton.setText("Save Carrier Package")
        self.exportButton.setIcon(get_text_color_icon(QStyle.SP_DialogSaveButton))
        self.exportButton.clicked.connect(self.export_carrier)
        
        self.backButton.setIcon(get_text_color_icon(QStyle.SP_ArrowBack))
        self.backButton.clicked.connect(self.go_back)
        self.statusLabel.setText("Workflow Complete. Ready to save or share the embedded carrier.")
        self.cloudShare.hide()
        self.update_handoff_summary()
        self.localExport.toggled.connect(self.update_route_description)
        self.emailShare.toggled.connect(self.update_route_description)
        self.qrShare.toggled.connect(self.update_route_description)
        self.update_route_description()

    def write_recovery_note(self, target_dir: str) -> str:
        from frontend.session import session

        note_path = os.path.join(target_dir, "recovery_notes.txt")
        lines = [
            "Hack0 Recovery Package",
            "",
            f"Carrier file: {os.path.basename(getattr(session, 'final_carrier_path', ''))}",
            f"Payload hash: {getattr(session, 'data_hash', 'not saved')}",
        ]
        if getattr(session, 'encryption_mode', '') == 'password':
            lines.extend([
                "",
                "Recovery method:",
                "- Open the carrier in Hack0 Recovery",
                "- Enter the same recovery password used during encryption",
                "- No private key file is required for this package",
            ])
        else:
            lines.extend([
                "",
                "Recovery method:",
                "- Open the carrier in Hack0 Recovery",
                "- Load the matching private key file",
                "- Enter the private-key password if prompted",
            ])

        with open(note_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return note_path

    def update_handoff_summary(self):
        from frontend.session import session
        carrier_path = getattr(session, 'final_carrier_path', '')
        if carrier_path:
            carrier_name = os.path.basename(carrier_path)
            self.carrierStateLabel.setText(f"Carrier: {carrier_name}")
        else:
            self.carrierStateLabel.setText("Carrier: no embedded file is ready yet")

        if getattr(session, 'private_pem', None):
            self.keyStateLabel.setText("Key: use the private key file you saved during encryption")
        else:
            self.keyStateLabel.setText("Key: save the private key from the encryption screen before sharing")

        if getattr(session, 'data_hash', None):
            self.integrityStateLabel.setText(f"Integrity: payload hash {session.data_hash[:16]}... is ready")
        else:
            self.integrityStateLabel.setText("Integrity: keep the saved payload hash for recovery verification")

    def update_route_description(self):
        if self.localExport.isChecked():
            text = "Choose a folder, then save the embedded carrier there for handoff."
        elif self.emailShare.isChecked():
            text = "Sends the carrier package as an email attachment using the configured SMTP account."
        elif self.qrShare.isChecked():
            text = "Starts a temporary LAN download link and displays a QR code for a nearby device."
        else:
            text = "Choose how the protected carrier should leave this workstation."
        self.routeDescriptionLabel.setText(text)

    def export_carrier(self):
        from frontend.session import session
        if not hasattr(session, 'final_carrier_path') or not session.final_carrier_path:
             QMessageBox.warning(self, "Warning", "No embedded carrier found to export.")
             return
             
        import os
        import platform
        import subprocess
        import shutil
        from PyQt5.QtWidgets import QFileDialog, QInputDialog

        base_dir = os.path.dirname(session.final_carrier_path)
        if self.localExport.isChecked():
            from PyQt5.QtWidgets import QApplication
            target_dir = QFileDialog.getExistingDirectory(
                self,
                "Choose Folder to Save Embedded Carrier",
                base_dir
            )
            if not target_dir:
                self.statusLabel.setText("Export cancelled. Choose a folder to save the carrier.")
                return

            carrier_name = os.path.basename(session.final_carrier_path)
            target_carrier = os.path.join(target_dir, carrier_name)
            if os.path.abspath(target_carrier) != os.path.abspath(session.final_carrier_path):
                shutil.copy2(session.final_carrier_path, target_carrier)
            self.write_recovery_note(target_dir)

            files_to_share = [target_carrier]
            clipboard = QApplication.clipboard()
            clipboard.setText(f"file://{target_carrier}")

            if platform.system() == "Windows":
                os.startfile(target_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", target_dir])
            else:
                subprocess.Popen(["xdg-open", target_dir])

            recovery_note = "Use the private key file saved during encryption for recovery."
            QMessageBox.information(self, "Share Folder Ready", f"Embedded carrier saved and folder opened:\n{target_dir}\n\n{recovery_note}")
            self.go_back()

        elif self.emailShare.isChecked():
            files_to_share = [session.final_carrier_path]
            email, ok = QInputDialog.getText(self, "Seamless Email Share", "Enter Recipient Email Address:")
            if ok and email:
                 self.statusLabel.setText("Seamlessly sending encrypted carrier via SMTP...")
                 from backend.network_utils import send_carrier_email
                 from PyQt5.QtWidgets import QApplication
                 QApplication.processEvents()
                 
                 success = send_carrier_email(email, files_to_share)
                 if success:
                     QMessageBox.information(self, "Email Sent", f"Carrier correctly sent to {email} seamlessly in the background!")
                     self.go_back()
                 else:
                     QMessageBox.warning(
                         self,
                         "Email Failed",
                         "Failed to send email. Use 'Local Export - USB / Offline Storage' for the most reliable handoff."
                     )

        elif self.qrShare.isChecked():
            files_to_share = [session.final_carrier_path]
            self.start_lan_server(files_to_share)

    def start_lan_server(self, files_to_share):
        import socket
        import tempfile
        import shutil
        import os
        
        # Create secure isolated staging directory
        stage_dir = tempfile.mkdtemp(prefix="hack0_qr_share_")
        self.active_stage_dir = stage_dir
        
        for fpath in files_to_share:
            if os.path.exists(fpath):
                shutil.copy(fpath, stage_dir)
                
        def get_local_ip():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                IP = s.getsockname()[0]
            except Exception:
                IP = '127.0.0.1'
            finally:
                s.close()
            return IP
            
        ip = get_local_ip()
        port = 8000
        url = f"http://{ip}:{port}/"
        
        import http.server
        import socketserver
        import threading
        
        Handler = http.server.SimpleHTTPRequestHandler
        from functools import partial
        handler_class = partial(Handler, directory=stage_dir)
        
        try:
            self.httpd = socketserver.TCPServer(("", port), handler_class)
        except OSError:
            port = 8080
            url = f"http://{ip}:{port}/"
            self.httpd = socketserver.TCPServer(("", port), handler_class)
            
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()
        
        import qrcode
        import io
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PyQt5.QtCore import Qt
        
        qr = qrcode.QRCode(version=None, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        byte_stream = io.BytesIO()
        img.save(byte_stream, format="PNG")
        
        qr_pixmap = QPixmap()
        qr_pixmap.loadFromData(byte_stream.getvalue())
        
        dialog = QDialog(self)
        dialog.setWindowTitle("QR LAN Transfer")
        layout = QVBoxLayout()
        
        lbl = QLabel()
        lbl.setPixmap(qr_pixmap.scaled(300, 300))
        layout.addWidget(lbl)
        
        txt = QLabel(f"Scan on your LAN device to download carrier:\n{url}")
        txt.setAlignment(Qt.AlignCenter)
        layout.addWidget(txt)
        
        btn = QPushButton("Close & Stop Server")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
        self.httpd.shutdown()
        self.httpd.server_close()
        try:
             import shutil
             shutil.rmtree(self.active_stage_dir)
        except Exception:
             pass
        self.go_back()

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)
