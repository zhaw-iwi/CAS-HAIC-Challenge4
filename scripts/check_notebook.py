"""Execute the default notebook without credentials and save a local verification copy."""
import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.pop("OPENAI_API_KEY", None)
os.environ["CHALLENGE_OFFLINE"] = "1"
notebook = nbformat.read(ROOT / "Evidenzknacker.ipynb", as_version=4)
nbformat.validate(notebook)
NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
destination = ROOT / "outputs/notebook_checked.ipynb"
destination.parent.mkdir(exist_ok=True)
nbformat.write(notebook, destination)
print(f"Notebook ohne API-Aufrufe ausgeführt: {destination}")
