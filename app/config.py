from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
URL_MAP_PATH = BASE_DIR / "url_map.json"

## FIXME: not efficient for run-time memory
with open(URL_MAP_PATH, "r") as f:
    URL_MAP = json.load(f)
