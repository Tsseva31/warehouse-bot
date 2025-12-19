#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warehouse Bot v1.2 - Fixed UTF-8"""
import logging
from pathlib import Path
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
import config
from config import validate_config
from services.permissions import permissions
from utils.localization import (
    MENU, MSG, BTN, PRODUCT_TYPES, DOCUMENT_TYPES, VEHICLE_OPS,
    HISTORY_FILTERS, HISTORY_PERIODS, get_qty_buttons,
    format_operation_summary, format_position_summary,
)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
# States
(MAIN_MENU, SELECT_COUNTERPARTY, SELECT_PLACE, POSITION_PHOTOS, POSITION_QTY,
 OPERATION_SUMMARY, OPERATION_GENERAL_COMMENT, NEW_PRODUCT_PHOTOS, NEW_PRODUCT_COMMENT,
 NEW_PRODUCT_TYPE, DOC_TYPE, DOC_PHOTOS, DOC_COUNTERPARTY, DOC_COMMENT,
 VEHICLE_OP_TYPE, VEHICLE_ID, VEHICLE_PHOTOS, VEHICLE_COMMENT,
 INVOICE_COMMENT, HISTORY_FILTER, HISTORY_PERIOD) = range(21)

def build_main_menu(tid):
    items = permissions.get_available_menu_items(tid)
    buttons, row = [], []
    for item in items:
        if item in MENU:
            row.append(MENU[item])
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row: buttons.append(row)
    buttons.append([MENU["help"]])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def build_keyboard(items, columns=2, add_cancel=True):
    buttons, row = [], []
    for item in items:
        if item == "---":
            if row: buttons.append(row); row = []
            continue
        row.append(item)
        if len(row) == columns: buttons.append(row); row = []
    if row: buttons.append(row)
    if add_cancel: buttons.append([BTN["cancel"]])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def build_qty_keyboard():
    buttons = get_qty_buttons()
    buttons.append([BTN["cancel"]])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def build_photo_keyboard():
    return ReplyKeyboardMarkup([[BTN["photo_done"]], [BTN["cancel"]]], resize_keyboard=True)

def _cleanup_temp_photos(context):
    temp = context.user_data.get('temp_photos', [])
    if 'current_position' in context.user_data:
        temp.extend(context.user_data['current_position'].get('temp_photos', []))
    for pos in context.user_data.get('positions', []):
        temp.extend(pos.get('temp_photos', []))
    for p in temp:
        try: Path(p).unlink()
        except: pass

def _safe_buttons(items, prefix=""):
    buttons = []
    for item in items:
        name = item.get('name_ru', item.get('Название RU', str(item))) if isinstance(item, dict) else str(item)
        buttons.append(f"{prefix} {name}" if prefix else name)
    return buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _cleanup_temp_photos(context)
    context.user_data.clear()
    if not permissions.is_registered(user_id):
        await update.message.reply_text(MSG["unknown_user"], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    user_name = permissions.get_user_display_name(user_id)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    await update.message.reply_text(
        f"👋 *{user_name}*\n🤖 v1.2 | 🕐 {now}\n{MSG['welcome']}",
        parse_mode='Markdown', reply_markup=build_main_menu(user_id))
    return MAIN_MENU

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.is_registered(user_id):
        await update.message.reply_text(MSG["unknown_user"])
        return ConversationHandler.END
    _cleanup_temp_photos(context)
    context.user_data.clear()
    await update.message.reply_text(MSG["welcome"], reply_markup=build_main_menu(user_id))
    return MAIN_MENU

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.is_registered(user_id):
        await update.message.reply_text(MSG["unknown_user"])
        return
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    username = permissions.get_username(user_id)
    await update.message.reply_text(
        f"🤖 *Статус / สถานะ*\n✅ OK\n🕐 {now}\n👤 {username}\nv1.2",
        parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _cleanup_temp_photos(context)
    context.user_data.clear()
    await update.message.reply_text(MSG["operation_cancelled"], reply_markup=build_main_menu(user_id))
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if text == MENU.get("help"):
        return await show_help(update, context)
    if text == MENU.get("receipt"):
        if not permissions.can_access_warehouse(user_id):
            await update.message.reply_text(MSG["access_denied"])
            return MAIN_MENU
        return await start_receipt(update, context)
    elif text == MENU.get("issue"):
        if not permissions.can_access_warehouse(user_id):
            await update.message.reply_text(MSG["access_denied"])
            return MAIN_MENU
        return await start_issue(update, context)
    elif text == MENU.get("new_product"):
        if not permissions.can_access_warehouse(user_id):
            await update.message.reply_text(MSG["access_denied"])
            return MAIN_MENU
        return await start_new_product(update, context)
    elif text == MENU.get("documents"):
        if not permissions.can_access_documents(user_id):
            await update.message.reply_text(MSG["access_denied"])
            return MAIN_MENU
        return await start_documents(update, context)
    elif text == MENU.get("vehicles"):
        if not permissions.can_access_vehicles(user_id):
            await update.message.reply_text(MSG["access_denied"])
            return MAIN_MENU
        return await start_vehicles(update, context)
    elif text == MENU.get("history"):
        return await start_history(update, context)
    await update.message.reply_text(MSG["welcome"], reply_markup=build_main_menu(user_id))
    return MAIN_MENU

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(MSG["help_text"], parse_mode='Markdown', reply_markup=build_main_menu(user_id))
    pdf_path = config.BASE_DIR / "docs" / "instruction.pdf"
    if pdf_path.exists():
        try:
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(document=f, caption=MSG["help_pdf_caption"])
        except: pass
    return MAIN_MENU

# ============================================================
# VEHICLES
# ============================================================
async def start_vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.update({'mode': 'vehicles', 'employee': permissions.get_username(user_id)})
    buttons = list(VEHICLE_OPS.values())
    await update.message.reply_text(
        f"🚛 *Грузы / รถผ่านด่าน*\n{MSG['select_vehicle_op']}",
        parse_mode='Markdown', reply_markup=build_keyboard(buttons, columns=2))
    return VEHICLE_OP_TYPE

async def handle_vehicle_op_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text not in VEHICLE_OPS.values():
        await update.message.reply_text("⚠️ Выберите / เลือก")
        return VEHICLE_OP_TYPE
    context.user_data['vehicle_op_type'] = "Въезд" if "Въезд" in text or "เข้า" in text else "Выезд"
    counterparties = permissions.get_counterparties()
    buttons = [f"🏭 {c.get('name_ru', c.get('Название RU', ''))}" for c in counterparties[:6]]
    buttons.extend([BTN["vehicle_auto"], BTN["vehicle_custom"]])
    await update.message.reply_text(MSG["enter_vehicle_id"], reply_markup=build_keyboard(buttons, columns=2))
    return VEHICLE_ID

async def handle_vehicle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["vehicle_auto"]:
        count = sheets_handler.get_today_vehicle_count()
        context.user_data['vehicle_id'] = f"Машина №{count + 1}"
    elif text == BTN["vehicle_custom"]:
        await update.message.reply_text("✏️ Введите / พิมพ์:", reply_markup=ReplyKeyboardRemove())
        return VEHICLE_ID
    else:
        context.user_data['vehicle_id'] = text.replace("🏭 ", "")
    context.user_data['temp_photos'] = []
    await update.message.reply_text(
        MSG.get('photo_instructions_vehicle', MSG['send_photo_vehicle']),
        reply_markup=build_photo_keyboard())
    return VEHICLE_PHOTOS

async def handle_vehicle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["photo_done"]:
        if not context.user_data['temp_photos']:
            await update.message.reply_text("⚠️ Нужно фото!")
            return VEHICLE_PHOTOS
        await update.message.reply_text(
            MSG.get('ask_final_comment', '💬 Комментарий?'),
            reply_markup=build_keyboard([BTN["add_comment"], BTN["no_comment"]], columns=2))
        return VEHICLE_COMMENT
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fp = config.TEMP_PHOTOS_DIR / f"vehicle_{ts}.jpg"
        await file.download_to_drive(fp)
        context.user_data['temp_photos'].append(str(fp))
        current = len(context.user_data['temp_photos'])
        if current >= config.MAX_PHOTOS_VEHICLE:
            await update.message.reply_text(
                MSG.get('ask_final_comment', '💬 Комментарий?'),
                reply_markup=build_keyboard([BTN["add_comment"], BTN["no_comment"]], columns=2))
            return VEHICLE_COMMENT
        await update.message.reply_text(
            MSG['photo_count'].format(current=current, max=config.MAX_PHOTOS_VEHICLE),
            reply_markup=build_photo_keyboard())
        return VEHICLE_PHOTOS
    await update.message.reply_text(MSG['send_photo_vehicle'])
    return VEHICLE_PHOTOS

async def handle_vehicle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    from services.drive_handler import drive_handler
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["add_comment"]:
        await update.message.reply_text(MSG["enter_comment"], reply_markup=ReplyKeyboardRemove())
        return VEHICLE_COMMENT
    context.user_data['comment'] = "" if text in [BTN["skip"], BTN["no_comment"]] else text[:config.MAX_COMMENT_LENGTH]
    await update.message.reply_text("⏳ Сохранение... / กำลังบันทึก...", reply_markup=ReplyKeyboardRemove())
    try:
        links = drive_handler.upload_vehicle_photos(
            context.user_data['temp_photos'],
            context.user_data['vehicle_id'],
            context.user_data['vehicle_op_type'])
        for tf in context.user_data['temp_photos']:
            try: Path(tf).unlink()
            except: pass
        vehicle_data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': datetime.now().strftime("%H:%M:%S"),
            'op_type': context.user_data['vehicle_op_type'],
            'vehicle_id': context.user_data['vehicle_id'],
            'photos': links,
            'comment': context.user_data.get('comment', ''),
            'employee': context.user_data['employee']
        }
        op_emoji = "🟢" if context.user_data['vehicle_op_type'] == "Въезд" else "🔴"
        if sheets_handler.add_vehicle(vehicle_data):
            await update.message.reply_text(
                f"✅ *{MSG['operation_saved']}*\n{op_emoji} {context.user_data['vehicle_op_type']}\n🚛 {context.user_data['vehicle_id']}",
                parse_mode='Markdown', reply_markup=build_main_menu(user_id))
        else:
            await update.message.reply_text(MSG["error_google"], reply_markup=build_main_menu(user_id))
    except Exception:
        logger.exception("Error saving vehicle")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ============================================================
# INVOICES
# ============================================================
async def handle_document_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.can_access_invoices(user_id): return MAIN_MENU
    document = update.message.document
    file_name = document.file_name
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
    if ext not in ['xlsx', 'xls', 'pdf']: return MAIN_MENU
    context.user_data.update({
        'mode': 'invoice',
        'employee': permissions.get_username(user_id),
        'filename': file_name
    })
    file = await document.get_file()
    fp = config.TEMP_PHOTOS_DIR / file_name
    await file.download_to_drive(fp)
    context.user_data['file_path'] = str(fp)
    await update.message.reply_text(
        f"📄 *Накладная / ใบส่งของ*\n📎 {file_name}\n{MSG.get('ask_final_comment', '💬 Комментарий?')}",
        parse_mode='Markdown', reply_markup=build_keyboard([BTN["add_comment"], BTN["no_comment"]], columns=2))
    return INVOICE_COMMENT

async def handle_invoice_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    from services.drive_handler import drive_handler
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["add_comment"]:
        await update.message.reply_text(MSG["enter_comment"], reply_markup=ReplyKeyboardRemove())
        return INVOICE_COMMENT
    context.user_data['comment'] = "" if text in [BTN["skip"], BTN["no_comment"]] else text[:config.MAX_COMMENT_LENGTH]
    await update.message.reply_text("⏳ Сохранение... / กำลังบันทึก...", reply_markup=ReplyKeyboardRemove())
    try:
        link = drive_handler.upload_invoice(context.user_data['file_path'], context.user_data['filename'])
        try: Path(context.user_data['file_path']).unlink()
        except: pass
        invoice_data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'filename': context.user_data['filename'],
            'file_link': link,
            'comment': context.user_data.get('comment', ''),
            'employee': context.user_data['employee']
        }
        if sheets_handler.add_invoice(invoice_data):
            await update.message.reply_text(f"✅ *{MSG['operation_saved']}*\n📄 {context.user_data['filename']}",
                parse_mode='Markdown', reply_markup=build_main_menu(user_id))
        else:
            await update.message.reply_text(MSG["error_google"], reply_markup=build_main_menu(user_id))
    except Exception:
        logger.exception("Error saving invoice")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ========== RECEIPT / ISSUE ==========
async def start_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.update({
        'mode': 'receipt', 'op_type': 'Приёмка', 'op_emoji': '📥',
        'employee': permissions.get_username(user_id), 'positions': []
    })
    counterparties = permissions.get_counterparties()
    buttons = [f"🏭 {c.get('name_ru', c.get('Название RU', ''))}" for c in counterparties]
    buttons.append(BTN["counterparty_other"])
    await update.message.reply_text(
        f"📥 *Приёмка / รับของ*\n{MSG['select_counterparty']}",
        parse_mode='Markdown', reply_markup=build_keyboard(buttons, columns=1))
    return SELECT_COUNTERPARTY

async def start_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.update({
        'mode': 'issue', 'op_type': 'Выдача', 'op_emoji': '📤',
        'employee': permissions.get_username(user_id), 'positions': []
    })
    places = permissions.get_places()
    buttons = [f"📍 {p.get('name_ru', p.get('Название RU', ''))}" for p in places]
    await update.message.reply_text(
        f"📤 *Выдача / จ่ายของ*\n{MSG['select_place']}",
        parse_mode='Markdown', reply_markup=build_keyboard(buttons, columns=1))
    return SELECT_PLACE

async def handle_counterparty_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["counterparty_other"]:
        await update.message.reply_text("✏️ Введите / พิมพ์:", reply_markup=ReplyKeyboardRemove())
        return SELECT_COUNTERPARTY
    context.user_data['counterparty'] = text.replace("🏭 ", "").replace("📍 ", "")
    return await start_position(update, context)

async def handle_place_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    context.user_data['counterparty'] = text.replace("📍 ", "")
    return await start_position(update, context)

async def start_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pos_num = len(context.user_data.get('positions', [])) + 1
    op_emoji = context.user_data.get('op_emoji', '📦')
    context.user_data['current_position'] = {'number': pos_num, 'photos': [], 'temp_photos': []}
    msg = MSG['photo_instructions'] if pos_num == 1 else MSG['send_photo']
    await update.message.reply_text(
        f"{op_emoji} *Позиция #{pos_num} / รายการ #{pos_num}*\n{msg}",
        parse_mode='Markdown', reply_markup=build_photo_keyboard())
    return POSITION_PHOTOS

async def handle_position_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["photo_done"]: return await ask_quantity(update, context)
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fp = config.TEMP_PHOTOS_DIR / f"photo_{ts}.jpg"
        await file.download_to_drive(fp)
        context.user_data['current_position']['temp_photos'].append(str(fp))
        current = len(context.user_data['current_position']['temp_photos'])
        if current >= config.MAX_PHOTOS_PER_POSITION:
            await update.message.reply_text(MSG['photo_max'])
            return await ask_quantity(update, context)
        await update.message.reply_text(
            MSG['photo_count'].format(current=current, max=config.MAX_PHOTOS_PER_POSITION),
            reply_markup=build_photo_keyboard())
        return POSITION_PHOTOS
    await update.message.reply_text(MSG['send_photo'], reply_markup=build_photo_keyboard())
    return POSITION_PHOTOS

async def ask_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG["select_quantity"], reply_markup=build_qty_keyboard())
    return POSITION_QTY

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == BTN["cancel"]: return await cancel(update, context)
    if 'positions' not in context.user_data or 'current_position' not in context.user_data:
        await update.message.reply_text(
            "⚠️ Сессия устарела. Начните заново.\nเซสชันหมดอายุ กรุณาเริ่มใหม่",
            reply_markup=build_main_menu(user_id))
        context.user_data.clear()
        return MAIN_MENU
    if text == BTN["qty_custom"]:
        await update.message.reply_text(MSG["enter_quantity"], reply_markup=ReplyKeyboardRemove())
        return POSITION_QTY
    try:
        clean = ''.join(c for c in text if c.isdigit())
        if not clean: raise ValueError()
        qty = int(clean)
    except:
        await update.message.reply_text("⚠️ Введите число / ใส่ตัวเลข", reply_markup=build_qty_keyboard())
        return POSITION_QTY
    if qty <= 0 or qty > config.MAX_QUANTITY:
        await update.message.reply_text(f"⚠️ 1-{config.MAX_QUANTITY}")
        return POSITION_QTY
    context.user_data['current_position']['quantity'] = qty
    context.user_data['positions'].append(context.user_data['current_position'].copy())
    pos_count = len(context.user_data['positions'])
    photos_count = len(context.user_data['current_position'].get('temp_photos', []))
    summary = format_position_summary(pos_count, qty, photos_count)
    if pos_count >= config.MAX_POSITIONS_PER_OPERATION:
        await update.message.reply_text(summary, parse_mode='Markdown')
        return await show_operation_summary(update, context)
    await update.message.reply_text(
        summary, parse_mode='Markdown',
        reply_markup=build_keyboard([BTN["next_position"], BTN["finish"]], columns=1))
    return OPERATION_SUMMARY

async def handle_operation_summary_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["next_position"]: return await start_position(update, context)
    if text == BTN["finish"]: return await show_operation_summary(update, context)
    return OPERATION_SUMMARY

async def show_operation_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    summary = format_operation_summary(data['op_type'], data['counterparty'], data['positions'], data['employee'])
    await update.message.reply_text(
        f"{summary}\n{MSG.get('ask_final_comment', '💬 Комментарий?')}",
        parse_mode='Markdown',
        reply_markup=build_keyboard([BTN["add_comment"], BTN["save"]], columns=2))
    return OPERATION_GENERAL_COMMENT

async def handle_general_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["add_comment"]:
        await update.message.reply_text(MSG["enter_comment"], reply_markup=ReplyKeyboardRemove())
        return OPERATION_GENERAL_COMMENT
    if text == BTN["save"]:
        context.user_data['general_comment'] = ""
    else:
        context.user_data['general_comment'] = text[:config.MAX_COMMENT_LENGTH]
    return await save_operation(update, context)

async def save_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    from services.drive_handler import drive_handler
    user_id = update.effective_user.id
    data = context.user_data
    await update.message.reply_text("⏳ Сохранение... / กำลังบันทึก...", reply_markup=ReplyKeyboardRemove())
    try:
        username = data["employee"]
        operation_id = f"OP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{username}"
        for idx, pos in enumerate(data["positions"]):
            photo_links = []
            if pos.get("temp_photos"):
                photo_links = drive_handler.upload_operation_photos(
                    pos["temp_photos"], operation_id, data["op_type"],
                    data.get("counterparty", ""), position_number=pos["number"])
                for tf in pos["temp_photos"]:
                    try: Path(tf).unlink()
                    except: pass
            row = {
                "Дата": datetime.now().strftime("%Y-%m-%d"),
                "Время": datetime.now().strftime("%H:%M:%S"),
                "Тип": data["op_type"],
                "Контрагент/Место": data.get("counterparty", ""),
                "Operation_ID": operation_id,
                "№ позиции": pos["number"],
                "Количество": pos.get("quantity", ""),
                "Комментарий позиции": "",
                "Фото 1": photo_links[0] if len(photo_links) > 0 else "",
                "Фото 2": photo_links[1] if len(photo_links) > 1 else "",
                "Фото 3": photo_links[2] if len(photo_links) > 2 else "",
                "Фото 4": photo_links[3] if len(photo_links) > 3 else "",
                "Фото 5": photo_links[4] if len(photo_links) > 4 else "",
                "Общий комментарий": data.get("general_comment", ""),
                "Сотрудник": username,
                "Статус": "NEW"
            }
            sheets_handler.append_movement(row, is_first_position=(idx == 0))
        await update.message.reply_text(
            f"✅ *Сохранено! / บันทึกแล้ว!*\n🆔 `{operation_id}`\n{data['op_emoji']} {len(data['positions'])} поз.",
            parse_mode="Markdown", reply_markup=build_main_menu(user_id))
    except Exception:
        logger.exception("Error saving operation")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ========== NEW PRODUCT ==========
async def start_new_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.update({
        'mode': 'new_product',
        'employee': permissions.get_username(user_id),
        'temp_photos': []
    })
    await update.message.reply_text(
        f"📦 *Новый товар / สินค้าใหม่*\n{MSG['photo_instructions']}",
        parse_mode='Markdown', reply_markup=build_photo_keyboard())
    return NEW_PRODUCT_PHOTOS

async def handle_new_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["photo_done"]:
        if not context.user_data['temp_photos']:
            await update.message.reply_text("⚠️ Нужно фото! / ต้องมีรูป!")
            return NEW_PRODUCT_PHOTOS
        await update.message.reply_text(
            "📝 *Описание / รายละเอียด:*\nБренд, название, артикул\nยี่ห้อ, ชื่อ, รหัส",
            parse_mode='Markdown', reply_markup=build_keyboard([BTN["cancel"]], add_cancel=False))
        return NEW_PRODUCT_COMMENT
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fp = config.TEMP_PHOTOS_DIR / f"newprod_{ts}.jpg"
        await file.download_to_drive(fp)
        context.user_data['temp_photos'].append(str(fp))
        current = len(context.user_data['temp_photos'])
        if current >= config.MAX_PHOTOS_NEW_PRODUCT:
            await update.message.reply_text("📝 *Описание:*", parse_mode='Markdown',
                reply_markup=build_keyboard([BTN["cancel"]], add_cancel=False))
            return NEW_PRODUCT_COMMENT
        await update.message.reply_text(
            MSG['photo_count'].format(current=current, max=config.MAX_PHOTOS_NEW_PRODUCT),
            reply_markup=build_photo_keyboard())
        return NEW_PRODUCT_PHOTOS
    await update.message.reply_text(MSG['send_photo'])
    return NEW_PRODUCT_PHOTOS

async def handle_new_product_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    context.user_data['comment'] = text[:config.MAX_COMMENT_LENGTH]
    buttons = list(PRODUCT_TYPES.values())
    await update.message.reply_text("📦 Тип / ประเภท:", reply_markup=build_keyboard(buttons, columns=2))
    return NEW_PRODUCT_TYPE

async def handle_new_product_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    from services.drive_handler import drive_handler
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]: return await cancel(update, context)
    if text not in PRODUCT_TYPES.values():
        await update.message.reply_text("⚠️ Выберите / เลือก")
        return NEW_PRODUCT_TYPE
    context.user_data['product_type'] = text
    await update.message.reply_text("⏳ Сохранение... / กำลังบันทึก...", reply_markup=ReplyKeyboardRemove())
    try:
        links = drive_handler.upload_new_product_photos(context.user_data['temp_photos'], context.user_data['employee'], 1)
        for tf in context.user_data['temp_photos']:
            try: Path(tf).unlink()
            except: pass
        product_data = {
            'time': datetime.now().strftime("%H:%M:%S"),
            'employee': context.user_data['employee'],
            'photos': links,
            'comment': context.user_data['comment'],
            'product_type': context.user_data['product_type']
        }
        if sheets_handler.add_new_product(product_data):
            await update.message.reply_text(f"✅ *{MSG['operation_saved']}*\n📦 {text}",
                parse_mode='Markdown', reply_markup=build_main_menu(user_id))
        else:
            await update.message.reply_text(MSG["error_google"], reply_markup=build_main_menu(user_id))
    except Exception:
        logger.exception("Error saving new product")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ========== DOCUMENTS ==========
async def start_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.update({'mode': 'documents', 'employee': permissions.get_username(user_id)})
    buttons = list(DOCUMENT_TYPES.values())
    await update.message.reply_text(
        f"📄 *Документы / เอกสาร*\n{MSG['select_doc_type']}",
        parse_mode='Markdown', reply_markup=build_keyboard(buttons, columns=1))
    return DOC_TYPE

async def handle_doc_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text not in DOCUMENT_TYPES.values():
        await update.message.reply_text("⚠️ Выберите / เลือก")
        return DOC_TYPE
    context.user_data['doc_type'] = text
    context.user_data['temp_photos'] = []
    await update.message.reply_text(MSG['send_photo'], reply_markup=build_photo_keyboard())
    return DOC_PHOTOS

async def handle_doc_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["photo_done"]:
        if not context.user_data['temp_photos']:
            await update.message.reply_text("⚠️ Нужно фото!")
            return DOC_PHOTOS
        counterparties = permissions.get_counterparties()
        buttons = _safe_buttons(counterparties[:6], "🏭")
        buttons.extend([BTN["counterparty_other"], BTN["skip"]])
        await update.message.reply_text(MSG["select_counterparty"], reply_markup=build_keyboard(buttons, columns=1))
        return DOC_COUNTERPARTY
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fp = config.TEMP_PHOTOS_DIR / f"doc_{ts}.jpg"
        await file.download_to_drive(fp)
        context.user_data['temp_photos'].append(str(fp))
        current = len(context.user_data['temp_photos'])
        if current >= config.MAX_PHOTOS_DOCUMENT:
            counterparties = permissions.get_counterparties()
            buttons = [f"🏭 {c.get('name_ru', c.get('Название RU', ''))}" for c in counterparties]
            buttons.extend([BTN["counterparty_other"], BTN["skip"]])
            await update.message.reply_text(MSG["select_counterparty"], reply_markup=build_keyboard(buttons, columns=1))
            return DOC_COUNTERPARTY
        await update.message.reply_text(
            MSG['photo_count'].format(current=current, max=config.MAX_PHOTOS_DOCUMENT),
            reply_markup=build_photo_keyboard())
        return DOC_PHOTOS
    await update.message.reply_text(MSG['send_photo'])
    return DOC_PHOTOS

async def handle_doc_counterparty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["counterparty_other"]:
        await update.message.reply_text("✏️ Введите / พิมพ์:", reply_markup=ReplyKeyboardRemove())
        return DOC_COUNTERPARTY
    context.user_data['counterparty'] = "" if text == BTN["skip"] else text.replace("🏭 ", "")
    await update.message.reply_text(
        MSG.get('ask_final_comment', '💬 Комментарий?'),
        reply_markup=build_keyboard([BTN["add_comment"], BTN["no_comment"]], columns=2))
    return DOC_COMMENT

async def handle_doc_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    from services.drive_handler import drive_handler
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]: return await cancel(update, context)
    if text == BTN["add_comment"]:
        await update.message.reply_text(MSG["enter_comment"], reply_markup=ReplyKeyboardRemove())
        return DOC_COMMENT
    context.user_data['comment'] = "" if text in [BTN["skip"], BTN["no_comment"]] else text[:config.MAX_COMMENT_LENGTH]
    await update.message.reply_text("⏳ Сохранение... / กำลังบันทึก...", reply_markup=ReplyKeyboardRemove())
    try:
        links = drive_handler.upload_document_photos(context.user_data['temp_photos'], context.user_data['doc_type'])
        for tf in context.user_data['temp_photos']:
            try: Path(tf).unlink()
            except: pass
        doc_data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': datetime.now().strftime("%H:%M:%S"),
            'doc_type': context.user_data['doc_type'],
            'counterparty': context.user_data.get('counterparty', ''),
            'photos': links,
            'comment': context.user_data.get('comment', ''),
            'employee': context.user_data['employee']
        }
        if sheets_handler.add_document(doc_data):
            await update.message.reply_text(
                f"✅ *{MSG['operation_saved']}*\n📄 {context.user_data['doc_type']}",
                parse_mode='Markdown', reply_markup=build_main_menu(user_id))
        else:
            await update.message.reply_text(MSG["error_google"], reply_markup=build_main_menu(user_id))
    except Exception:
        logger.exception("Error saving document")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ============================================================
# HISTORY
# ============================================================
async def start_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = list(HISTORY_FILTERS.values())
    await update.message.reply_text(
        f"📊 *{MSG['history_title']}*\n{MSG['select_filter']}",
        parse_mode='Markdown', reply_markup=build_keyboard(buttons, columns=2))
    return HISTORY_FILTER

async def handle_history_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]:
        await update.message.reply_text(MSG["welcome"], reply_markup=build_main_menu(user_id))
        return MAIN_MENU
    filter_key = None
    for k, v in HISTORY_FILTERS.items():
        if v == text: filter_key = k; break
    if not filter_key:
        await update.message.reply_text("⚠️ Выберите / เลือก")
        return HISTORY_FILTER
    context.user_data['history_filter'] = filter_key
    buttons = list(HISTORY_PERIODS.values())
    await update.message.reply_text(MSG["select_period"], reply_markup=build_keyboard(buttons, columns=2))
    return HISTORY_PERIOD

async def handle_history_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.sheets_handler import sheets_handler
    text = update.message.text
    user_id = update.effective_user.id
    if text == BTN["cancel"]:
        await update.message.reply_text(MSG["welcome"], reply_markup=build_main_menu(user_id))
        return MAIN_MENU
    period_key = None
    for k, v in HISTORY_PERIODS.items():
        if v == text: period_key = k; break
    if not period_key:
        await update.message.reply_text("⚠️ Выберите / เลือก")
        return HISTORY_PERIOD
    filter_key = context.user_data.get('history_filter', 'all')
    await update.message.reply_text("⏳ Загрузка... / กำลังโหลด...")
    try:
        records = sheets_handler.get_history(filter_key, period_key, limit=10)
        if not records:
            await update.message.reply_text(MSG["history_empty"], reply_markup=build_main_menu(user_id))
            return MAIN_MENU
        result = f"📊 *{HISTORY_FILTERS.get(filter_key, 'История')}*\n📅 {HISTORY_PERIODS.get(period_key, '')}\n━━━━━━━━━━━━━━━\n"
        for i, rec in enumerate(records, 1):
            result += f"*{i}.* {rec.get('emoji', '📦')} {rec.get('type', '')}\n   📅 {rec.get('date', '')} {rec.get('time', '')}\n"
            if rec.get('details'): result += f"   {rec['details']}\n"
            result += "\n"
        sheet_type = {'receipt': 'warehouse', 'issue': 'warehouse', 'documents': 'documents', 'vehicles': 'vehicles'}.get(filter_key, 'warehouse')
        sheet_url = sheets_handler.get_sheet_url(sheet_type)
        if sheet_url: result += f"━━━━━━━━━━━━━━━\n🔗 [Открыть таблицу / เปิดตาราง]({sheet_url})"
        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=build_main_menu(user_id), disable_web_page_preview=True)
    except Exception:
        logger.exception("History error")
        await update.message.reply_text(MSG["error_generic"], reply_markup=build_main_menu(user_id))
    context.user_data.clear()
    return MAIN_MENU

# ============================================================
# ADMIN
# ============================================================
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.is_admin(user_id):
        await update.message.reply_text(MSG["admin_only"])
        return
    stats = permissions.force_refresh()
    await update.message.reply_text(MSG["cache_updated"].format(**stats), reply_markup=build_main_menu(user_id))

async def cmd_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.is_admin(user_id):
        await update.message.reply_text(MSG["admin_only"])
        return
    count = 0
    for f in config.TEMP_PHOTOS_DIR.glob("*"):
        if f.is_file():
            try: f.unlink(); count += 1
            except: pass
    await update.message.reply_text(MSG["cleanup_done"].format(count=count), reply_markup=build_main_menu(user_id))

async def global_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not permissions.is_registered(user_id):
        await update.message.reply_text(MSG["unknown_user"], reply_markup=ReplyKeyboardRemove())
        return
    _cleanup_temp_photos(context)
    context.user_data.clear()
    user_name = permissions.get_user_display_name(user_id)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    await update.message.reply_text(
        f"👋 *{user_name}*\n🤖 v1.2 | 🕐 {now}\n{MSG['welcome']}",
        parse_mode='Markdown', reply_markup=build_main_menu(user_id))

# ============================================================
# MAIN
# ============================================================
def main():
    errors = validate_config()
    if errors:
        for e in errors: logger.error(f"Config error: {e}")
        return
    for f in config.TEMP_PHOTOS_DIR.glob("*"):
        if f.is_file():
            try: f.unlink()
            except: pass
    docs_dir = config.BASE_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu), MessageHandler(filters.Document.ALL, handle_document_file)],
            SELECT_COUNTERPARTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_counterparty_selection)],
            SELECT_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_place_selection)],
            POSITION_PHOTOS: [MessageHandler(filters.PHOTO, handle_position_photo), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_position_photo)],
            POSITION_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            OPERATION_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_operation_summary_action)],
            OPERATION_GENERAL_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_comment)],
            NEW_PRODUCT_PHOTOS: [MessageHandler(filters.PHOTO, handle_new_product_photo), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_product_photo)],
            NEW_PRODUCT_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_product_comment)],
            NEW_PRODUCT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_product_type)],
            DOC_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_doc_type)],
            DOC_PHOTOS: [MessageHandler(filters.PHOTO, handle_doc_photo), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_doc_photo)],
            DOC_COUNTERPARTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_doc_counterparty)],
            DOC_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_doc_comment)],
            VEHICLE_OP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vehicle_op_type)],
            VEHICLE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vehicle_id)],
            VEHICLE_PHOTOS: [MessageHandler(filters.PHOTO, handle_vehicle_photo), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vehicle_photo)],
            VEHICLE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vehicle_comment)],
            INVOICE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invoice_comment)],
            HISTORY_FILTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_history_filter)],
            HISTORY_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_history_period)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("cancel", cancel), CommandHandler("menu", cmd_menu)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("cleanup", cmd_cleanup))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_document_file))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_fallback))
    logger.info("🚀 Starting Warehouse Bot v1.2...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()