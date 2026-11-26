import json
import os
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

if service_account_json:
    credential_info = json.loads(service_account_json)
    credential = credentials.Certificate(credential_info)
else:
    key_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    key_path = Path(key_path)

    if not key_path.is_absolute():
        key_path = BASE_DIR / key_path

    credential = credentials.Certificate(str(key_path))

if not firebase_admin._apps:
    firebase_admin.initialize_app(credential)

db = firestore.client()
