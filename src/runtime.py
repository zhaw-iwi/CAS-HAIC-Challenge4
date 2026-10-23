"""Paid API access is closed by default during offline development."""
import os


def require_live_access():
    if os.environ.get("CHALLENGE_OFFLINE", "1") != "0":
        raise RuntimeError("Offline-Modus: Modell-API-Aufrufe sind gesperrt. Freigabe erfolgt durch die Lehrperson.")
