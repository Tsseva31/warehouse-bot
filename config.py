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
if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and not Path(GOOGLE_SERVICE_ACCOUNT_FILE).exists():
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    try:
        # Чистим строку от возможных проблемных символов
        # Убираем переносы строк, лишние пробелы, экранирование
        sa_json_clean = sa_json.strip()
        
        # Если JSON содержит экранированные переносы строк - заменяем на реальные
        if '\\n' in sa_json_clean:
            sa_json_clean = sa_json_clean.replace('\\n', '\n')
        
        # Пробуем распарсить как JSON (для валидации)
        sa_dict = json.loads(sa_json_clean)
        
        # Записываем валидный JSON в файл
        with open(GOOGLE_SERVICE_ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sa_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created {GOOGLE_SERVICE_ACCOUNT_FILE} from environment variable")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"   First 200 chars of JSON: {sa_json[:200]}")
        raise RuntimeError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    except Exception as e:
        print(f"❌ Error creating service account file: {e}")
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
