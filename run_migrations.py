import subprocess
print("[STARTUP] Running migrations...")
subprocess.run(['python', 'migrations/add_iv_columns.py'])
subprocess.run(['python', 'migrations/add_email_verification.py'])
print("[STARTUP] Done")
