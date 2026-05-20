import subprocess
print("[STARTUP] Running migrations...")
subprocess.run(['python', 'migrations/add_iv_columns.py'])
subprocess.run(['python', 'migrations/add_email_verification.py'])
print("[STARTUP] Done")
from migrations.add_updated_at_column import run_migration as add_updated_at
    add_updated_at()
