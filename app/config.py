import os

## TODO(06 May): can be removed?  (CX: if removed, local DB cannot find right)
class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://username:password@localhost:5432/aquastock"
    UPLOAD_FOLDER = "uploads/fish_images"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
URL_MAP_PATH = BASE_DIR / "url_map.json"

## FIXME: not efficient for run-time memory
with open(URL_MAP_PATH, "r") as f:
    URL_MAP = json.load(f)
