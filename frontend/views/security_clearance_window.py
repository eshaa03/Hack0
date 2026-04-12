from frontend.views.base_window import BaseWindow
from frontend.views.dashboard_window import DashboardWindow
from frontend.session import session


class SecurityClearanceWindow(BaseWindow):
    def __init__(self):
        super().__init__("security_clearance.ui")
        self.accessButton.clicked.connect(self.access_system)
        
        # Inject Back/Cancel Button
        from PyQt5.QtWidgets import QPushButton
        self.cancelButton = QPushButton("Cancel Authentication (Back)")
        self.cancelButton.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-weight: bold;")
        layout = self.accessButton.parent().layout()
        if layout:
            layout.addWidget(self.cancelButton)
        self.cancelButton.clicked.connect(self.cancel_auth)
        
        # Hide radio buttons to prevent user selection ambiguity entirely
        self.administratorRadio.hide()
        self.operatorRadio.hide()
        self.analystRadio.hide()
        self.observerRadio.hide()
        
        role = getattr(session, 'role', 'observer')
        if role == 'admin':
            role_display = "Administrator"
        elif role == 'operator':
            role_display = "Secure Operator"
        elif role == 'analyst':
            role_display = "Intelligence Analyst"
        else:
            role_display = "Observer"
            
        # Display Only The Assigned Clearnance
        self.subTitleLabel.setText(f"Security Cleared As: {role_display}")
        self.subTitleLabel.setStyleSheet("font-size: 20px; font-weight: bold; color: #00E5FF;")

    def access_system(self) -> None:
        self.navigate_to(DashboardWindow)

    def cancel_auth(self):
        from frontend.session import session
        from frontend.views.login_window import LoginWindow
        session.user_id = None
        session.role = None
        session.is_mfa_verified = False
        session.is_biometric_verified = False
        self.navigate_to(LoginWindow)
