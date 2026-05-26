# Hack0: Advanced Cryptographic & Steganographic Data Management System

![Hack0 Banner](https://img.shields.io/badge/Status-Active-brightgreen) ![Python Version](https://img.shields.io/badge/Python-3.x-blue) ![License](https://img.shields.io/badge/License-MIT-orange)

Hack0 is a highly secure, PyQt5-based desktop application designed for secure data orchestration. It acts as a comprehensive vault for sensitive information by leveraging a hybrid cryptographic engine (RSA + AES-GCM), biometric authentication, advanced multimedia steganography, and an immutable blockchain-style ledger.

---

## ✨ Core Features & Architectural Deep Dive

### 🔐 Multi-Tiered Authentication & RBAC
Identity management in Hack0 is strict and heavily layered to secure local workstation constraints.
- **Multi-Factor Authentication (MFA)**: Supports TOTP (Time-Based One-Time Passwords) via `pyotp`. Users configure their devices upon first login.
- **Biometric Security Engine**: Built-in support for facial recognition models. The AI models (managed via PyTorch & OpenCV) are converted into secure blobs and encrypted dynamically into the SQLite database (`users.db`).
- **Granular Role-Based Access Control (RBAC)**:
  - `Admin`: Full access. Can provision roles, manage user biometric lifecycle, and access system settings.
  - `Operator`: Can encrypt payloads, access the data-entry pipelines, and secure exports.
  - `Analyst`: Can access the recovery and decryption pipelines, but barred from raw-data entry.
  - `Observer`: Read-only telemetry views on the administrative dashboard.
- **Step-Up Authentication**: Elevated workflows (e.g., extracting data, deploying a Private Key) dynamically require re-verification of the principal's password.

### 🛡 Real-Time Hybrid Cryptographic Engine
Hack0 utilizes a dual-mode cryptographic pipeline, visually exposing real-time progression to the operator.
- **Asymmetric Encapsulation (RSA-1024 + AES-GCM)**: Sensitive payloads are primarily encrypted using AES-GCM for robust authenticated encryption. The AES symmetric key is then encrypted via the recipient's RSA-1024 public key utilizing optimal asymmetric encryption padding (OAEP/SHA1). Private keys (`.pem`) are heavily secured (PKCS8) via PBKDF2.
- **Symmetric Fallback**: Includes capabilities for PBKDF2-HMAC (200k iterations) derived password protection for direct AES-256 symmetrical operations if Public Keys are unavailable. 
- **Hash Integrity Verification**: All decryption routines mandate `SHA3-256` authenticity verification.

### 🤫 In-Depth Multimedia Steganography
Hack0 doesn't just encrypt data; it hides its very presence from casual forensic observation.
- **Image LSB Subversion (`stego.py`)**: Discreetly hides encrypted payloads directly into the Least Significant Bits (LSB) of standard image bytes (via Pillow and Numpy arrays). Employs `H0SG` magic packet headers and legacy 64-bit termination tracking.
- **Audio Modulation (`encoder.py`)**: Encodes binary bytes into Mock Audio Signals (PCM Amplitude). To recover data, Hack0 applies active AI Noise Cancellation workflows before applying vector-pooled mean approximations to re-assemble the true payload bytes from `.wav` signal waveforms.
- **Generic File Appending**: Conceal data transparently at the end of innocuous binaries utilizing strict `<<HACK0_MARKER>>` injection indexing routines.

### 📡 Secure Exfiltration & Telemetry
- **Dynamic LAN Exports**: Generates on-the-fly local TCP Socket Servers wrapped into an export QR code, allowing physically proximate devices to download payload carriers over local ethernet/Wi-Fi topologies without crossing external ISP routes.
- **SMTP Network Relays**: Securely ship standard-carrier files directly over email attachments using automated SMTP relays natively integrated into `network_utils.py`.
- **System Telemetry Matrix**: The PyQt Dashboard provides aggressive real-time `pyqtgraph` profiling of system CPU footprints, RAM load, User Access volumes, and Blockchain integrity state.

### ⛓️ Immutable Auditing Ledger
All operational actions in Hack0 are hashed and retained to prevent tamper-based attacks.
- **The Blockchain (`blockchain.py`)**: Sensitive module executions, configuration patches, and encrypted file distributions trigger an internal transaction commit. 
- The target payload structures are hashed (`SHA3-256`) and stored linearly alongside strict ISO timestamps within `blockchain_ledger.json`. Decryption will halt and warn the user if a carrier hash isn't recognized by the known internal network state.

---

## 🛠️ Technology Stack Breakdown

- **Core Runtime**: `Python 3`
- **Graphical Subsystem**: `PyQt5`, `pyqtgraph`
- **Cryptography & Defense**: `cryptography`, `hashlib`, `pyotp`
- **Machine Learning & Biometrics**: `torch` (PyTorch), `opencv-python` (cv2), `scikit-learn`
- **Audio & Signal Processing**: `librosa`, `soundfile`
- **Image Mathematics**: `Pillow`, `numpy`, `scipy`
- **Storage/Databases**: `SQLite3` (Protected DB blobs), `json`

---

## 🚀 Installation & Network Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Hack0.git
   cd Hack0
   ```

2. **Initialize a secure Python virtual environment (Required):**
   ```bash
   python -m venv venv
   
   # Windows Activation:
   venv\Scripts\activate
   # macOS/Linux Activation:
   source venv/bin/activate
   ```

3. **Install Core Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration (`.env`):**
   Create a standard `.env` configuration template in root. The system leverages these for runtime integrations. If a `DATABASE_KEY` is omitted, the `auth.py` manager will seed a rigid 32-byte rotational hex on boot.
   ```env
   SMTP_EMAIL=operator@defense-domain.internal
   SMTP_PASSWORD=your_app_password
   # DATABASE_KEY (auto-generated if left blank)
   ```

5. **Execute Runtime Environment:**
   Run the overarching application controller:
   ```bash
   python main.py
   # Or using the native Windows Batch Script:
   run.bat
   ```

---

## 📂 Structural Pipeline

- `backend/` 
  - `auth.py` – Implements PyOTP and SQLite database transactional locks.
  - `crypto.py` – Engine for RSA/GCM operations.
  - `stego.py` / `encoder.py` – Multimedia carrier generation logic (WAV, Image).
  - `blockchain.py` – Immutable auditing layer hash algorithms.
  - `network_utils.py` – Socket generation and direct SMTP networking capabilities.
- `frontend/`
  - `/views/` – Modular PyQT windows (`recovery_window.py`, `dashboard_window.py`, etc.).
  - `/styles/` – Contains `theme_ironman.qss` mapping the strict application-wide unified dark aesthetic.
- `ai/` – Handles advanced mathematical biometrics, PyTorch interactions, and ML integration for access controls.
- `tests/` – Automated QA deployment scripts using pytest frameworks.

---

## 👥 Setup & Administration

**First Boot Generation**:
Upon first successful compilation and database initialization (`users.db`), the system will securely bootstrap an initial override profile:
- **Default Username**: `admin`
- **Default Password**: `admin123`

*Important Configuration Note:* Hack0 mandates 2FA out of the box. During your first login with the bootstrap Admin credentials, you will immediately be provided with a generated PyOTP secret. You must bind this configuration to an external authenticator application (such as Google Authenticator, Authy, or similar) to proceed into the system dashboard.

## ⚠️ Security Disclaimer
This software repository acts as a conceptual framework designed explicitly for authorized cyber-security education, auditing infrastructures, and defensive research. Do not operate, deploy, or otherwise use these tools to bypass, penetrate, or manipulate restricted system structures without the explicit, documented administrative consent of the asset owners.

---
*Built for absolute real-time operational security.*