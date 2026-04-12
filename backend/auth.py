import hashlib
import sqlite3
import os
import pyotp
from typing import Tuple, Optional, Dict, Any

class AuthManager:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "users.db")
        self.emergency_offline_code = "999999"
        self.current_user = None
        self.init_db()

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone_number TEXT,
                    email TEXT,
                    totp_secret TEXT NOT NULL,
                    has_biometric BOOLEAN NOT NULL DEFAULT 0
                )
            ''')
            
            # Check if admin exists
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                # Initialize with default admin
                pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
                secret = pyotp.random_base32()
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role, phone_number, email, totp_secret, has_biometric)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ("admin", pwd_hash, "admin", "555-0100", "admin@hack0.org", secret, False))
            conn.commit()

    def add_user(self, username: str, password: str, role: str, phone: str, email: str, has_biometric: bool) -> str:
        """Add a new user and return their generated TOTP secret"""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        totp_secret = pyotp.random_base32()
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, phone_number, email, totp_secret, has_biometric)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, pwd_hash, role, phone, email, totp_secret, has_biometric))
            conn.commit()
            
        return totp_secret

    def update_user(self, username: str, password: str, role: str, phone: str, email: str) -> bool:
        """Update an existing user's details without altering their TOTP secret or biometric flags."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            # check if user exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if not cursor.fetchone():
                return False
            
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('''
                UPDATE users 
                SET password_hash = ?, role = ?, phone_number = ?, email = ?
                WHERE username = ?
            ''', (pwd_hash, role, phone, email, username))
            conn.commit()
            return True

    def update_my_profile(self, username: str, phone: str, email: str, new_password: str = "") -> bool:
        """Update a user's own profile safely without touching role or totp."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if not cursor.fetchone():
                return False
                
            if new_password:
                pwd_hash = hashlib.sha256(new_password.encode()).hexdigest()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, phone_number = ?, email = ?
                    WHERE username = ?
                ''', (pwd_hash, phone, email, username))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET phone_number = ?, email = ?
                    WHERE username = ?
                ''', (phone, email, username))
            conn.commit()
            return True

    def update_user_biometric_status(self, username: str, status: bool = True) -> bool:
        """Update an existing user's biometric availability flag."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if not cursor.fetchone():
                return False
                
            cursor.execute('UPDATE users SET has_biometric = ? WHERE username = ?', (status, username))
            conn.commit()
            return True

    def login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role FROM users WHERE username = ? AND password_hash = ?', (username, pwd_hash))
            user = cursor.fetchone()
            
            if user:
                self.current_user = username
                return True, user['role']
        return False, None

    def get_current_user_data(self) -> Optional[Dict[str, Any]]:
        if self.current_user:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ?', (self.current_user,))
                user = cursor.fetchone()
                if user:
                    return dict(user)
        return None

    def verify_mfa(self, code: str) -> bool:
        user_data = self.get_current_user_data()
        if not user_data or "totp_secret" not in user_data:
            return False
        
        totp = pyotp.TOTP(user_data["totp_secret"])
        return totp.verify(code, valid_window=1)

    def verify_emergency_code(self, code: str) -> bool:
        return code == self.emergency_offline_code

    def verify_password(self, password: str) -> bool:
        if not self.current_user:
            return False
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', (self.current_user, pwd_hash))
            return cursor.fetchone() is not None

    def is_authenticated(self) -> bool:
        return self.current_user is not None

auth_manager = AuthManager()
