# -*- coding: utf-8 -*-
"""
Google Sheets handler - read/write layer (Service Account)
Warehouse Bot v1.2

Исправлена обработка UTF-8 для всех значений из таблиц (русский/тайский текст).
"""

from __future__ import annotations

import os
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _env(name, default=None):
    v = os.getenv(name)
    if v is None or v == "":
        if default is None:
            raise RuntimeError(f"Missing required env: {name}")
        return default
    return v


def _to_bool(v):
    """Convert string to boolean, but only for boolean-like strings"""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        # Не конвертируем числовые строки!
        if s.isdigit():
            return v  # Вернуть как есть
        if s in ("true", "yes", "y", "да"):
            return True
        if s in ("false", "no", "n", "нет"):
            return False
    return v


def _to_number(v):
    if not isinstance(v, str):
        return v
    s = str(v).strip()
    if s == "":
        return ""
    try:
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    except Exception:
        pass
    s2 = s.replace(",", ".")
    try:
        return float(s2)
    except Exception:
        return v


def _normalize_cell(v):
    # Сначала пробуем число, потом bool
    v = _to_number(v)
    if not isinstance(v, (int, float)):
        v = _to_bool(v)
    return v


def _safe_str(v):
    if v is None:
        return ""
    return str(v)


@dataclass(frozen=True)
class SheetsConfig:
    spreadsheet_id: str
    users_sheet: str
    counterparties_sheet: str
    places_sheet: str
    movements_sheet: str
    
    vehicles_spreadsheet_id: str = ""
    vehicles_sheet: str = "Грузы"
    
    documents_spreadsheet_id: str = ""
    documents_sheet: str = "Документы"
    
    invoices_spreadsheet_id: str = ""
    invoices_sheet: str = "Накладные"
    
    new_products_spreadsheet_id: str = ""
    new_products_sheet: str = "Шаблон"
    
    refresh_ttl_sec: int = 60


class SheetsHandler:
    def __init__(self, cfg):
        self.cfg = cfg
        self._service = None
        self._cache = {}
        self._cache_ts = {}

    def _get_service(self):
        if self._service is not None:
            return self._service

        sa_file = _env("GOOGLE_SERVICE_ACCOUNT_FILE")
        creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        logger.info("[Sheets] Google Sheets service initialized")
        return self._service

    def _get_values(self, spreadsheet_id, a1_range):
        service = self._get_service()
        try:
            resp = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=a1_range)
                .execute()
            )
            return resp.get("values", []) or []
        except HttpError as e:
            logger.exception("[Sheets] GET failed spreadsheet=%s range=%s: %s", spreadsheet_id, a1_range, e)
            return []

    def _append_values(self, spreadsheet_id, a1_range, rows):
        service = self._get_service()
        body = {"values": rows}
        try:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=a1_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            return True
        except HttpError as e:
            logger.exception("[Sheets] APPEND failed: %s", e)
            return False

    def _read_table_as_dicts(self, spreadsheet_id, sheet_name):
        values = self._get_values(spreadsheet_id, f"{sheet_name}!A1:ZZ")
        if not values:
            logger.warning("[Sheets] %s is empty", sheet_name)
            return []

        header = [str(h).strip() for h in values[0]]
        rows = values[1:]

        out = []
        for r in rows:
            d = {}
            for i, key in enumerate(header):
                if key == "":
                    continue
                cell = r[i] if i < len(r) else ""
                d[key] = _normalize_cell(cell)
            if any(_safe_str(v).strip() != "" for v in d.values()):
                out.append(d)
        return out

    def _cache_get(self, key):
        ts = self._cache_ts.get(key)
        if ts is None:
            return None
        if (time.time() - ts) > self.cfg.refresh_ttl_sec:
            return None
        return self._cache.get(key)

    def _cache_set(self, key, value):
        self._cache[key] = value
        self._cache_ts[key] = time.time()

    def get_users(self):
        cache_key = "users"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._read_table_as_dicts(self.cfg.spreadsheet_id, self.cfg.users_sheet)
        logger.info("[Users] loaded=%d", len(data))
        self._cache_set(cache_key, data)
        return data

    def get_counterparties(self):
        cache_key = "counterparties"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._read_table_as_dicts(self.cfg.spreadsheet_id, self.cfg.counterparties_sheet)

        out = []
        for row in data:
            active = row.get("Активен", row.get("Active", True))
            active = _to_bool(active)
            if active is True:
                out.append(row)

        logger.info("[Counterparties] loaded_active=%d total=%d", len(out), len(data))
        self._cache_set(cache_key, out)
        return out

    def get_places(self):
        cache_key = "places"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._read_table_as_dicts(self.cfg.spreadsheet_id, self.cfg.places_sheet)

        out = []
        for row in data:
            if "Активен" in row or "Active" in row:
                active = row.get("Активен", row.get("Active", True))
                active = _to_bool(active)
                if active is True:
                    out.append(row)
            else:
                out.append(row)

        logger.info("[Places] loaded_active=%d total=%d", len(out), len(data))
        self._cache_set(cache_key, out)
        return out

    def append_movement(self, row, is_first_position=True):
        header_values = self._get_values(self.cfg.spreadsheet_id, f"{self.cfg.movements_sheet}!A1:ZZ")
        if not header_values or not header_values[0]:
            logger.error("Movements sheet has no header row")
            return False

        header = [str(h).strip() for h in header_values[0] if str(h).strip() != ""]
        values_row = [_safe_str(row.get(col, "")) for col in header]

        result = self._append_values(self.cfg.spreadsheet_id, f"{self.cfg.movements_sheet}!A:A", [values_row])
        if result:
            logger.info("[Movements] appended row")
        return result

    def add_vehicle(self, data):
        spreadsheet_id = self.cfg.vehicles_spreadsheet_id or self.cfg.spreadsheet_id
        sheet_name = self.cfg.vehicles_sheet
        
        header_values = self._get_values(spreadsheet_id, f"{sheet_name}!A1:ZZ")
        if not header_values or not header_values[0]:
            logger.error("Vehicles sheet has no header row")
            return False

        header = [str(h).strip() for h in header_values[0] if str(h).strip() != ""]
        
        row_data = {
            "Дата": data.get("date", ""),
            "Время": data.get("time", ""),
            "Тип": data.get("op_type", ""),
            "Машина/ID": data.get("vehicle_id", ""),
            "Комментарий": data.get("comment", ""),
            "Сотрудник": data.get("employee", ""),
        }
        
        photos = data.get("photos", [])
        for i, link in enumerate(photos[:10], 1):
            row_data[f"Фото {i}"] = link
        
        values_row = [_safe_str(row_data.get(col, "")) for col in header]
        return self._append_values(spreadsheet_id, f"{sheet_name}!A:A", [values_row])

    def get_today_vehicle_count(self):
        spreadsheet_id = self.cfg.vehicles_spreadsheet_id or self.cfg.spreadsheet_id
        sheet_name = self.cfg.vehicles_sheet
        
        data = self._read_table_as_dicts(spreadsheet_id, sheet_name)
        today = datetime.now().strftime("%Y-%m-%d")
        
        count = sum(1 for row in data if row.get("Дата", "") == today)
        return count

    def add_document(self, data):
        spreadsheet_id = self.cfg.documents_spreadsheet_id or self.cfg.spreadsheet_id
        sheet_name = self.cfg.documents_sheet
        
        header_values = self._get_values(spreadsheet_id, f"{sheet_name}!A1:ZZ")
        if not header_values or not header_values[0]:
            logger.error("Documents sheet has no header row")
            return False

        header = [str(h).strip() for h in header_values[0] if str(h).strip() != ""]
        
        row_data = {
            "Дата": data.get("date", ""),
            "Время": data.get("time", ""),
            "Тип документа": data.get("doc_type", ""),
            "Контрагент": data.get("counterparty", ""),
            "Комментарий": data.get("comment", ""),
            "Сотрудник": data.get("employee", ""),
        }
        
        photos = data.get("photos", [])
        for i, link in enumerate(photos[:5], 1):
            row_data[f"Фото {i}"] = link
        
        values_row = [_safe_str(row_data.get(col, "")) for col in header]
        return self._append_values(spreadsheet_id, f"{sheet_name}!A:A", [values_row])

    def add_invoice(self, data):
        spreadsheet_id = self.cfg.invoices_spreadsheet_id or self.cfg.spreadsheet_id
        sheet_name = self.cfg.invoices_sheet
        
        header_values = self._get_values(spreadsheet_id, f"{sheet_name}!A1:ZZ")
        if not header_values or not header_values[0]:
            logger.error("Invoices sheet has no header row")
            return False

        header = [str(h).strip() for h in header_values[0] if str(h).strip() != ""]
        
        row_data = {
            "Дата": data.get("date", ""),
            "Файл": data.get("filename", ""),
            "Ссылка": data.get("file_link", ""),
            "Комментарий": data.get("comment", ""),
            "Сотрудник": data.get("employee", ""),
        }
        
        values_row = [_safe_str(row_data.get(col, "")) for col in header]
        return self._append_values(spreadsheet_id, f"{sheet_name}!A:A", [values_row])

    def add_new_product(self, data):
        spreadsheet_id = self.cfg.new_products_spreadsheet_id or self.cfg.spreadsheet_id
        sheet_name = self.cfg.new_products_sheet
        
        header_values = self._get_values(spreadsheet_id, f"{sheet_name}!A1:ZZ")
        if not header_values or not header_values[0]:
            logger.error("New products sheet has no header row")
            return False

        header = [str(h).strip() for h in header_values[0] if str(h).strip() != ""]
        
        row_data = {
            "Время": data.get("time", ""),
            "Сотрудник": data.get("employee", ""),
            "Комментарий": data.get("comment", ""),
            "Тип товара": data.get("product_type", ""),
        }
        
        photos = data.get("photos", [])
        for i, link in enumerate(photos[:5], 1):
            row_data[f"Фото {i}"] = link
        
        values_row = [_safe_str(row_data.get(col, "")) for col in header]
        return self._append_values(spreadsheet_id, f"{sheet_name}!A:A", [values_row])

    def get_history(self, filter_key, period_key, limit=10):
        now = datetime.now()
        if period_key == "today":
            start_date = now.replace(hour=0, minute=0, second=0)
        elif period_key == "yesterday":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            now = now.replace(hour=0, minute=0, second=0)
        elif period_key == "week":
            start_date = now - timedelta(days=7)
        elif period_key == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)

        records = []

        try:
            if filter_key in ("all", "receipt", "issue"):
                movements = self._read_table_as_dicts(self.cfg.spreadsheet_id, self.cfg.movements_sheet)
                for row in movements:
                    op_type = row.get("Тип", "")
                    
                    if filter_key == "receipt" and "Приёмка" not in op_type:
                        continue
                    if filter_key == "issue" and "Выдача" not in op_type:
                        continue
                    
                    emoji = "📥" if "Приёмка" in op_type else "📤"
                    records.append({
                        "type": op_type,
                        "emoji": emoji,
                        "date": row.get("Дата", ""),
                        "time": row.get("Время", ""),
                        "details": f"{row.get('Контрагент/Место', '')} | {row.get('Количество', '')}",
                    })

            if filter_key in ("all", "documents"):
                spreadsheet_id = self.cfg.documents_spreadsheet_id or self.cfg.spreadsheet_id
                docs = self._read_table_as_dicts(spreadsheet_id, self.cfg.documents_sheet)
                for row in docs:
                    records.append({
                        "type": row.get("Тип документа", "Документ"),
                        "emoji": "📄",
                        "date": row.get("Дата", ""),
                        "time": row.get("Время", ""),
                        "details": row.get("Контрагент", ""),
                    })

            if filter_key in ("all", "vehicles"):
                spreadsheet_id = self.cfg.vehicles_spreadsheet_id or self.cfg.spreadsheet_id
                vehicles = self._read_table_as_dicts(spreadsheet_id, self.cfg.vehicles_sheet)
                for row in vehicles:
                    op_type = row.get("Тип", "")
                    emoji = "🟢" if "Въезд" in op_type else "🔴"
                    records.append({
                        "type": op_type,
                        "emoji": emoji,
                        "date": row.get("Дата", ""),
                        "time": row.get("Время", ""),
                        "details": row.get("Машина/ID", ""),
                    })

        except Exception as e:
            logger.exception("Error getting history: %s", e)
            return []

        records.sort(key=lambda x: f"{x.get('date', '')} {x.get('time', '')}", reverse=True)
        return records[:limit]

    def get_sheet_url(self, sheet_type):
        if sheet_type == "warehouse":
            return f"https://docs.google.com/spreadsheets/d/{self.cfg.spreadsheet_id}"
        elif sheet_type == "vehicles":
            sid = self.cfg.vehicles_spreadsheet_id or self.cfg.spreadsheet_id
            return f"https://docs.google.com/spreadsheets/d/{sid}"
        elif sheet_type == "documents":
            sid = self.cfg.documents_spreadsheet_id or self.cfg.spreadsheet_id
            return f"https://docs.google.com/spreadsheets/d/{sid}"
        else:
            return f"https://docs.google.com/spreadsheets/d/{self.cfg.spreadsheet_id}"


def _build_config():
    return SheetsConfig(
        spreadsheet_id=_env("WAREHOUSE_MAIN_SHEET_ID"),
        users_sheet=os.getenv("USERS_SHEET_NAME", "Пользователи"),
        counterparties_sheet=os.getenv("COUNTERPARTIES_SHEET_NAME", "Контрагенты"),
        places_sheet=os.getenv("PLACES_SHEET_NAME", "Места"),
        movements_sheet=os.getenv("MOVEMENTS_SHEET_NAME", "Движения"),
        
        vehicles_spreadsheet_id=os.getenv("INCOMING_VEHICLES_SHEET_ID", ""),
        vehicles_sheet=os.getenv("VEHICLES_SHEET_NAME", "Грузы"),
        
        documents_spreadsheet_id=os.getenv("K_YORK_DOCUMENTS_SHEET_ID", ""),
        documents_sheet=os.getenv("DOCUMENTS_SHEET_NAME", "Документы"),
        
        invoices_spreadsheet_id=os.getenv("SUPPLIER_INVOICES_SHEET_ID", ""),
        invoices_sheet=os.getenv("INVOICES_SHEET_NAME", "Накладные"),
        
        new_products_spreadsheet_id=os.getenv("NEW_PRODUCTS_SHEET_ID", ""),
        new_products_sheet=os.getenv("NEW_PRODUCTS_SHEET_NAME", "Шаблон"),
        
        refresh_ttl_sec=int(os.getenv("SHEETS_REFRESH_TTL_SEC", "60")),
    )


sheets_handler = SheetsHandler(_build_config())
