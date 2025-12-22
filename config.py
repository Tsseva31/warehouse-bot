# -*- coding: utf-8 -*-
"""
Configuration module - loads settings from .env file
Compatible with:
- Google Sheets via Service Account
- Google Drive Shared Drive (supportsAllDrives)
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# ========================================
# Load .env
# ========================================
load_dotenv()

# ========================================
# TELEGRAM
# ========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ========================================
# GOOGLE (Service Account)
# ========================================
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "service-account.json"
)

# ========================================
# Create service account file from environment variable
# ========================================
if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
    import json
    sa_json_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    try:
        # Парсим JSON
        sa_dict = json.loads(sa_json_raw)
        
        # КРИТИЧЕСКИ ВАЖНО: Правильная обработка private_key
        if 'private_key' in sa_dict and isinstance(sa_dict['private_key'], str):
            # Проверяем что там есть
            pk = sa_dict['private_key']
            
            # Если есть литеральные \n (строка "\\n"), заменяем на реальные
            if '\\n' in pk:
                pk = pk.replace('\\n', '\n')
            
            # Если private_key не начинается с "-----BEGIN", значит он в одну строку
            if not pk.startswith('-----BEGIN'):
                # Ищем маркеры и вставляем переносы
                pk = pk.replace('-----BEGIN PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----\n')
                pk = pk.replace('-----END PRIVATE KEY-----', '\n-----END PRIVATE KEY-----\n')
            
            sa_dict['private_key'] = pk
            
            print(f"✅ Processed private_key (length: {len(pk)} chars)")
        
        # Записываем корректный JSON
        with open(GOOGLE_SERVICE_ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sa_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created {GOOGLE_SERVICE_ACCOUNT_FILE} from environment variable")
        
        # Проверяем что файл валидный
        with open(GOOGLE_SERVICE_ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            test = json.load(f)
        print(f"✅ Validated {GOOGLE_SERVICE_ACCOUNT_FILE} - JSON is valid")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"   Position: {e.pos}")
        if hasattr(e, 'pos') and e.pos:
            start = max(0, e.pos - 50)
            end = min(len(sa_json_raw), e.pos + 50)
            print(f"   Context: {sa_json_raw[start:end]}")
        raise RuntimeError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    except Exception as e:
        print(f"❌ Error creating service account file: {e}")
        import traceback
        traceback.print_exc()
        raise

# ========================================
# GOOGLE SHEETS (IDs НЕ МЕНЯТЬ!)
# ========================================
WAREHOUSE_MAIN_SHEET_ID = os.getenv("WAREHOUSE_MAIN_SHEET_ID")
NEW_PRODUCTS_SHEET_ID = os.getenv("NEW_PRODUCTS_SHEET_ID")
K_YORK_DOCUMENTS_SHEET_ID = os.getenv("K_YORK_DOCUMENTS_SHEET_ID")
INCOMING_VEHICLES_SHEET_ID = os.getenv("INCOMING_VEHICLES_SHEET_ID")
SUPPLIER_INVOICES_SHEET_ID = os.getenv("SUPPLIER_INVOICES_SHEET_ID")

# ========================================
# GOOGLE DRIVE — SHARED DRIVE
# ========================================
SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID")

WAREHOUSE_OPERATIONS_FOLDER_ID = os.getenv("WAREHOUSE_OPERATIONS_FOLDER_ID")
NEW_PRODUCTS_FOLDER_ID = os.getenv("NEW_PRODUCTS_FOLDER_ID")
K_YORK_DOCUMENTS_FOLDER_ID = os.getenv("K_YORK_DOCUMENTS_FOLDER_ID")
INCOMING_VEHICLES_FOLDER_ID = os.getenv("INCOMING_VEHICLES_FOLDER_ID")
SUPPLIER_INVOICES_FOLDER_ID = os.getenv("SUPPLIER_INVOICES_FOLDER_ID")

# ========================================
# BOT SETTINGS - v1.1
# ========================================
MAX_PHOTOS_PER_POSITION = int(os.getenv("MAX_PHOTOS_PER_POSITION", 5))
MAX_PHOTOS_NEW_PRODUCT = int(os.getenv("MAX_PHOTOS_NEW_PRODUCT", 5))
MAX_PHOTOS_DOCUMENT = int(os.getenv("MAX_PHOTOS_DOCUMENT", 5))
MAX_PHOTOS_VEHICLE = int(os.getenv("MAX_PHOTOS_VEHICLE", 10))  # Расширено до 10!

MAX_POSITIONS_PER_OPERATION = int(os.getenv("MAX_POSITIONS_PER_OPERATION", 30))
MAX_QUANTITY = int(os.getenv("MAX_QUANTITY", 99999))
MAX_COMMENT_LENGTH = int(os.getenv("MAX_COMMENT_LENGTH", 1000))  # Для длинных диктовок

CACHE_REFRESH_MINUTES = int(os.getenv("CACHE_REFRESH_MINUTES", 30))

# ========================================
# TABLE FORMATTING - v1.1
# ========================================
SEPARATOR_ROWS = 2
SEPARATOR_COLOR = {
    "red": 1.0,
    "green": 0.976,
    "blue": 0.769,
}  # #FFF9C4

# ========================================
# ADMIN
# ========================================
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "serg")

# ========================================
# PATHS
# ========================================
BASE_DIR = Path(__file__).resolve().parent
TEMP_PHOTOS_DIR = BASE_DIR / "temp_photos"
TEMP_PHOTOS_DIR.mkdir(exist_ok=True)

# ========================================
# VALIDATION
# ========================================
def validate_config() -> list[str]:
    """Validate required configuration values"""
    errors: list[str] = []

    # Telegram
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN not set")

    # Service account
    if not GOOGLE_SERVICE_ACCOUNT_FILE:
        errors.append("GOOGLE_SERVICE_ACCOUNT_FILE not set")
    elif not Path(GOOGLE_SERVICE_ACCOUNT_FILE).exists():
        errors.append(f"Service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")

    # Sheets
    sheets = [
        ("WAREHOUSE_MAIN_SHEET_ID", WAREHOUSE_MAIN_SHEET_ID),
        ("NEW_PRODUCTS_SHEET_ID", NEW_PRODUCTS_SHEET_ID),
        ("K_YORK_DOCUMENTS_SHEET_ID", K_YORK_DOCUMENTS_SHEET_ID),
        ("INCOMING_VEHICLES_SHEET_ID", INCOMING_VEHICLES_SHEET_ID),
        ("SUPPLIER_INVOICES_SHEET_ID", SUPPLIER_INVOICES_SHEET_ID),
    ]
    for name, value in sheets:
        if not value:
            errors.append(f"{name} not set")

    # Shared Drive
    if not SHARED_DRIVE_ID:
        errors.append("SHARED_DRIVE_ID not set")

    folders = [
        ("WAREHOUSE_OPERATIONS_FOLDER_ID", WAREHOUSE_OPERATIONS_FOLDER_ID),
        ("NEW_PRODUCTS_FOLDER_ID", NEW_PRODUCTS_FOLDER_ID),
        ("K_YORK_DOCUMENTS_FOLDER_ID", K_YORK_DOCUMENTS_FOLDER_ID),
        ("INCOMING_VEHICLES_FOLDER_ID", INCOMING_VEHICLES_FOLDER_ID),
        ("SUPPLIER_INVOICES_FOLDER_ID", SUPPLIER_INVOICES_FOLDER_ID),
    ]
    for name, value in folders:
        if not value:
            errors.append(f"{name} not set")

    return errors
