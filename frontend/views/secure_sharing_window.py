from PyQt5.QtWidgets import QFileDialog, QMessageBox
from frontend.views.base_window import BaseWindow
from frontend.views.frontend_data import SHARING_OPTIONS

class SecureSharingWindow(BaseWindow):
    def __init__(self):
        super().__init__("secure_sharing.ui")
        self.exportButton.setText("Export Carrier & Save Keys")
        self.exportButton.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #28a745; color: white; padding: 5px;")
        self.exportButton.clicked.connect(self.export_carrier)
        self.backButton.clicked.connect(self.go_back)
        self.statusLabel.setText("Workflow Complete. Ready to share carrier and keys.")

    def export_carrier(self):
        from frontend.session import session
        if self.localExport.isChecked():
            if hasattr(session, 'final_carrier_path') and session.final_carrier_path:
                ext = session.final_carrier_path.split('.')[-1]
                filename, _ = QFileDialog.getSaveFileName(self, "Save Carrier", f"secure_carrier.{ext}")
                if filename:
                    import shutil
                    import os
                    shutil.copy2(session.final_carrier_path, filename)
                    
                    # Store RSA keys
                    base_dir = os.path.dirname(filename)
                    base_name = os.path.splitext(os.path.basename(filename))[0]
                    
                    if hasattr(session, 'private_pem') and session.private_pem:
                        priv_path = os.path.join(base_dir, f"{base_name}_PRIVATE_KEY.pem")
                        with open(priv_path, "wb") as f:
                             f.write(session.private_pem)
                             
                    if hasattr(session, 'public_pem') and session.public_pem:
                        pub_path = os.path.join(base_dir, f"{base_name}_PUBLIC_KEY.pem")
                        with open(pub_path, "wb") as f:
                             f.write(session.public_pem)
                    
                    # Copy to clipboard
                    from PyQt5.QtWidgets import QApplication
                    clipboard = QApplication.clipboard()
                    clipboard.setText(f"file://{filename}")
                    
                    QMessageBox.information(self, "Export Success!", f"Carrier & Keys successfully saved!\nFolder: {base_dir}\nCarrier: {base_name}\n\nIMPORTANT: securely share the _PRIVATE_KEY.pem file securely with your recipient so they can decrypt!")
            else:
                 QMessageBox.warning(self, "Warning", "No embedded carrier found in session.")
        else:
            QMessageBox.information(self, "External Sharing", "Carrier prepared for selected sharing method.")
        
        # Return to dashboard as the final step
        self.go_back()

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)
