from PyQt5.QtWidgets import QMessageBox, QPushButton
from PyQt5.QtCore import QTimer
import pyotp

from frontend.views.base_window import BaseWindow
from frontend.views.biometric_window import BiometricWindow
from frontend.views.dashboard_window import DashboardWindow
from backend.auth import auth_manager
from frontend.session import session
from backend.network_utils import is_online, send_real_email, send_real_sms

class MFAWindow(BaseWindow):
    def __init__(self):
        super().__init__("mfa.ui")
        self.verifyButton.clicked.connect(self.verify_code)
        
        # Inject Back/Cancel Button
        self.cancelButton = QPushButton("Cancel Authentication (Back)")
        self.cancelButton.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-weight: bold;")
        layout = self.verifyButton.parent().layout()
        if layout:
            layout.addWidget(self.cancelButton)
        self.cancelButton.clicked.connect(self.cancel_auth)
        
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Real-Time MFA")
            
        self.otp_timer = QTimer(self)
        self.otp_timer.timeout.connect(self.update_timer)
        self.otp_timer.start(1000)
            
        QTimer.singleShot(100, self.dispatch_otp)

    def update_timer(self):
        import time
        remaining = 30 - (int(time.time()) % 30)
        if hasattr(self, 'statusLabel'):
            current_text = self.statusLabel.text()
            if any(word in current_text for word in ["dispatched", "OTP", "Awaiting"]):
                new_text = current_text.rsplit(' (', 1)[0] if ' (' in current_text else current_text

    def dispatch_otp(self):
        user_data = auth_manager.get_current_user_data()
        if not user_data or "totp_secret" not in user_data:
            self.statusLabel.setText("MFA Setup missing for user.")
            return

        totp = pyotp.TOTP(user_data["totp_secret"]).now()
        phone = user_data.get("phone_number")
        email = user_data.get("email")
        if is_online():
            # Email only
            email_sent = send_real_email(email, totp)
            if email_sent:
                self.statusLabel.setText("OTP dispatched by Email.")
            else:
                self.statusLabel.setText("Email failed. Use Authenticator app.")
                QMessageBox.warning(
                    self,
                    "Email Failed",
                    "\nLocal TOTP: " + totp
                )
        else:
            QMessageBox.warning(self, "Offline Mode", "Offline. Use Authenticator TOTP.")
            self.statusLabel.setText("Awaiting authenticator app code...")

    def verify_code(self) -> None:
        code = self.otpInput.text().strip()
        if auth_manager.verify_mfa(code) or auth_manager.verify_emergency_code(code):
            session.is_mfa_verified = True
            
            user_data = auth_manager.get_current_user_data()
            if user_data and user_data.get("has_biometric", False):
                self.navigate_to(BiometricWindow)
            else:
                self.navigate_to(DashboardWindow)
        else:
            self.statusLabel.setText("Invalid OTP.")

    def cancel_auth(self):
        from frontend.session import session
        from frontend.views.login_window import LoginWindow
        session.user_id = None
        session.role = None
        self.navigate_to(LoginWindow)
