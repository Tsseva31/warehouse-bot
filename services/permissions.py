# -*- coding: utf-8 -*-
"""
Permissions service - user access control
Warehouse Bot v1.2

Исправлена обработка UTF-8 для корректного отображения русского и тайского текста.
"""

import logging
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)

# Column name mapping: Russian -> internal key
COLUMN_MAPPING = {
    "Telegram ID": "telegram_id",
    "Username": "username",
    "Имя": "name",
    "Складской учёт": "warehouse",
    "Складской учет": "warehouse",  # Alternative spelling
    "Документы K York": "documents",
    "Грузы": "vehicles",
    "Накладные": "invoices",
    "Админ": "admin",
    "Активен": "active",
    "Название RU": "name_ru",
    "Название TH": "name_th",
    "Тип": "type",
    "Зона": "zone",
}


def _normalize_row(row):
    """Normalize row dict to use both original and mapped keys"""
    normalized = {}
    for key, value in row.items():
        # Приводим ключи и значения к str с явной обработкой UTF-8
        key_str = str(key) if key is not None else ""
        value_str = str(value) if value is not None else ""
        normalized[key_str] = value_str
        if key_str in COLUMN_MAPPING:
            normalized[COLUMN_MAPPING[key_str]] = value_str
    return normalized


class PermissionsManager:
    def __init__(self):
        self.users = {}
        self.counterparties = []
        self.places = []
        self.last_update = None
    
    def _load_all(self):
        from services.sheets_handler import sheets_handler
        
        logger.info("Loading reference data...")
        
        users_rows = sheets_handler.get_users()
        users_map = {}
        
        for r in users_rows:
            normalized = _normalize_row(r)
            
            # Get Telegram ID from various possible column names
            tid = (
                normalized.get("telegram_id") or
                normalized.get("Telegram ID") or
                normalized.get("TelegramID") or
                ""
            )
            
            # Преобразуем в строку и проверяем что это число
            tid_str = str(tid).strip()
            if not tid_str or not tid_str.isdigit():
                logger.warning(f"Invalid Telegram ID: {tid} (row: {r})")
                continue
            tid = tid_str
            
            # Check if user is active
            active = normalized.get("active", normalized.get("Активен", True))
            if active is False:
                logger.info(f"User {tid} is inactive, skipping")
                continue
                
            users_map[str(tid)] = normalized
            logger.debug(f"Loaded user: {tid} -> {normalized.get('username', 'unknown')}")

        self.users = users_map
        
        # Load counterparties
        counterparties_raw = sheets_handler.get_counterparties()
        self.counterparties = [_normalize_row(c) for c in counterparties_raw]
        
        # Load places
        places_raw = sheets_handler.get_places()
        self.places = [_normalize_row(p) for p in places_raw]
        
        self.last_update = datetime.now()
        
        logger.info(
            f"Loaded: {len(self.users)} users, "
            f"{len(self.counterparties)} counterparties, "
            f"{len(self.places)} places"
        )
        
        # Debug: show loaded users
        for tid, user in self.users.items():
            logger.info(f"  User {tid}: {user.get('username')} | warehouse={user.get('warehouse')} | admin={user.get('admin')}")
    
    def refresh_if_needed(self):
        """Refresh cache if TTL expired"""
        if self.last_update is None:
            self._load_all()
            return
        
        elapsed = datetime.now() - self.last_update
        if elapsed > timedelta(minutes=config.CACHE_REFRESH_MINUTES):
            self._load_all()
    
    def force_refresh(self):
        """Force cache refresh (for /reload command)"""
        self._load_all()
        return {
            "counterparties": len(self.counterparties),
            "places": len(self.places),
            "users": len(self.users),
        }
    
    def get_user(self, telegram_id):
        """Get user by Telegram ID"""
        self.refresh_if_needed()
        return self.users.get(str(telegram_id))
    
    def is_registered(self, telegram_id):
        """Check if user is registered"""
        return self.get_user(telegram_id) is not None
    
    def can_access_warehouse(self, telegram_id):
        """Check warehouse access permission"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        return bool(user.get("warehouse"))
    
    def can_access_documents(self, telegram_id):
        """Check documents access permission"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        return bool(user.get("documents"))
    
    def can_access_vehicles(self, telegram_id):
        """Check vehicles access permission"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        return bool(user.get("vehicles"))
    
    def can_access_invoices(self, telegram_id):
        """Check invoices access permission"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        return bool(user.get("invoices"))
    
    def is_admin(self, telegram_id):
        """Check if user is admin"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        username = (user.get("username") or user.get("Username") or "").lower()
        admin_flag = user.get("admin") or user.get("Админ")
        return username == config.ADMIN_USERNAME.lower() or bool(admin_flag)
    
    def get_username(self, telegram_id):
        """Get username for display"""
        user = self.get_user(telegram_id)
        if not user:
            return "unknown"
        return user.get("username") or user.get("Username") or "unknown"
    
    def get_user_display_name(self, telegram_id):
        """Get display name (Имя or username)"""
        user = self.get_user(telegram_id)
        if not user:
            return "unknown"
        return user.get("name") or user.get("Имя") or user.get("username") or user.get("Username") or "unknown"
    
    def get_counterparties(self):
        """Get list of active counterparties"""
        self.refresh_if_needed()
        return self.counterparties
    
    def get_places(self):
        """Get list of active places"""
        self.refresh_if_needed()
        return self.places
    
    def get_available_menu_items(self, telegram_id):
        user = self.get_user(telegram_id)
        if not user:
            return []
        
        items = []
        
        # MVP: только Приёмка, Выдача, Грузы
        if user.get("warehouse"):
            items.extend(["receipt", "issue"])
            # items.append("new_product")  # TODO: v1.3
        
        # if user.get("documents"):  # TODO: v1.3
        #     items.append("documents")
        
        if user.get("vehicles"):
            items.append("vehicles")
        
        # if user.get("invoices"):  # TODO: v1.3
        #     items.append("invoices")
        
        # items.append("history")  # TODO: v1.3
        
        return items


# Global instance
permissions = PermissionsManager()
