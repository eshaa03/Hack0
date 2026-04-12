import subprocess

out = subprocess.getoutput(r"venv\Scripts\python.exe -m pylint frontend/views/recovery_window.py")
print(out)
