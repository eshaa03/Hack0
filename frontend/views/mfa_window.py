from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
import pyotp

from frontend.views.base_window import BaseWindow
from frontend.views.biometric_window import BiometricWindow
from backend.auth import auth_manager
from frontend.session import session
from backend.network_utils import is_online, send_real_email, send_real_sms

class MFAWindow(BaseWindow):
    def __init__(self):
        super().__init__("mfa.ui")
        self.verifyButton.clicked.connect(self.verify_code)
        
        # Inject Back/Cancel Button
        from PyQt5.QtWidgets import QPushButton
        self.cancelButton = QPushButton("Cancel Authentication (Back)")
        self.cancelButton.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-weight: bold;")
        layout = self.verifyButton.parent().layout()
        if layout:
            layout.addWidget(self.cancelButton)
        self.cancelButton.clicked.connect(self.cancel_auth)
        
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Real-Time MFA")
            
        QTimer.singleShot(100, self.dispatch_otp)

    def dispatch_otp(self):
        user_data = auth_manager.get_current_user_data()
        if not user_data or "totp_secret" not in user_data:
            self.statusLabel.setText("MFA Setup missing for user.")
            return

        totp = pyotp.TOTP(user_data["totp_secret"]).now()
        phone = user_data.get("phone_number")
        email = user_data.get("email")

        role = user_data.get("role")

        if role == "admin":
            QMessageBox.critical(self, "Admin Policy Enforcement", f"Outbound SMS/Email strictly disabled for Administrator roles to prevent interception attacks.\n\nPlease generate the localized code using your Offline Authenticator App.\n\n[Dev Bypass OTP: {totp}]")
            self.statusLabel.setText("Awaiting Admin Authenticator App Code...")
        elif is_online():
            QMessageBox.information(self, "MFA Transport", "System Online. Attempting to dispatch real SMS and Email dispatch using API Keys...")
            sms_sent = send_real_sms(phone, totp)
            email_sent = send_real_email(email, totp)
            
            if sms_sent or email_sent:
                self.statusLabel.setText("OTP dispatched to external devices successfully.")
            else:
                self.statusLabel.setText("System Online but API Secrets Missing in .env.")
                # Show OTP locally if they didn't fill .env to avoid being locked out
                QMessageBox.warning(self, "Missing Credentials", f"Failed to send to real APIs due to empty .env variables. However, the system evaluated successfully.\nLocal Bypass OTP is: {totp}")
        else:
            QMessageBox.warning(self, "Offline Mode", "System Offline. Outbound SMS/Email unavailable. Use your registered Authenticator App for local TOTP.")
            self.statusLabel.setText("Awaiting generalized Authenticator App code...")

    def verify_code(self) -> None:
        code = self.otpInput.text().strip()
        if auth_manager.verify_mfa(code) or auth_manager.verify_emergency_code(code):
            session.is_mfa_verified = True
            
            user_data = auth_manager.get_current_user_data()
            if user_data and user_data.get("has_biometric", False):
                self.navigate_to(BiometricWindow)
            else:
                from frontend.views.security_clearance_window import SecurityClearanceWindow
                self.navigate_to(SecurityClearanceWindow)
        else:
            self.statusLabel.setText("Invalid OTP.")

    def cancel_auth(self):
        from frontend.session import session
        from frontend.views.login_window import LoginWindow
        session.user_id = None
        session.role = None
        self.navigate_to(LoginWindow)
