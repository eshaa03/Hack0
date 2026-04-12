import os
from backend.crypto import crypto_manager
from frontend.views.base_window import BaseWindow
from frontend.views.frontend_data import ENCRYPTION_PIPELINE

class EncryptionWindow(BaseWindow):
    def __init__(self):
        super().__init__("encryption.ui")
        self.pipelineList.addItems(ENCRYPTION_PIPELINE)
        self.startButton.clicked.connect(self.start_encryption)
        self.backButton.clicked.connect(self.go_back)

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)

    def start_encryption(self):
        # Mock advanced encryption pipeline
        self.statusLabel.setText("Running AES-GCM + RSA + SHA3 pipeline...")
        # Simulate
        self.progressBar.setValue(100)
        self.statusLabel.setText("Encryption pipeline complete. Ready for encoding.")

