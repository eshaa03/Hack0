import os
import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox

from frontend.views.base_window import BaseWindow
from frontend.views.security_clearance_window import SecurityClearanceWindow
from backend.auth import auth_manager

class BiometricWindow(BaseWindow):
    def __init__(self):
        super().__init__("biometric.ui")
        self.scanButton.clicked.connect(self.start_scan)
        self.continueButton.clicked.connect(lambda: self.navigate_to(SecurityClearanceWindow))
        self.continueButton.setEnabled(False)
        
        # Inject Back/Cancel Button
        from PyQt5.QtWidgets import QPushButton
        self.cancelButton = QPushButton("Cancel Authentication (Back)")
        self.cancelButton.setStyleSheet("background-color: #dc3545; color: white; padding: 10px; font-weight: bold;")
        layout = self.scanButton.parent().layout()
        if layout:
            layout.addWidget(self.cancelButton)
        self.cancelButton.clicked.connect(self.cancel_auth)
        
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.model_loaded = False
        
        # Try to load model for current user
        user_id = getattr(auth_manager, 'current_user', None)
        if user_id:
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", f"{user_id}_face.yml")
            if os.path.exists(model_path):
                self.recognizer.read(model_path)
                self.model_loaded = True
            else:
                self.statusLabel.setText("No biometric model found for user.")
                self.scanButton.setEnabled(False)

    def start_scan(self) -> None:
        if not self.model_loaded:
            return

        self.statusLabel.setText("Initializing real-time facial recognition...")
        self.scanButton.setEnabled(False)
        QMessageBox.information(self, "Biometric Scan", "Look at the camera. Verification will complete automatically upon positive match.")

        cap = cv2.VideoCapture(0)
        authenticated = False
        attempts = 0
        
        while attempts < 100:
            ret, frame = cap.read()
            if not ret:
                break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
                face_crop = gray[y:y+h, x:x+w]
                
                label, confidence = self.recognizer.predict(face_crop)
                # Lower confidence means better match for LBPH
                if confidence < 75:  
                    authenticated = True
                    break
                    
            cv2.imshow("Authenticating - Look at Camera", frame)
            cv2.waitKey(30)
            
            if authenticated:
                break
                
            attempts += 1
            
        cap.release()
        cv2.destroyAllWindows()
        
        if authenticated:
            from frontend.session import session
            session.is_biometric_verified = True
            
            self.scanProgress.setValue(100)
            self.statusLabel.setText("Facial recognition SUCCESS. Identity verified.")
            self.scanButton.setEnabled(True)
            self.continueButton.setEnabled(True)
            
            QMessageBox.information(self, "Success", "Biometric verification successful.")
        else:
            self.statusLabel.setText("Face not recognized or timed out.")
            self.scanButton.setEnabled(True)
            QMessageBox.warning(self, "Failed", "Could not verify identity. Please try again.")

    def cancel_auth(self):
        from frontend.session import session
        from frontend.views.login_window import LoginWindow
        session.user_id = None
        session.role = None
        session.is_mfa_verified = False
        session.is_biometric_verified = False
        self.navigate_to(LoginWindow)
