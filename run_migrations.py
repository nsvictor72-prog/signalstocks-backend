import subprocess
print("[STARTUP] Running migrations...")
subprocess.run(['python', 'migrations/add_iv_columns.py'])
print("[STARTUP] Done")
