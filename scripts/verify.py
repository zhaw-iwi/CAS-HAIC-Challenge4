"""Run the bounded technical checks, including the default notebook."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "scripts/check_notebook.py"], cwd=ROOT, check=True)
