import hashlib
import sqlite3
import os
import re
import pyotp
from typing import Tuple, Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DATABASE_KEY = os.environ.get("DATABASE_KEY")
if not DATABASE_KEY:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("DATABASE_KEY="):
                    DATABASE_KEY = line.strip().split("=", 1)[1]
    
    if not DATABASE_KEY:
        DATABASE_KEY = os.urandom(32).hex()
        with open(env_path, "a") as f:
            f.write(f"\nDATABASE_KEY={DATABASE_KEY}\n")

def _encrypt_blob(data: bytes) -> bytes:
    if not data: return data
    key = bytes.fromhex(DATABASE_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, data, None)

def _decrypt_blob(data: bytes) -> bytes:
    if not data: return data
    key = bytes.fromhex(DATABASE_KEY)
    aesgcm = AESGCM(key)
    nonce = data[:12]
    ct = data[12:]
    return aesgcm.decrypt(nonce, ct, None)

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
            
            # Migration check: Add face_model_blob column if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'face_model_blob' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN face_model_blob BLOB")
                
            conn.commit()

    def _normalize_username(self, username: str) -> str:
        return username.strip()

    def _normalize_email(self, email: str) -> Optional[str]:
        email = email.strip().lower()
        return email or None

    def _normalize_phone(self, phone: str) -> Optional[str]:
        phone = phone.strip()
        return phone or None

    def _validate_user_fields(self, username: str, password: str, phone: str, email: str, require_password: bool = True) -> Tuple[str, Optional[str], Optional[str]]:
        username = self._normalize_username(username)
        email = self._normalize_email(email)
        phone = self._normalize_phone(phone)

        if not username:
            raise ValueError("Username is required.")
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            raise ValueError("Username may only contain letters, numbers, dot, underscore, and hyphen.")

        if require_password and len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        if email and not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Please enter a valid email address.")

        if phone and not re.fullmatch(r"^\+?[\d\s\-()]{7,18}$", phone):
            raise ValueError("Please enter a valid phone number.")

        return username, phone, email

    def _ensure_unique_identity_fields(self, username: str, phone: Optional[str], email: Optional[str], exclude_username: Optional[str] = None) -> None:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT username FROM users WHERE lower(username) = lower(?)", (username,))
            row = cursor.fetchone()
            if row and row["username"] != exclude_username:
                raise ValueError("Username already exists.")

            if email:
                cursor.execute("SELECT username FROM users WHERE lower(email) = lower(?)", (email,))
                row = cursor.fetchone()
                if row and row["username"] != exclude_username:
                    raise ValueError("Email address is already in use.")

            if phone:
                cursor.execute("SELECT username FROM users WHERE phone_number = ?", (phone,))
                row = cursor.fetchone()
                if row and row["username"] != exclude_username:
                    raise ValueError("Phone number is already in use.")

    def save_face_model_to_db(self, username: str, blob: bytes) -> bool:
        """Stores the given pre-trained biometric face model into the DB."""
        encrypted_blob = _encrypt_blob(blob)
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if not cursor.fetchone():
                return False
            cursor.execute('UPDATE users SET face_model_blob = ? WHERE username = ?', (encrypted_blob, username))
            conn.commit()
            return True

    def get_face_model_from_db(self, username: str) -> Optional[bytes]:
        """Retrieves the user's face model binary blob directly from SQLite."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT face_model_blob FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row and row['face_model_blob']:
                try:
                    return _decrypt_blob(row['face_model_blob'])
                except Exception as e:
                    print(f"Failed to decrypt biometric blob for {username}: {e}")
                    return None
        return None

    def add_user(self, username: str, password: str, role: str, phone: str, email: str, has_biometric: bool) -> str:
        """Add a new user and return their generated TOTP secret"""
        username, phone, email = self._validate_user_fields(username, password, phone, email, require_password=True)
        self._ensure_unique_identity_fields(username, phone, email)
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

    def delete_user(self, username: str) -> bool:
        """Deletes a user from the database."""
        if username.lower() == 'admin':
            return False # Prevent deleting the default admin
            
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if not cursor.fetchone():
                return False
                
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return True

    def update_user(self, username: str, password: str, role: str, phone: str, email: str) -> bool:
        """Update an existing user's details without altering their TOTP secret or biometric flags."""
        username, phone, email = self._validate_user_fields(username, password, phone, email, require_password=True)
        self._ensure_unique_identity_fields(username, phone, email, exclude_username=username)
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
        username, phone, email = self._validate_user_fields(username, new_password, phone, email, require_password=False)
        if new_password and len(new_password) < 6:
            raise ValueError("Your new password must be at least 6 characters long.")
        self._ensure_unique_identity_fields(username, phone, email, exclude_username=username)
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

    def get_all_users(self) -> list:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username, role, phone_number, email, has_biometric FROM users')
            return [dict(row) for row in cursor.fetchall()]

    def verify_mfa(self, code: str) -> bool:
        user_data = self.get_current_user_data()
        if not user_data or "totp_secret" not in user_data:
            return False
        
        totp = pyotp.TOTP(user_data["totp_secret"])
        return totp.verify(code, valid_window=5)

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
