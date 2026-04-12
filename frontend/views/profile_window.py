import os
import re
import cv2
import numpy as np
from PyQt5.QtWidgets import QMessageBox, QLineEdit

from frontend.views.base_window import BaseWindow
from backend.auth import auth_manager
from frontend.session import session

class ProfileWindow(BaseWindow):
    def __init__(self):
        super().__init__("profile.ui")
        
        # Optional: set password input to show dots
        if hasattr(self, 'passwordInput'):
            self.passwordInput.setEchoMode(QLineEdit.Password)
        
        self.username = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        self.load_profile()
        self.connect_buttons()

    def load_profile(self):
        user_data = auth_manager.get_current_user_data()
        if not user_data:
            self.statusLabel.setText("Error: Could not load user profile.")
            return
            
        self.username = user_data["username"]
        self.usernameLabel.setText(f"Username: {self.username}")
        
        # Populate contact details
        phone = user_data.get("phone_number", "")
        email = user_data.get("email", "")
        
        self.phoneInput.setText(phone if phone else "")
        self.emailInput.setText(email if email else "")

    def connect_buttons(self):
        self.backButton.clicked.connect(self.go_back)
        self.updateProfileButton.clicked.connect(self.update_profile)
        self.registerBiometricButton.clicked.connect(self.register_biometrics)

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)

    def prompt_authentication(self) -> bool:
        from PyQt5.QtWidgets import QInputDialog
        password, ok = QInputDialog.getText(
            self, "Security Verification", 
            "Please enter your current password to authorize this action:", 
            QLineEdit.Password
        )
        if ok and password:
            success, _ = auth_manager.login(self.username, password)
            if success:
                return True
        QMessageBox.warning(self, "Authentication Failed", "Incorrect password or action cancelled.")
        return False

    def update_profile(self):
        if not self.username:
            QMessageBox.warning(self, "Error", "No user profile loaded.")
            return

        if not self.prompt_authentication():
            return

        phone = self.phoneInput.text().strip()
        email = self.emailInput.text().strip()
        new_password = self.passwordInput.text().strip()
        
        # Format Validation
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid email address containing an '@' and a domain.")
            return
            
        if phone and not re.match(r"^\+?[\d\s\-()]{7,18}$", phone):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid phone number (digits, hyphens, and parentheses).")
            return
            
        if new_password and len(new_password) < 6:
            QMessageBox.warning(self, "Weak Password", "Your new password must be at least 6 characters long.")
            return
        
        success = auth_manager.update_my_profile(self.username, phone, email, new_password)
        if success:
            self.statusLabel.setText("Profile updated successfully.")
            msg = "Your profile has been updated."
            if new_password:
                msg += " Password was also changed."
            QMessageBox.information(self, "Success", msg)
            self.passwordInput.clear()
        else:
            self.statusLabel.setText("Failed to update profile.")
            QMessageBox.warning(self, "Error", "Could not update profile.")

    def register_biometrics(self):
        if not self.username:
            QMessageBox.warning(self, "Error", "No user profile loaded.")
            return

        if not self.prompt_authentication():
            return

        self.statusLabel.setText("Opening webcam. Look at the camera...")
        QMessageBox.information(self, "Biometric Registration", "The webcam will open. Please look at the camera until registration completes.")
        
        cap = cv2.VideoCapture(0)
        faces_data = []
        labels = []
        user_id = 1 # Dummy ID for model
        sample_num = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                faces_data.append(gray[y:y+h, x:x+w])
                labels.append(user_id)
                sample_num += 1
            
            cv2.imshow("Registering Faces", frame)
            cv2.waitKey(1)
            
            if sample_num > 50:
                break
                
        cap.release()
        cv2.destroyAllWindows()
        
        if len(faces_data) > 0:
            self.recognizer.train(faces_data, np.array(labels))
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", f"{self.username}_face.yml")
            self.recognizer.save(model_path)
            
            # Update user's biometric availability status in DB
            auth_manager.update_user_biometric_status(self.username, status=True)
            
            self.statusLabel.setText("Biometrics registered successfully.")
            QMessageBox.information(self, "Success", "Biometric data captured and saved.")
        else:
            self.statusLabel.setText("Failed to capture faces.")
            QMessageBox.warning(self, "Error", "No face detected. Please try again.")

