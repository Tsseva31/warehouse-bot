#!/usr/bin/env python3
"""
Warehouse Bot â€” Setup Google Sheets structure (v1.1)

Run once (or anytime to re-apply headers/format):
  python scripts/setup_tables.py

What it does:
- Ensures worksheets exist
- Writes headers
- Freezes header row
- Formats header row
- Sets up reference sheets (ÐšÐ¾Ð½Ñ‚Ñ€Ð°Ð³ÐµÐ½Ñ‚Ñ‹, ÐœÐµÑÑ‚Ð°, ÐŸÐ¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»Ð¸)
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
MOVEMENTS_SHEET_NAME = "Ð”Ð²Ð¸Ð¶ÐµÐ½Ð¸Ñ"
MOVEMENTS_HEADERS: List[str] = [
    "Ð”Ð°Ñ‚Ð°",                 # A
    "Ð’Ñ€ÐµÐ¼Ñ",                # B
    "Ð¢Ð¸Ð¿",                  # C (ÐŸÑ€Ð¸Ñ‘Ð¼ÐºÐ°/Ð’Ñ‹Ð´Ð°Ñ‡Ð°)
    "ÐšÐ¾Ð½Ñ‚Ñ€Ð°Ð³ÐµÐ½Ñ‚/ÐœÐµÑÑ‚Ð¾",     # D
    "Operation_ID",         # E
    "â„– Ð¿Ð¾Ð·Ð¸Ñ†Ð¸Ð¸",            # F
    "ÐšÐ¾Ð»Ð¸Ñ‡ÐµÑÑ‚Ð²Ð¾",           # G
    "ÐšÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹ Ð¿Ð¾Ð·Ð¸Ñ†Ð¸Ð¸",  # H
    "Ð¤Ð¾Ñ‚Ð¾ 1",               # I
    "Ð¤Ð¾Ñ‚Ð¾ 2",               # J
    "Ð¤Ð¾Ñ‚Ð¾ 3",               # K
    "Ð¤Ð¾Ñ‚Ð¾ 4",               # L
    "Ð¤Ð¾Ñ‚Ð¾ 5",               # M
    "ÐžÐ±Ñ‰Ð¸Ð¹ ÐºÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹",    # N
    "Ð¡Ð¾Ñ‚Ñ€ÑƒÐ´Ð½Ð¸Ðº",            # O
    "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ",               # P
]

# Reference: Counterparties
COUNTERPARTIES_SHEET_NAME = "ÐšÐ¾Ð½Ñ‚Ñ€Ð°Ð³ÐµÐ½Ñ‚Ñ‹"
COUNTERPARTIES_HEADERS: List[str] = [
    "ID",           # A
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ RU",  # B
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ TH",  # C
    "Ð¢Ð¸Ð¿",          # D (supplier/customer)
    "ÐÐºÑ‚Ð¸Ð²ÐµÐ½",      # E (TRUE/FALSE)
]

# Reference: Places
PLACES_SHEET_NAME = "ÐœÐµÑÑ‚Ð°"
PLACES_HEADERS: List[str] = [
    "ID",           # A
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ RU",  # B
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ TH",  # C
    "Ð—Ð¾Ð½Ð°",         # D
    "ÐÐºÑ‚Ð¸Ð²ÐµÐ½",      # E (TRUE/FALSE)
]

# Reference: Users
USERS_SHEET_NAME = "ÐŸÐ¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»Ð¸"
USERS_HEADERS: List[str] = [
    "Telegram ID",       # A
    "Username",          # B
    "Ð˜Ð¼Ñ",               # C
    "Ð¡ÐºÐ»Ð°Ð´ÑÐºÐ¾Ð¹ ÑƒÑ‡Ñ‘Ñ‚",    # D (TRUE/FALSE)
    "Ð”Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ñ‹ K York",  # E (TRUE/FALSE)
    "Ð“Ñ€ÑƒÐ·Ñ‹",             # F (TRUE/FALSE)
    "ÐÐ°ÐºÐ»Ð°Ð´Ð½Ñ‹Ðµ",         # G (TRUE/FALSE)
    "ÐÐ´Ð¼Ð¸Ð½",             # H (TRUE/FALSE)
    "ÐÐºÑ‚Ð¸Ð²ÐµÐ½",           # I (TRUE/FALSE)
]

# Vehicles (incoming/outgoing cargo) - 10 photos!
VEHICLES_SHEET_NAME = "Ð“Ñ€ÑƒÐ·Ñ‹"
VEHICLES_HEADERS: List[str] = [
    "Ð”Ð°Ñ‚Ð°",        # A
    "Ð’Ñ€ÐµÐ¼Ñ",       # B
    "Ð¢Ð¸Ð¿",         # C (Ð’ÑŠÐµÐ·Ð´/Ð’Ñ‹ÐµÐ·Ð´)
    "ÐœÐ°ÑˆÐ¸Ð½Ð°/ID",   # D
    "Ð¤Ð¾Ñ‚Ð¾ 1",      # E
    "Ð¤Ð¾Ñ‚Ð¾ 2",      # F
    "Ð¤Ð¾Ñ‚Ð¾ 3",      # G
    "Ð¤Ð¾Ñ‚Ð¾ 4",      # H
    "Ð¤Ð¾Ñ‚Ð¾ 5",      # I
    "Ð¤Ð¾Ñ‚Ð¾ 6",      # J
    "Ð¤Ð¾Ñ‚Ð¾ 7",      # K
    "Ð¤Ð¾Ñ‚Ð¾ 8",      # L
    "Ð¤Ð¾Ñ‚Ð¾ 9",      # M
    "Ð¤Ð¾Ñ‚Ð¾ 10",     # N
    "ÐšÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹", # O
    "Ð¡Ð¾Ñ‚Ñ€ÑƒÐ´Ð½Ð¸Ðº",   # P
]

# K York documents
DOCS_SHEET_NAME = "Ð”Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ñ‹"
DOCS_HEADERS: List[str] = [
    "Ð”Ð°Ñ‚Ð°",          # A
    "Ð’Ñ€ÐµÐ¼Ñ",         # B
    "Ð¢Ð¸Ð¿ Ð´Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ð°", # C
    "ÐšÐ¾Ð½Ñ‚Ñ€Ð°Ð³ÐµÐ½Ñ‚",    # D
    "Ð¤Ð¾Ñ‚Ð¾ 1",        # E
    "Ð¤Ð¾Ñ‚Ð¾ 2",        # F
    "Ð¤Ð¾Ñ‚Ð¾ 3",        # G
    "Ð¤Ð¾Ñ‚Ð¾ 4",        # H
    "Ð¤Ð¾Ñ‚Ð¾ 5",        # I
    "ÐšÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹",   # J
    "Ð¡Ð¾Ñ‚Ñ€ÑƒÐ´Ð½Ð¸Ðº",     # K
    "ÐÐ¾Ð¼ÐµÑ€",         # L
    "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ",        # M
]

# Supplier invoices
INVOICES_SHEET_NAME = "ÐÐ°ÐºÐ»Ð°Ð´Ð½Ñ‹Ðµ"
INVOICES_HEADERS: List[str] = [
    "Ð”Ð°Ñ‚Ð°",            # A
    "Ð¤Ð°Ð¹Ð»",            # B
    "Ð¡ÑÑ‹Ð»ÐºÐ°",          # C
    "ÐšÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹",     # D
    "Ð¡Ð¾Ñ‚Ñ€ÑƒÐ´Ð½Ð¸Ðº",       # E
    "ÐÐ¾Ð¼ÐµÑ€ Ð½Ð°ÐºÐ»Ð°Ð´Ð½Ð¾Ð¹", # F
    "ÐŸÐ¾ÑÑ‚Ð°Ð²Ñ‰Ð¸Ðº",       # G
    "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ",          # H
]

# New products template
NEW_PRODUCTS_TEMPLATE_NAME = "Ð¨Ð°Ð±Ð»Ð¾Ð½"
NEW_PRODUCTS_HEADERS: List[str] = [
    "Ð’Ñ€ÐµÐ¼Ñ",       # A
    "Ð¡Ð¾Ñ‚Ñ€ÑƒÐ´Ð½Ð¸Ðº",   # B
    "Ð¤Ð¾Ñ‚Ð¾ 1",      # C
    "Ð¤Ð¾Ñ‚Ð¾ 2",      # D
    "Ð¤Ð¾Ñ‚Ð¾ 3",      # E
    "Ð¤Ð¾Ñ‚Ð¾ 4",      # F
    "Ð¤Ð¾Ñ‚Ð¾ 5",      # G
    "ÐšÐ¾Ð¼Ð¼ÐµÐ½Ñ‚Ð°Ñ€Ð¸Ð¹", # H
    "Ð¢Ð¸Ð¿ Ñ‚Ð¾Ð²Ð°Ñ€Ð°",  # I
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ RU", # J
    "ÐÐ°Ð·Ð²Ð°Ð½Ð¸Ðµ TH", # K
    "ÐÑ€Ñ‚Ð¸ÐºÑƒÐ»",     # L
    "ÐšÐ°Ñ‚ÐµÐ³Ð¾Ñ€Ð¸Ñ",   # M
    "Ð•Ð´.Ð¸Ð·Ð¼",      # N
    "Ð¡Ñ‚Ð°Ñ‚ÑƒÑ",      # O
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
    print("ðŸ“Š WAREHOUSE BOT v1.1 - TABLE SETUP")
    print("=" * 50)
    
    gc = _get_client()
    logger.info("âœ… Connected to Google Sheets\n")

    # ===== Warehouse Main Sheet =====
    logger.info("ðŸ“¦ WAREHOUSE_MAIN...")
    ss_main = gc.open_by_key(config.WAREHOUSE_MAIN_SHEET_ID)
    
    # Movements
    ws_mov = _ensure_worksheet(ss_main, MOVEMENTS_SHEET_NAME, rows=2000, cols=len(MOVEMENTS_HEADERS))
    _set_headers_and_format(ss_main, ws_mov, MOVEMENTS_HEADERS)
    logger.info(f"  âœ… {MOVEMENTS_SHEET_NAME}")
    
    # Counterparties
    ws_cp = _ensure_worksheet(ss_main, COUNTERPARTIES_SHEET_NAME, rows=100, cols=len(COUNTERPARTIES_HEADERS))
    _set_headers_and_format(ss_main, ws_cp, COUNTERPARTIES_HEADERS)
    _add_sample_data_if_empty(ws_cp, [
        ["1", "K York", "à¹€à¸„ à¸¢à¸­à¸£à¹Œà¸„", "supplier", "TRUE"],
        ["2", "Ð”Ñ€ÑƒÐ³Ð¾Ð¹ Ð¿Ð¾ÑÑ‚Ð°Ð²Ñ‰Ð¸Ðº", "à¸œà¸¹à¹‰à¸ˆà¸³à¸«à¸™à¹ˆà¸²à¸¢à¸­à¸·à¹ˆà¸™", "supplier", "TRUE"],
    ])
    logger.info(f"  âœ… {COUNTERPARTIES_SHEET_NAME}")
    
    # Places
    ws_pl = _ensure_worksheet(ss_main, PLACES_SHEET_NAME, rows=100, cols=len(PLACES_HEADERS))
    _set_headers_and_format(ss_main, ws_pl, PLACES_HEADERS)
    _add_sample_data_if_empty(ws_pl, [
        ["1", "Ð¡ÐºÐ»Ð°Ð´ Ð", "à¹‚à¸à¸”à¸±à¸‡ A", "ÐžÑÐ½Ð¾Ð²Ð½Ð¾Ð¹", "TRUE"],
        ["2", "ÐžÐ±ÑŠÐµÐºÑ‚ 1", "à¹„à¸‹à¸•à¹Œ 1", "Ð¡Ñ‚Ñ€Ð¾Ð¹ÐºÐ°", "TRUE"],
    ])
    logger.info(f"  âœ… {PLACES_SHEET_NAME}")
    
    # Users
    ws_usr = _ensure_worksheet(ss_main, USERS_SHEET_NAME, rows=50, cols=len(USERS_HEADERS))
    _set_headers_and_format(ss_main, ws_usr, USERS_HEADERS)
    logger.info(f"  âœ… {USERS_SHEET_NAME}")
    logger.info(f"     âš ï¸  Ð”Ð¾Ð±Ð°Ð²ÑŒ Ð¿Ð¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»ÐµÐ¹!")

    # ===== Vehicles Sheet =====
    logger.info("\nðŸš› INCOMING_VEHICLES...")
    ss_vehicles = gc.open_by_key(config.INCOMING_VEHICLES_SHEET_ID)
    ws_veh = _ensure_worksheet(ss_vehicles, VEHICLES_SHEET_NAME, rows=2000, cols=len(VEHICLES_HEADERS))
    _set_headers_and_format(ss_vehicles, ws_veh, VEHICLES_HEADERS)
    logger.info(f"  âœ… {VEHICLES_SHEET_NAME} (10 Ñ„Ð¾Ñ‚Ð¾)")

    # ===== K York Documents =====
    logger.info("\nðŸ“„ K_YORK_DOCUMENTS...")
    ss_docs = gc.open_by_key(config.K_YORK_DOCUMENTS_SHEET_ID)
    ws_docs = _ensure_worksheet(ss_docs, DOCS_SHEET_NAME, rows=2000, cols=len(DOCS_HEADERS))
    _set_headers_and_format(ss_docs, ws_docs, DOCS_HEADERS)
    logger.info(f"  âœ… {DOCS_SHEET_NAME}")

    # ===== Supplier Invoices =====
    logger.info("\nðŸ“‹ SUPPLIER_INVOICES...")
    ss_inv = gc.open_by_key(config.SUPPLIER_INVOICES_SHEET_ID)
    ws_inv = _ensure_worksheet(ss_inv, INVOICES_SHEET_NAME, rows=2000, cols=len(INVOICES_HEADERS))
    _set_headers_and_format(ss_inv, ws_inv, INVOICES_HEADERS)
    logger.info(f"  âœ… {INVOICES_SHEET_NAME}")

    # ===== New Products =====
    logger.info("\nðŸ“¦ NEW_PRODUCTS...")
    ss_np = gc.open_by_key(config.NEW_PRODUCTS_SHEET_ID)
    ws_np = _ensure_worksheet(ss_np, NEW_PRODUCTS_TEMPLATE_NAME, rows=100, cols=len(NEW_PRODUCTS_HEADERS))
    _set_headers_and_format(ss_np, ws_np, NEW_PRODUCTS_HEADERS)
    logger.info(f"  âœ… {NEW_PRODUCTS_TEMPLATE_NAME}")

    print("\n" + "=" * 50)
    print("âœ… ALL TABLES CONFIGURED!")
    print("=" * 50)
    print("\nâš ï¸  Ð’ÐÐ–ÐÐž:")
    print("   Ð”Ð¾Ð±Ð°Ð²ÑŒ Ð¿Ð¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»ÐµÐ¹ Ð² Ð»Ð¸ÑÑ‚ 'ÐŸÐ¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»Ð¸'")
    print("   Telegram ID: 341518922, Username: serg")


if __name__ == "__main__":
    main()
