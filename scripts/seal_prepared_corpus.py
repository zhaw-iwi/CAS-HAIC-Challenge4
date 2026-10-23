"""Seal already-extracted pages after checking their source-file linkage."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sourcepack import seal_pack

seal_pack(ROOT)
print("Vorbereiteter Quellenbestand mit Prüfsummen versehen.")
