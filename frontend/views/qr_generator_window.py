from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap
from qrcode import QRCode
import os

from frontend.views.base_window import BaseWindow

class QRGeneratorWindow(BaseWindow):
    def __init__(self):
        super().__init__("qr_generator.ui")
        self.current_qr_img = None
        from PyQt5.QtWidgets import QPushButton, QStyle

        from PyQt5.QtGui import QIcon, QPixmap, QPainter
        from PyQt5.QtCore import Qt
        
        def get_text_color_icon(standard_icon):
            pixmap = self.style().standardIcon(standard_icon).pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), Qt.white)
            painter.end()
            return QIcon(pixmap)

        self.generateButton.clicked.connect(self.generate_standalone_qr)
        self.generateButton.setIcon(get_text_color_icon(QStyle.SP_FileDialogDetailedView))

        self.saveButton.clicked.connect(self.save_qr_image)
        self.saveButton.setIcon(get_text_color_icon(QStyle.SP_DialogSaveButton))
        self.saveButton.setStyleSheet("background-color: #28a745; color: white;")

        self.backButton.clicked.connect(self.go_back)
        self.backButton.setIcon(get_text_color_icon(QStyle.SP_ArrowBack))

        self.fileButton = QPushButton("Attach File Instead")
        self.fileButton.setIcon(get_text_color_icon(QStyle.SP_FileIcon))
        layout = self.generateButton.parent().layout()
        if layout:
            idx = layout.indexOf(self.generateButton)
            layout.insertWidget(idx, self.fileButton)
        self.fileButton.clicked.connect(self.select_file)
        self.attached_bytes = None

    def select_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select File to Embed", "", "All Files (*.*)")
        if filename:
            with open(filename, 'rb') as f:
                self.attached_bytes = f.read()
            self.qrTextInput.setPlainText(f"[FILE ATTACHED: {os.path.basename(filename)} - {len(self.attached_bytes)} bytes]")

    def generate_standalone_qr(self):
        text_data = self.qrTextInput.toPlainText()
        if not text_data.strip():
            QMessageBox.warning(self, "Warning", "Please enter some text or URL first.")
            return

        import base64
        if text_data.startswith("[FILE ATTACHED:") and hasattr(self, 'attached_bytes'):
            if len(self.attached_bytes) > 2000:
                QMessageBox.warning(self, "Size Limit Exceeded", f"This file is {len(self.attached_bytes)} bytes. QR Codes max out at around ~2KB (2000 bytes).")
                return
            payload = base64.b64encode(self.attached_bytes).decode('utf-8')
        else:
            payload = text_data
            
        if len(payload) > 2900:
            QMessageBox.warning(self, "Size Limit Exceeded", "Data is too large to encode into a QR block.")
            return

        qr = QRCode(version=None, box_size=10, border=5)
        qr.add_data(payload)
        qr.make(fit=True)
        self.current_qr_img = qr.make_image(fill_color="black", back_color="white")
        
        from io import BytesIO
        from PyQt5.QtGui import QPixmap
        buffer = BytesIO()
        self.current_qr_img.save(buffer, format="PNG")
        
        qr_pixmap = QPixmap()
        qr_pixmap.loadFromData(buffer.getvalue())
        self.qrPreview.setPixmap(qr_pixmap.scaled(300, 300))

    def save_qr_image(self):
        if not self.current_qr_img:
            QMessageBox.warning(self, "Warning", "Generate a QR code first!")
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Save QR Code", "standalone_qr.png", "PNG Images (*.png);;All Files (*)")
        if filename:
            self.current_qr_img.save(filename, format="PNG")
            QMessageBox.information(self, "Success", f"QR Code successfully saved to:\n{filename}")

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)
