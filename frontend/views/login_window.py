from PyQt5.QtWidgets import QLineEdit

from PyQt5.QtWidgets import QLineEdit, QMessageBox

from frontend.views.base_window import BaseWindow
from frontend.views.mfa_window import MFAWindow
from backend.auth import auth_manager
from frontend.session import session

class LoginWindow(BaseWindow):
    def __init__(self):
        super().__init__("login.ui")
        self.passwordInput.setEchoMode(QLineEdit.Password)
        self.togglePasswordButton.clicked.connect(self.toggle_password)
        self.authenticateButton.clicked.connect(self.authenticate)

    def toggle_password(self) -> None:
        hidden = self.passwordInput.echoMode() == QLineEdit.Password
        self.passwordInput.setEchoMode(QLineEdit.Normal if hidden else QLineEdit.Password)
        self.togglePasswordButton.setText("Hide" if hidden else "Show")

    def authenticate(self) -> None:
        username = self.usernameInput.text().strip() if hasattr(self, 'usernameInput') else "admin"
        password = self.passwordInput.text().strip()
        
        # Reset session
        session.role = None
        session.user_id = None
        session.is_mfa_verified = False
        session.is_biometric_verified = False
        session.step_up_cache = False

        success, role = auth_manager.login(username, password)
        if success:
            session.user_id = username
            session.role = role
            self.navigate_to(MFAWindow)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
