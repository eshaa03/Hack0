from backend.auth import auth_manager
import pyotp
import time

auth_manager.login("admin", "admin123")
user_data = auth_manager.get_current_user_data()
secret = user_data["totp_secret"]

totp = pyotp.TOTP(secret)

current_code = totp.now()
old_code = totp.at(time.time() - 30)
future_code = totp.at(time.time() + 30)
invalid_code = totp.at(time.time() - 60)

print(f"Current Verify: {auth_manager.verify_mfa(current_code)}")
print(f"Old (-30s) Verify: {auth_manager.verify_mfa(old_code)}")
print(f"Future (+30s) Verify: {auth_manager.verify_mfa(future_code)}")
print(f"Invalid (-60s) Verify: {auth_manager.verify_mfa(invalid_code)}")
