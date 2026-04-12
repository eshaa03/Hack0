import os
import cv2
import numpy as np
from PyQt5.QtWidgets import QMessageBox

from frontend.views.base_window import BaseWindow
from backend.auth import auth_manager

class ManageUsersWindow(BaseWindow):
    def __init__(self):
        super().__init__("manage_users.ui")
        self.addUserButton.clicked.connect(self.add_user)
        
        # Inject dynamic Update User button
        from PyQt5.QtWidgets import QPushButton
        self.updateUserButton = QPushButton("Update Existing User")
        self.updateUserButton.setStyleSheet("background-color: #f39c12; color: white;")
        layout = self.addUserButton.parent().layout()
        if layout:
            layout.addWidget(self.updateUserButton)
        self.updateUserButton.clicked.connect(self.update_existing_user)
        
        self.registerBiometricButton.clicked.connect(self.register_biometrics)
        self.backButton.clicked.connect(self.go_back)
        self.has_biometric = False
        
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()

    def go_back(self):
        from frontend.views.dashboard_window import DashboardWindow
        self.navigate_to(DashboardWindow)

    def register_biometrics(self):
        username = self.usernameInput.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a username first before registering biometrics.")
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
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", f"{username}_face.yml")
            self.recognizer.save(model_path)
            self.has_biometric = True
            
            # If user already exists in DB, automatically toggle their biometrics active flag
            auth_manager.update_user_biometric_status(username, status=True)
            
            self.statusLabel.setText(f"Biometrics registered for {username}.")
            QMessageBox.information(self, "Success", "Biometric data captured successfully.")
        else:
            self.statusLabel.setText("Failed to capture faces.")
            QMessageBox.warning(self, "Error", "Face not detected. Try again.")

    def update_existing_user(self):
        username = self.usernameInput.text().strip()
        password = self.passwordInput.text().strip()
        role = self.roleComboBox.currentText()
        phone = self.phoneInput.text().strip()
        
        email = ""
        if hasattr(self, 'emailInput'):
            email = self.emailInput.text().strip()
            
        if not username or not password:
            self.statusLabel.setText("Username and password required to update.")
            return
            
        success = auth_manager.update_user(username, password, role, phone, email)
        if success:
            self.statusLabel.setText(f"User {username} updated successfully.")
            QMessageBox.information(self, "User Updated", f"Profile for {username} was updated.")
            
            # Reset fields
            self.usernameInput.clear()
            self.passwordInput.clear()
            self.phoneInput.clear()
            if hasattr(self, 'emailInput'):
                self.emailInput.clear()
        else:
            self.statusLabel.setText("User does not exist.")
            QMessageBox.warning(self, "Error", "Cannot update. Username does not exist.")

    def add_user(self):
        username = self.usernameInput.text().strip()
        password = self.passwordInput.text().strip()
        role = self.roleComboBox.currentText()
        phone = self.phoneInput.text().strip()
        
        email = ""
        if hasattr(self, 'emailInput'):
            email = self.emailInput.text().strip()
        
        if not username or not password:
            self.statusLabel.setText("Username and password required.")
            return
            
        with auth_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                self.statusLabel.setText("User already exists.")
                return
            
        totp_secret = auth_manager.add_user(username, password, role, phone, email, self.has_biometric)
        
        self.statusLabel.setText(f"User {username} added.")
        msg = f"User: {username}\nRole: {role}\n\nTOTP SECRET (Save this!):\n{totp_secret}"
        QMessageBox.information(self, "User Registered", msg)
        
        # Reset fields
        self.usernameInput.clear()
        self.passwordInput.clear()
        self.phoneInput.clear()
        if hasattr(self, 'emailInput'):
            self.emailInput.clear()
        self.has_biometric = False
