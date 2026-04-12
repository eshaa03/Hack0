# Hack0 Project Architecture & Capabilities Report

## 1. Executive Summary
Hack0 is a robust, secure, role-based desktop application built using Python and PyQt5. The application is designed to operate securely even in offline or compromised environments by implementing military-grade cryptography, hybrid authentication pipelines (online/offline), telemetry monitoring, steganography (data hiding), and AI-assisted signal correction. 

## 2. Security & Authentication Architecture
The core authentication system utilizes a robust step-up approach, relying on a localized SQLite database (`users.db`) to allow true offline operation.

*   **Primary Authentication**: SHA-256 hashed passwords matching against the SQLite database.
*   **Time-based One-Time Password (TOTP)**: Integration with `pyotp` provides second-factor authentication without requiring internet connectivity.
*   **Biometric Simulations**: Biometric validation flags (`has_biometric`) mimic advanced login systems (e.g., facial recognition integration module).
*   **Emergency Access**: A localized override code (`999999`) exists for catastrophic offline scenarios.
*   **Session Management**: A robust `session.py` architecture maintains state vectors (e.g., `is_mfa_verified`, `is_biometric_verified`, `step_up_cache`) ensuring authorization continuity across restricted windows.

## 3. Role-Based Access Control (RBAC)
The application dynamically injects and hides UI elements according to the Principle of Least Privilege. Actions available to users are strictly gated:

*   **Admin**: Total system oversight. Controls role assignment, user management, and has access to all functional modules including `Manage Roles` and profile configuration.
*   **Operator**: Tasked with active deployment. Can execute **Data Entry** and **Recovery** pipelines, but cannot access system monitoring or QR generation modules.
*   **Analyst**: Tasked with intelligence and extraction. Can access **Recovery** and **Monitoring** (QR Generation), but cannot process primary Data Entry.
*   **Observer**: Strictly read-only monitoring. Denied access to Data Entry, Recovery, and the monitoring interactive tabs. Access is limited to live System Telemetry graphs.

## 4. Cryptographic Pipeline (`crypto.py`)
Hack0 implements a dual-layer cryptographic envelope designed to protect state-secrets at rest and in transit.

*   **Asymmetric Root**: RSA (2048-bit) keypairs are generated and formatted via PKCS8 (PEM) encoding. 
*   **Symmetric Workload**: AES-GCM (Galois/Counter Mode) handles high-speed, authenticated symmetric encryption for the main data payloads. 
*   **Key Wrapping**: AES symmetric keys are securely encrypted using the destination's RSA public key with OAEP padding and SHA-256 hashing format, preventing man-in-the-middle attacks on the cryptographic keys themselves. 

## 5. Steganography Engine (`stego.py`)
Provides advanced capability to securely exfiltrate or hide encrypted payloads within seemingly innocuous carrier files (Images, Audio, General Data).

*   **Image Carrier (LSB)**: Embeds binary payloads into the Least Significant Bits of PNG files without noticeably distorting visual fidelity.
*   **Audio Carrier (LSB)**: Modifies WAV files leveraging the `librosa` library, embedding ciphertexts within the low-level frequency samples.
*   **Generic Appended Carrier**: For massive payloads, the engine bypasses fragile LSB processing and securely appends payloads to the raw binary strings of executables or PDFs, separated by a proprietary marker (`<<HACK0_MARKER>>`).

## 6. Artificial Intelligence Engine (`ai/ai.py`)
AI modules optimize data embedding quality and retrieve corrupted signals during degraded system transmission operations.

*   **AI Noise Reduction**: Utilizes `librosa` Spectral Gating to mock noise filtering algorithms specifically tuned to preserve underlying structural data heuristics.
*   **Signal Quality Analytics**: Calculates realistic Signal-to-Noise Ratio (SNR) in dB, generating a `decoding_reliability` metric for analysts.
*   **Dynamic Payload Recommendations**: Heuristics analyzer maps exact byte weights of payload requests and automatically selects the safest steganographic medium (e.g., Raw Binary/PNG for small payloads; Appended Binary for >10kb to >500kb payloads) to prevent carrier corruption.

## 7. Blockchain Tamper-Resistance (`blockchain.py`)
To prevent internal tampering of cryptographic records, the app leverages a localized JSON-based ledger (`blockchain_ledger.json`). 

*   **Algorithmic Hashing**: Every critical artifact generates a deterministic SHA3-256 hash. 
*   **Immutable Tracking**: Hashes are written against UTC timestamps in a linear chain validation system. Any external modification to the local data breaks the internal chain validation.

## 8. Telemetry & User Interface (`dashboard_window.py`)
The main Command Center dynamically represents critical operations data.

*   **System Tracking**: Hooks into the native OS via `psutil` to graph live CPU and RAM consumption data through `pyqtgraph`.
*   **Metric Synthesis**: Continuously aggregates SQLite user counts, BlockChain ledger verification length, and recent system activities into live-rendering 2x2 multi-plots.
*   **Theming**: Entire application benefits from a custom-designed dark Qt theme prioritizing contrast and military-grade UI aesthetics with clear error handling states.
