import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "memory.json"


def load_memory():
    with MEMORY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(data):
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)