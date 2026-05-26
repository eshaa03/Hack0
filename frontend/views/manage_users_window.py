import os
import cv2
import re
import tempfile
import numpy as np
from PyQt5.QtWidgets import QMessageBox, QHeaderView

from frontend.views.base_window import BaseWindow
from backend.auth import auth_manager

class ManageUsersWindow(BaseWindow):
    def __init__(self):
        super().__init__("manage_users.ui")
        from PyQt5.QtGui import QIcon, QPainter
        from PyQt5.QtWidgets import QStyle
        from PyQt5.QtCore import Qt
        
        def get_text_color_icon(standard_icon):
            pixmap = self.style().standardIcon(standard_icon).pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), Qt.white)
            painter.end()
            return QIcon(pixmap)
            
        self.addUserButton.setIcon(get_text_color_icon(QStyle.SP_FileIcon))
        self.addUserButton.clicked.connect(self.add_user)
        
        # update and delete user buttons are natively in UI now
        self.updateUserButton.setIcon(get_text_color_icon(QStyle.SP_BrowserReload))
        self.updateUserButton.clicked.connect(self.update_existing_user)
        
        self.deleteUserButton.setIcon(get_text_color_icon(QStyle.SP_TrashIcon))
        self.deleteUserButton.clicked.connect(self.delete_user)
        
        self.registerBiometricButton.setIcon(get_text_color_icon(QStyle.SP_ComputerIcon))
        self.registerBiometricButton.clicked.connect(self.register_biometrics)
        
        self.backButton.setIcon(get_text_color_icon(QStyle.SP_ArrowBack))
        self.backButton.clicked.connect(self.go_back)
        
        self.has_biometric = False
        
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()

        # Connect table selection to auto-fill form
        if hasattr(self, 'usersTable'):
            self.tableGroup.setTitle("Registered Users Matrix")
            self.formGroup.setTitle("Admin Controls & Credentials")
            self.usersTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.usersTable.verticalHeader().setVisible(False)
            self.usersTable.viewport().setStyleSheet("background-color: #071018;")
            self.usersTable.itemSelectionChanged.connect(self.on_user_selected)
            self.refresh_users_table()
            
    def refresh_users_table(self):
        if not hasattr(self, 'usersTable'): return
        users = auth_manager.get_all_users()
        self.usersTable.setRowCount(0)
        from PyQt5.QtWidgets import QTableWidgetItem
        for row_idx, user in enumerate(users):
            self.usersTable.insertRow(row_idx)
            self.usersTable.setItem(row_idx, 0, QTableWidgetItem(user.get('username', '')))
            self.usersTable.setItem(row_idx, 1, QTableWidgetItem(user.get('role', '')))
            self.usersTable.setItem(row_idx, 2, QTableWidgetItem(user.get('phone_number', '') or ''))
            self.usersTable.setItem(row_idx, 3, QTableWidgetItem(user.get('email', '') or ''))
            
    def on_user_selected(self):
        selected_items = self.usersTable.selectedItems()
        if not selected_items: return
        row = selected_items[0].row()
        username = self.usersTable.item(row, 0).text()
        role = self.usersTable.item(row, 1).text()
        phone = self.usersTable.item(row, 2).text()
        email = self.usersTable.item(row, 3).text()
        
        self.usernameInput.setText(username)
        idx = self.roleComboBox.findText(role)
        if idx >= 0: self.roleComboBox.setCurrentIndex(idx)
        self.phoneInput.setText(phone)
        if hasattr(self, 'emailInput'): self.emailInput.setText(email)
        self.passwordInput.clear() # Require password entry for updates

    def delete_user(self):
        username = self.usernameInput.text().strip()
        if not username:
            self.statusLabel.setText("Username required to delete.")
            return

        if username.lower() == 'admin':
            QMessageBox.warning(self, "Action Denied", "Cannot delete the default admin account.")
            return

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to completely remove user '{username}' from the system?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success = auth_manager.delete_user(username)
            if success:
                self.statusLabel.setText(f"User {username} deleted successfully.")
                QMessageBox.information(self, "Deleted", f"User {username} has been eradicated.")
                self.usernameInput.clear()
                self.refresh_users_table()
            else:
                self.statusLabel.setText("User does not exist.")
                QMessageBox.warning(self, "Error", f"Failed to delete {username}. They might not exist.")

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
            
            # Secure write to DB via temporary proxy
            fd, temp_path = tempfile.mkstemp(suffix=".yml")
            os.close(fd)
            self.recognizer.save(temp_path)
            with open(temp_path, "rb") as f:
                blob = f.read()
            os.remove(temp_path)
            
            self.has_biometric = True
            
            # If user already exists in DB, automatically toggle their biometrics active flag and inject blob
            if auth_manager.update_user_biometric_status(username, status=True):
                auth_manager.save_face_model_to_db(username, blob)
                self.statusLabel.setText(f"Biometrics registered for {username}.")
                QMessageBox.information(self, "Success", "Biometric data captured successfully.")
            else:
                self.statusLabel.setText("Biometrics cached for Registration.")
                QMessageBox.information(self, "Success", f"Biometrics held in memory. Ensure you finish adding the user {username} via Add User!")
                # Technically for 'Add User' we need to pass this blob. Since the add user flow might be used for NEW users,
                # let's just save it immediately using a dummy insert or just cache the blob on the window.
                self.cached_blob = blob 
                self.cached_username = username
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

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid email address.")
            return
            
        if phone and not re.match(r"^\+?[\d\s\-()]{7,18}$", phone):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid phone number.")
            return
            
        if password and len(password) < 6:
            QMessageBox.warning(self, "Weak Password", "Password must be at least 6 characters long.")
            return
            
        try:
            success = auth_manager.update_user(username, password, role, phone, email)
        except ValueError as e:
            self.statusLabel.setText(str(e))
            QMessageBox.warning(self, "Validation Error", str(e))
            return
        if success:
            self.statusLabel.setText(f"User {username} updated successfully.")
            QMessageBox.information(self, "User Updated", f"Profile for {username} was updated.")
            
            # Reset fields
            self.usernameInput.clear()
            self.passwordInput.clear()
            self.phoneInput.clear()
            if hasattr(self, 'emailInput'):
                self.emailInput.clear()
            self.refresh_users_table()
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

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid email address.")
            return
            
        if phone and not re.match(r"^\+?[\d\s\-()]{7,18}$", phone):
            QMessageBox.warning(self, "Invalid Format", "Please enter a valid phone number.")
            return
            
        if password and len(password) < 6:
            QMessageBox.warning(self, "Weak Password", "Password must be at least 6 characters long.")
            return
            
        try:
            totp_secret = auth_manager.add_user(username, password, role, phone, email, self.has_biometric)
        except ValueError as e:
            self.statusLabel.setText(str(e))
            QMessageBox.warning(self, "Validation Error", str(e))
            return
        
        # Save cached biometric blob if it exists
        if self.has_biometric and hasattr(self, 'cached_blob') and self.cached_username == username:
             auth_manager.save_face_model_to_db(username, self.cached_blob)
             del self.cached_blob
        
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
        self.refresh_users_table()
