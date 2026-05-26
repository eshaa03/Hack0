import logging
import os
from datetime import datetime

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"audit_{datetime.now().strftime('%Y-%m')}.log")

logger = logging.getLogger("Hack0_Audit")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def log_security_event(action: str, status: str, details: str = ""):
    logger.info(f"SECURITY EVENT | {action} | {status} | {details}")
