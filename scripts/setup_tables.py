#!/usr/bin/env python3
"""
Warehouse Bot — Setup Google Sheets structure (v1.1)

Run once (or anytime to re-apply headers/format):
  python scripts/setup_tables.py

What it does:
- Ensures worksheets exist
- Writes headers
- Freezes header row
- Formats header row
- Sets up reference sheets (Контрагенты, Места, Пользователи)
"""

from __future__ import annotations

import sys
from pathlib import Path
import logging
from typing import List

import gspread
from google.oauth2.service_account import Credentials

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("setup_tables")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ======== V1.1 HEADERS ========

# Warehouse movements (main)
MOVEMENTS_SHEET_NAME = "Движения"
MOVEMENTS_HEADERS: List[str] = [
    "Дата",                 # A
    "Время",                # B
    "Тип",                  # C (Приёмка/Выдача)
    "Контрагент/Место",     # D
    "Operation_ID",         # E
    "№ позиции",            # F
    "Количество",           # G
    "Комментарий позиции",  # H
    "Фото 1",               # I
    "Фото 2",               # J
    "Фото 3",               # K
    "Фото 4",               # L
    "Фото 5",               # M
    "Общий комментарий",    # N
    "Сотрудник",            # O
    "Статус",               # P
]

# Reference: Counterparties
COUNTERPARTIES_SHEET_NAME = "Контрагенты"
COUNTERPARTIES_HEADERS: List[str] = [
    "ID",           # A
    "Название RU",  # B
    "Название TH",  # C
    "Тип",          # D (supplier/customer)
    "Активен",      # E (TRUE/FALSE)
]

# Reference: Places
PLACES_SHEET_NAME = "Места"
PLACES_HEADERS: List[str] = [
    "ID",           # A
    "Название RU",  # B
    "Название TH",  # C
    "Зона",         # D
    "Активен",      # E (TRUE/FALSE)
]

# Reference: Users
USERS_SHEET_NAME = "Пользователи"
USERS_HEADERS: List[str] = [
    "Telegram ID",       # A
    "Username",          # B
    "Имя",               # C
    "Складской учёт",    # D (TRUE/FALSE)
    "Документы K York",  # E (TRUE/FALSE)
    "Грузы",             # F (TRUE/FALSE)
    "Накладные",         # G (TRUE/FALSE)
    "Админ",             # H (TRUE/FALSE)
    "Активен",           # I (TRUE/FALSE)
]

# Vehicles (incoming/outgoing cargo) - 10 photos!
VEHICLES_SHEET_NAME = "Грузы"
VEHICLES_HEADERS: List[str] = [
    "Дата",        # A
    "Время",       # B
    "Тип",         # C (Въезд/Выезд)
    "Машина/ID",   # D
    "Фото 1",      # E
    "Фото 2",      # F
    "Фото 3",      # G
    "Фото 4",      # H
    "Фото 5",      # I
    "Фото 6",      # J
    "Фото 7",      # K
    "Фото 8",      # L
    "Фото 9",      # M
    "Фото 10",     # N
    "Комментарий", # O
    "Сотрудник",   # P
]

# K York documents
DOCS_SHEET_NAME = "Документы"
DOCS_HEADERS: List[str] = [
    "Дата",          # A
    "Время",         # B
    "Тип документа", # C
    "Контрагент",    # D
    "Фото 1",        # E
    "Фото 2",        # F
    "Фото 3",        # G
    "Фото 4",        # H
    "Фото 5",        # I
    "Комментарий",   # J
    "Сотрудник",     # K
    "Номер",         # L
    "Статус",        # M
]

# Supplier invoices
INVOICES_SHEET_NAME = "Накладные"
INVOICES_HEADERS: List[str] = [
    "Дата",            # A
    "Файл",            # B
    "Ссылка",          # C
    "Комментарий",     # D
    "Сотрудник",       # E
    "Номер накладной", # F
    "Поставщик",       # G
    "Статус",          # H
]

# New products template
NEW_PRODUCTS_TEMPLATE_NAME = "Шаблон"
NEW_PRODUCTS_HEADERS: List[str] = [
    "Время",       # A
    "Сотрудник",   # B
    "Фото 1",      # C
    "Фото 2",      # D
    "Фото 3",      # E
    "Фото 4",      # F
    "Фото 5",      # G
    "Комментарий", # H
    "Тип товара",  # I
    "Название RU", # J
    "Название TH", # K
    "Артикул",     # L
    "Категория",   # M
    "Ед.изм",      # N
    "Статус",      # O
]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _ensure_worksheet(ss: gspread.Spreadsheet, title: str, rows: int, cols: int) -> gspread.Worksheet:
    try:
        ws = ss.worksheet(title)
        return ws
    except gspread.WorksheetNotFound:
        logger.info(f"  Creating worksheet: {title}")
        return ss.add_worksheet(title=title, rows=rows, cols=cols)


def _set_headers_and_format(
    ss: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    headers: List[str],
) -> None:
    col_count = len(headers)

    # Ensure enough columns
    if ws.col_count < col_count:
        ws.resize(cols=col_count)

    # Write headers
    ws.update("A1", [headers])

    # Freeze header row
    ws.freeze(rows=1)

    # Header formatting via Sheets API batchUpdate
    sheet_id = ws._properties["sheetId"]
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        "textFormat": {"bold": True},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {"pixelSize": 32},
                "fields": "pixelSize",
            }
        },
    ]
    ss.batch_update({"requests": requests})


def _add_sample_data_if_empty(ws: gspread.Worksheet, sample_data: List[List[str]]) -> None:
    """Add sample data if sheet has only header row"""
    existing = ws.get_all_values()
    if len(existing) <= 1:
        ws.update("A2", sample_data)
        logger.info(f"    Added {len(sample_data)} sample rows")


def main() -> None:
    print("=" * 50)
    print("📊 WAREHOUSE BOT v1.1 - TABLE SETUP")
    print("=" * 50)
    
    gc = _get_client()
    logger.info("✅ Connected to Google Sheets\n")

    # ===== Warehouse Main Sheet =====
    logger.info("📦 WAREHOUSE_MAIN...")
    ss_main = gc.open_by_key(config.WAREHOUSE_MAIN_SHEET_ID)
    
    # Movements
    ws_mov = _ensure_worksheet(ss_main, MOVEMENTS_SHEET_NAME, rows=2000, cols=len(MOVEMENTS_HEADERS))
    _set_headers_and_format(ss_main, ws_mov, MOVEMENTS_HEADERS)
    logger.info(f"  ✅ {MOVEMENTS_SHEET_NAME}")
    
    # Counterparties
    ws_cp = _ensure_worksheet(ss_main, COUNTERPARTIES_SHEET_NAME, rows=100, cols=len(COUNTERPARTIES_HEADERS))
    _set_headers_and_format(ss_main, ws_cp, COUNTERPARTIES_HEADERS)
    _add_sample_data_if_empty(ws_cp, [
        ["1", "K York", "เค ยอร์ค", "supplier", "TRUE"],
        ["2", "Другой поставщик", "ผู้จำหน่ายอื่น", "supplier", "TRUE"],
    ])
    logger.info(f"  ✅ {COUNTERPARTIES_SHEET_NAME}")
    
    # Places
    ws_pl = _ensure_worksheet(ss_main, PLACES_SHEET_NAME, rows=100, cols=len(PLACES_HEADERS))
    _set_headers_and_format(ss_main, ws_pl, PLACES_HEADERS)
    _add_sample_data_if_empty(ws_pl, [
        ["1", "Склад А", "โกดัง A", "Основной", "TRUE"],
        ["2", "Объект 1", "ไซต์ 1", "Стройка", "TRUE"],
    ])
    logger.info(f"  ✅ {PLACES_SHEET_NAME}")
    
    # Users
    ws_usr = _ensure_worksheet(ss_main, USERS_SHEET_NAME, rows=50, cols=len(USERS_HEADERS))
    _set_headers_and_format(ss_main, ws_usr, USERS_HEADERS)
    logger.info(f"  ✅ {USERS_SHEET_NAME}")
    logger.info(f"     ⚠️  Добавь пользователей!")

    # ===== Vehicles Sheet =====
    logger.info("\n🚛 INCOMING_VEHICLES...")
    ss_vehicles = gc.open_by_key(config.INCOMING_VEHICLES_SHEET_ID)
    ws_veh = _ensure_worksheet(ss_vehicles, VEHICLES_SHEET_NAME, rows=2000, cols=len(VEHICLES_HEADERS))
    _set_headers_and_format(ss_vehicles, ws_veh, VEHICLES_HEADERS)
    logger.info(f"  ✅ {VEHICLES_SHEET_NAME} (10 фото)")

    # ===== K York Documents =====
    logger.info("\n📄 K_YORK_DOCUMENTS...")
    ss_docs = gc.open_by_key(config.K_YORK_DOCUMENTS_SHEET_ID)
    ws_docs = _ensure_worksheet(ss_docs, DOCS_SHEET_NAME, rows=2000, cols=len(DOCS_HEADERS))
    _set_headers_and_format(ss_docs, ws_docs, DOCS_HEADERS)
    logger.info(f"  ✅ {DOCS_SHEET_NAME}")

    # ===== Supplier Invoices =====
    logger.info("\n📋 SUPPLIER_INVOICES...")
    ss_inv = gc.open_by_key(config.SUPPLIER_INVOICES_SHEET_ID)
    ws_inv = _ensure_worksheet(ss_inv, INVOICES_SHEET_NAME, rows=2000, cols=len(INVOICES_HEADERS))
    _set_headers_and_format(ss_inv, ws_inv, INVOICES_HEADERS)
    logger.info(f"  ✅ {INVOICES_SHEET_NAME}")

    # ===== New Products =====
    logger.info("\n📦 NEW_PRODUCTS...")
    ss_np = gc.open_by_key(config.NEW_PRODUCTS_SHEET_ID)
    ws_np = _ensure_worksheet(ss_np, NEW_PRODUCTS_TEMPLATE_NAME, rows=100, cols=len(NEW_PRODUCTS_HEADERS))
    _set_headers_and_format(ss_np, ws_np, NEW_PRODUCTS_HEADERS)
    logger.info(f"  ✅ {NEW_PRODUCTS_TEMPLATE_NAME}")

    print("\n" + "=" * 50)
    print("✅ ALL TABLES CONFIGURED!")
    print("=" * 50)
    print("\n⚠️  ВАЖНО:")
    print("   Добавь пользователей в лист 'Пользователи'")
    print("   Telegram ID: 341518922, Username: serg")


if __name__ == "__main__":
    main()
