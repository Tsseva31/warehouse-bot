# -*- coding: utf-8 -*-
"""
Google Drive handler - Shared Drive uploads and folder management
Warehouse Bot v1.2

Исправлена обработка UTF-8 для русских и тайских имён файлов и папок.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import List, Optional

import config
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _mime_for_path(file_path: str) -> str:
    """Get MIME type for file"""
    ext = os.path.splitext(file_path)[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
    }.get(ext, "application/octet-stream")


def _sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    Sanitize filename - remove dangerous characters.
    Полностью поддерживает тайский и русский текст.
    """
    if not name:
        return "unnamed"
    
    name = str(name)  # Явное приведение к строке
    
    # Replace path separators and other dangerous chars
    name = re.sub(r'[/\\:*?"<>|]', '_', name)
    # Replace multiple spaces/underscores
    name = re.sub(r'[\s_]+', '_', name)
    # Trim and limit length
    name = name.strip('_')[:max_length]
    
    return name or "unnamed"


class DriveHandler:
    def __init__(self) -> None:
        self.service = None
        self.drive_id = getattr(config, "SHARED_DRIVE_ID", None)
        if not self.drive_id:
            raise RuntimeError("config.SHARED_DRIVE_ID is required for Shared Drive mode")
        self._connect()

        # Common kwargs for Shared Drive calls
        self._sd_list_kwargs = {
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "corpora": "drive",
            "driveId": self.drive_id,
        }
        self._sd_create_kwargs = {"supportsAllDrives": True}

    def _connect(self) -> None:
        """Connect to Google Drive API"""
        try:
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=SCOPES,
            )
            self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
            logger.info("Connected to Google Drive (Shared Drive mode)")
        except Exception as exc:
            logger.exception("Failed to connect to Google Drive")
            raise

    def _escape_q(self, s: str) -> str:
        """Escape quotes for Drive query strings"""
        return str(s).replace("'", "\\'")

    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        """Get existing folder or create new one inside Shared Drive"""
        try:
            folder_name = str(folder_name)
            safe_name = self._escape_q(folder_name)

            query = (
                f"name='{safe_name}' and '{parent_id}' in parents "
                f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
            results = (
                self.service.files()
                .list(q=query, fields="files(id,name)", **self._sd_list_kwargs)
                .execute()
            )
            files = results.get("files", [])
            if files:
                return files[0]["id"]

            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = (
                self.service.files()
                .create(body=file_metadata, fields="id", **self._sd_create_kwargs)
                .execute()
            )
            folder_id = folder.get("id")
            logger.info(f"Created folder: {folder_name} -> {folder_id}")
            return folder_id

        except Exception as exc:
            logger.exception(f"Error with folder {folder_name}")
            raise

    def upload_file(self, file_path: str, folder_id: str, file_name: Optional[str] = None) -> str:
        """Upload file to Shared Drive folder and return webViewLink"""
        if not file_name:
            file_name = os.path.basename(file_path)

        file_name = str(file_name)

        if not os.path.exists(file_path):
            logger.error(f"[Drive] File not found: {file_path}")
            return ""

        try:
            file_metadata = {"name": file_name, "parents": [folder_id]}
            media = MediaFileUpload(file_path, mimetype=_mime_for_path(file_path))

            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink",
                    **self._sd_create_kwargs,
                )
                .execute()
            )
            link = file.get("webViewLink") or f"https://drive.google.com/file/d/{file.get('id')}/view"
            logger.info(f"[Drive] Uploaded: {file_name} -> {link}")
            return link

        except Exception as exc:
            logger.exception("Error uploading file")
            raise

    # ================================================================
    # WAREHOUSE OPERATIONS
    # ================================================================

    def upload_operation_photos(
        self,
        photos: List[str],
        operation_id: str,
        op_type: str,
        counterparty: str,
        position_number: int = 1,
    ) -> List[str]:
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # Create folder structure
            date_folder = self._get_or_create_folder(today, config.WAREHOUSE_OPERATIONS_FOLDER_ID)
            
            safe_counterparty = _sanitize_filename(counterparty, 20)
            safe_op_type = _sanitize_filename(op_type, 15)
            op_folder_name = f"{operation_id}_{safe_op_type}_{safe_counterparty}"
            op_folder = self._get_or_create_folder(op_folder_name, date_folder)

            links: List[str] = []
            for photo_num, photo_path in enumerate(photos, 1):
                ext = os.path.splitext(photo_path)[1] or ".jpg"
                file_name = f"{operation_id}_P{position_number:02d}_F{photo_num:02d}{ext}"
                links.append(self.upload_file(photo_path, op_folder, file_name))

            return links

        except Exception as exc:
            logger.exception("Error uploading operation photos")
            return []

    # ================================================================
    # NEW PRODUCTS
    # ================================================================

    def upload_new_product_photos(self, photos: List[str], employee: str, product_num: int) -> List[str]:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            date_folder = self._get_or_create_folder(today, config.NEW_PRODUCTS_FOLDER_ID)

            safe_employee = _sanitize_filename(employee, 15)
            timestamp = datetime.now().strftime("%H%M%S")
            product_folder_name = f"{today}_{timestamp}_{safe_employee}"
            product_folder = self._get_or_create_folder(product_folder_name, date_folder)

            links: List[str] = []
            for i, photo_path in enumerate(photos, 1):
                ext = os.path.splitext(photo_path)[1] or ".jpg"
                file_name = f"Photo_{i:02d}{ext}"
                links.append(self.upload_file(photo_path, product_folder, file_name))
            return links

        except Exception as exc:
            logger.exception("Error uploading new product photos")
            return []

    # ================================================================
    # K YORK DOCUMENTS
    # ================================================================

    def upload_document_photos(self, photos: List[str], doc_type: str) -> List[str]:
        try:
            dt = str(doc_type or "").lower()
            if "входящ" in dt or "incoming" in dt or "📥" in (doc_type or ""):
                subfolder = "Incoming"
            else:
                subfolder = "Outgoing"

            month = datetime.now().strftime("%Y-%m")
            type_folder = self._get_or_create_folder(subfolder, config.K_YORK_DOCUMENTS_FOLDER_ID)
            month_folder = self._get_or_create_folder(month, type_folder)

            links: List[str] = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, photo_path in enumerate(photos, 1):
                ext = os.path.splitext(photo_path)[1] or ".jpg"
                file_name = f"Doc_{timestamp}_{i:02d}{ext}"
                links.append(self.upload_file(photo_path, month_folder, file_name))
            return links

        except Exception as exc:
            logger.exception("Error uploading document photos")
            return []

    # ================================================================
    # INCOMING VEHICLES - supports 10 photos
    # ================================================================

    def upload_vehicle_photos(self, photos: List[str], vehicle_id: str, op_type: str) -> List[str]:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            date_folder = self._get_or_create_folder(today, config.INCOMING_VEHICLES_FOLDER_ID)

            safe_vehicle = _sanitize_filename(vehicle_id, 20)
            safe_op = "IN" if "Въезд" in op_type else "OUT"
            timestamp = datetime.now().strftime("%H%M%S")
            vehicle_folder_name = f"{timestamp}_{safe_op}_{safe_vehicle}"
            vehicle_folder = self._get_or_create_folder(vehicle_folder_name, date_folder)

            links: List[str] = []
            for i, photo_path in enumerate(photos, 1):
                ext = os.path.splitext(photo_path)[1] or ".jpg"
                file_name = f"Photo_{i:02d}{ext}"
                links.append(self.upload_file(photo_path, vehicle_folder, file_name))
            return links

        except Exception as exc:
            logger.exception("Error uploading vehicle photos")
            return []

    # ================================================================
    # SUPPLIER INVOICES
    # ================================================================

    def upload_invoice(self, file_path: str, original_name: str) -> str:
        try:
            month = datetime.now().strftime("%Y-%m")
            month_folder = self._get_or_create_folder(month, config.SUPPLIER_INVOICES_FOLDER_ID)
            
            safe_name = _sanitize_filename(original_name, 100)
            return self.upload_file(file_path, month_folder, safe_name)
            
        except Exception as exc:
            logger.exception("Error uploading invoice")
            return ""


# Global instance
drive_handler = DriveHandler()