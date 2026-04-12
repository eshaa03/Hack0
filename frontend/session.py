class SessionData:
    def __init__(self):
        # Authentication & RBAC
        self.user_id = None
        self.role = None
        self.is_mfa_verified = False
        self.is_biometric_verified = False
        self.step_up_cache = False

        # Crypto & Data
        self.plaintext = None
        self.encrypted_data = None
        self.nonce = None
        self.aes_key = None
        self.private_pem = None
        self.public_pem = None
        self.data_hash = None
        self.encoded_output_path = None

session = SessionData()
