SYSTEM_STATS = [
    ("Active Sessions", "12", "+3"),
    ("Files Encrypted", "1,247", "+89"),
    ("System Health", "98%", "+2%"),
    ("Blockchain Verified", "3,456", "+156"),
]

RECENT_ACTIVITY = [
    "AES-GCM encryption completed | Operator-7 | 2 min ago | success",
    "Signal embedded in audio carrier | Analyst-3 | 5 min ago | success",
    "Blockchain verification passed | Operator-7 | 8 min ago | success",
    "AI noise reduction applied | Admin-1 | 12 min ago | warning",
    "RSA key generated | Operator-5 | 15 min ago | success",
]

CARRIER_TYPES = [
    "Audio Carrier | WAV, MP3, FLAC, OGG | Frequency domain embedding",
    "Image Carrier | PNG, JPEG, BMP, TIFF | LSB / DCT embedding",
    "Video Carrier | MP4, AVI, MKV, MOV | Frame-by-frame embedding",
    "Binary File Carrier | ZIP, PDF, DOCX, EXE, DAT | Byte-level insertion",
]

ENCRYPTION_PIPELINE = [
    "Data Input Validation",
    "AES Key Generation",
    "AES-GCM Encryption",
    "RSA Key Protection",
    "Authentication Tag",
]

MONITORING_ACTIVITY_LOGS = [
    "14:32:45 | Operator-7 | File encrypted | INFO",
    "14:31:12 | Analyst-3 | Signal extracted from carrier | INFO",
    "14:29:58 | Admin-1 | New RSA key pair generated | INFO",
    "14:23:07 | Operator-7 | Failed decryption attempt | WARNING",
    "14:21:45 | Unknown | Unauthorized access attempt | CRITICAL",
]

MONITORING_ALERTS = [
    "MEDIUM | Multiple failed decryption attempts detected | 10 min ago",
    "LOW | System backup completed successfully | 25 min ago",
    "HIGH | Unauthorized access attempt blocked | 32 min ago",
]

ANALYTICS_SUMMARY = """Encryption Operations: 1247 (+12%)
Active Users: 24 (+3)
Blocked Threats: 7 (-2)
System Uptime: 99.8% (+0.1%)

Top Users:
- Operator-7: 245 ops
- Analyst-3: 189 ops
- Admin-1: 156 ops

Operation Types:
- Encryption: 456
- Decryption: 312
- Embedding: 189
- Extraction: 156
"""

EMBEDDING_TEXT = {
    "audio": "Carrier upload, embedding strength 10-100%, LSB + frequency masking, integrity verification, output download.",
    "image": "Carrier upload, LSB/DCT/DWT method, bit plane 1-4, PSNR/MSE/SSIM quality checks, output download.",
    "video": "Carrier upload, frame interval 1-15, temporal distribution, frame processing pipeline, output download.",
    "file": "Binary file upload, append/insert/scatter/header methods, checksum updates, file integrity verification.",
}

RECOVERY_PIPELINE = [
    "Carrier Loading and Analysis",
    "AI Signal Detection and Noise Reduction",
    "Blockchain Verification",
    "RSA Key Decryption",
    "AES-GCM Decryption",
    "Data Reconstruction",
]

DATA_ENTRY_TEXT = """Enter confidential text or upload file for secure processing.
Supports: Text, PDF, DOCX, Images, Audio, Archives.

File upload will convert to binary for encryption pipeline."""

QR_TEXT = "QR Preview:\n[Mock QR Code Display]\n\nScan to verify data integrity.\nSupports up to 4K data payload."

SHARING_OPTIONS = [
    "Local Export: USB drive, offline storage (fully secure)",
    "Email Attachment: Appears as normal audio/image file",
    "Cloud Storage: Dropbox/Google Drive (carrier looks innocent)",
    "QR Code: Instant sharing, scan to receive",
]
