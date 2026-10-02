import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
DB_FILE = "orders.db"

app = FastAPI()
telegram_app = Application.builder().token(TOKEN).build()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            customer_name TEXT,
            username TEXT,
            service_id TEXT NOT NULL,
            service_name TEXT NOT NULL,
            price TEXT NOT NULL,
            payment_method TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(orders)").fetchall()}
    for name in ("request_details", "phone", "file_id", "file_type", "final_file_id", "final_file_type", "final_file_name"):
        if name not in columns:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {name} TEXT")
    conn.commit()
    conn.close()


init_db()


def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def create_order(user_id, customer_name, username, service_id, service_name, price, request_details, phone):
    conn = get_db()
    now = now_utc()
    cur = conn.execute("""
        INSERT INTO orders (
            order_id, user_id, customer_name, username, service_id, service_name,
            price, payment_method, status, created_at, updated_at,
            request_details, phone, file_id, file_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TEMP", user_id, customer_name, username, service_id, service_name,
        price, None, "Pending Payment", now, now, request_details, phone, None, None
    ))
    row_id = cur.lastrowid
    order_id = f"ORD-{row_id:05d}"
    conn.execute("UPDATE orders SET order_id=? WHERE id=?", (order_id, row_id))
    conn.commit()
    conn.close()
    return order_id


def update_order_payment(order_id, payment_method):
    conn = get_db()
    conn.execute("UPDATE orders SET payment_method=?, status=?, updated_at=? WHERE order_id=?",
                 (payment_method, "Payment Submitted", now_utc(), order_id))
    conn.commit()
    conn.close()


def update_order_status(order_id, status):
    conn = get_db()
    conn.execute("UPDATE orders SET status=?, updated_at=? WHERE order_id=?",
                 (status, now_utc(), order_id))
    conn.commit()
    conn.close()


def update_order_file(order_id, file_id, file_type):
    conn = get_db()
    conn.execute("UPDATE orders SET file_id=?, file_type=?, updated_at=? WHERE order_id=?",
                 (file_id, file_type, now_utc(), order_id))
    conn.commit()
    conn.close()

def update_final_file(order_id, file_id, file_type, file_name=None):
    conn = get_db()
    conn.execute("""
        UPDATE orders
        SET final_file_id=?, final_file_type=?, final_file_name=?, updated_at=?
        WHERE order_id=?
    """, (file_id, file_type, file_name, now_utc(), order_id))
    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
    conn.close()
    return row


def get_recent_orders(limit=20):
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_latest_user_order(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return row


services = {
    "surveying": {"name": "📐 Surveying & Engineering", "price": "500 ETB ", "description": "• Total Station support\n• Coordinate processing\n• Survey data processing\n• Road construction survey support"},
    "excel": {"name": "📊 Excel / KML / Coordinate", "price": "300 ETB ", "description": "• Excel data processing\n• KML / KMZ preparation\n• Coordinate conversion\n• Survey data formatting"},
    "cv": {"name": "📄 Professional CV", "price": "800 ETB", "description": "• Professional CV writing\n• International-style CV\n• Job-focused formatting\n• PDF-ready document"},
    "cover": {"name": "📝 Cover Letter", "price": "200 ETB", "description": "• Professional cover letter\n• Job-specific application\n• Clear and professional writing"},
    "job_support": {"name": "💼 Job Application Support", "price": "300 ETB ", "description": "• Job application assistance\n• CV & Cover Letter review\n• Job-specific application support\n• Professional application guidance"},
    "ai": {"name": "🤖 AI Services", "price": "200 ETB ", "description": "• AI writing\n• Document assistance\n• AI-generated content\n• Professional text improvement"},
    "design": {"name": "🎨 Poster & Design", "price": "350 ETB ", "description": "• Business posters\n• Social media designs\n• Promotional graphics\n• Digital designs"},
    "translation": {"name": "🌐 Translation", "price": "150 ETB ", "description": "• Afaan Oromo ↔ English\n• Afaan Oromo ↔ Amharic\n• English ↔ Amharic"},
}

payment_info = {
    "bank": {"name": "🏦 Bank Transfer", "account": os.environ.get("BANK_ACCOUNT", "Bank account information is not configured yet.")},
    "telebirr": {"name": "📱 Telebirr", "account": os.environ.get("TELEBIRR_NUMBER", "Telebirr number is not configured yet.")},
    "cbe_birr": {"name": "💳 CBE Birr", "account": os.environ.get("CBE_BIRR_NUMBER", "CBE Birr number is not configured yet.")},
    "coopay": {"name": "🟢 Coopay-Ebirr", "account": os.environ.get("COOPAY_NUMBER", "Coopay-Ebirr number is not configured yet.")},
    "awash": {"name": "🟠 Awash", "account": os.environ.get("AWASH_ACCOUNT", "Awash account information is not configured yet.")},
}


# =========================================================
# SUPPORT CHAT
# =========================================================

def support_reply_markup(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("💬 Reply to Customer", callback_data=f"support_reply|{user_id}")]])

async def send_support_text_to_admin(update, context):
    user=update.effective_user; message=update.message
    username=f"@{user.username}" if user.username else "N/A"
    await context.bot.send_message(chat_id=ADMIN_ID, text=(f"🆘 NEW SUPPORT MESSAGE\n\n👤 Customer: {user.full_name}\n🔗 Username: {username}\n🆔 User ID: {user.id}\n\n💬 Message:\n{message.text}"), reply_markup=support_reply_markup(user.id))
    await message.reply_text("✅ Your message has been sent to Engineering Services Support.\n\n💬 Our team will reply here as soon as possible.")

async def send_support_media_to_admin(update, context):
    user=update.effective_user; message=update.message
    username=f"@{user.username}" if user.username else "N/A"
    caption=f"🆘 NEW SUPPORT MESSAGE\n\n👤 Customer: {user.full_name}\n🔗 Username: {username}\n🆔 User ID: {user.id}\n\n📎 Customer sent a file/photo."
    markup=support_reply_markup(user.id)
    if message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=markup)
    elif message.document:
        await context.bot.send_document(chat_id=ADMIN_ID, document=message.document.file_id, caption=caption, reply_markup=markup)
    await message.reply_text("✅ Your file/photo has been sent to Support.\n\n💬 Our team will reply here as soon as possible.")

async def send_admin_support_text(update, context):
    user_id=context.user_data.get("support_reply_to")
    if update.effective_user.id != ADMIN_ID or not user_id: return False
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"💬 Engineering Services Support\n\n{update.message.text}")
        await update.message.reply_text("✅ Reply sent to the customer.")
    except Exception as exc:
        await update.message.reply_text(f"❌ Could not send the reply.\n\n{exc}")
    context.user_data.pop("support_reply_to", None); return True

async def send_admin_support_media(update, context):
    user_id=context.user_data.get("support_reply_to")
    if update.effective_user.id != ADMIN_ID or not user_id: return False
    try:
        if update.message.photo:
            await context.bot.send_photo(chat_id=int(user_id), photo=update.message.photo[-1].file_id, caption="💬 Engineering Services Support")
        elif update.message.document:
            await context.bot.send_document(chat_id=int(user_id), document=update.message.document.file_id, caption="💬 Engineering Services Support")
        await update.message.reply_text("✅ File/photo sent to the customer.")
    except Exception as exc:
        await update.message.reply_text(f"❌ Could not send the file/photo.\n\n{exc}")
    context.user_data.pop("support_reply_to", None); return True

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 Surveying", callback_data="service_surveying"), InlineKeyboardButton("📊 Excel / KML", callback_data="service_excel")],
        [InlineKeyboardButton("📄 CV & Cover Letter", callback_data="cv_menu")],
        [InlineKeyboardButton("🤖 AI Services", callback_data="service_ai"), InlineKeyboardButton("🎨 Design", callback_data="service_design")],
        [InlineKeyboardButton("🌐 Translation", callback_data="service_translation"), InlineKeyboardButton("💳 Payment", callback_data="payment")],
        [InlineKeyboardButton("📦 Order Status", callback_data="status_help")],
        [InlineKeyboardButton("📞 Support", callback_data="support")],
    ])


def cv_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Professional CV — 800 ETB", callback_data="service_cv")],
        [InlineKeyboardButton("📝 Cover Letter — 200 ETB", callback_data="service_cover")],
        [InlineKeyboardButton("💼 Job Application Support — 300 ETB ", callback_data="service_job_support")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
    ])


def payment_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank")],
        [InlineKeyboardButton("📱 Telebirr", callback_data="payment_telebirr")],
        [InlineKeyboardButton("💳 CBE Birr", callback_data="payment_cbe_birr")],
        [InlineKeyboardButton("🟢 Coopay-Ebirr", callback_data="payment_coopay")],
        [InlineKeyboardButton("🟠 Awash", callback_data="payment_awash")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu")],
    ])


def file_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Skip File", callback_data="skip_file")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
    ])


def payment_after_request_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Choose Payment", callback_data="payment")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\nProfessional digital & engineering services.\n\n👇 Choose a service:",
        reply_markup=main_menu(),
    )


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 Our Services\n\n"
        "📐 Surveying & Engineering — 500 ETB \n"
        "📊 Excel / KML / Coordinate — 300 ETB \n"
        "📄 Professional CV — 800 ETB\n"
        "📝 Cover Letter — 200 ETB \n"
        "💼 Job Application Support — 300 ETB \n"
        "🤖 AI Services — 200 ETB \n"
        "🎨 Poster & Design — 350 ETB \n"
        "🌐 Translation — 150 ETB \n\n👇 Choose a service:",
        reply_markup=main_menu(),
    )


# =========================================================
# CUSTOMER ORDER STATUS
# =========================================================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args:
        order_id = context.args[0].strip().upper()
        order = get_order(order_id)
        if not order:
            await update.message.reply_text("❌ Order not found.\n\nExample:\n/status ORD-00001")
            return
        if order["user_id"] != user_id and user_id != ADMIN_ID:
            await update.message.reply_text("⛔ You are not authorized to view this order.")
            return
    else:
        order = get_latest_user_order(user_id)
        if not order:
            await update.message.reply_text("📦 You don't have any orders yet.\n\nUse /start to create a new order.")
            return

    await update.message.reply_text(
        "📦 ORDER STATUS\n\n"
        f"🆔 Order ID: {order['order_id']}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {order['payment_method'] or 'Not selected'}\n"
        f"📌 Status: {order['status']}\n"
        f"📎 File: {'Attached' if order['file_id'] else 'No file'}\n"
        f"📅 Created: {order['created_at']}\n"
        f"🔄 Updated: {order['updated_at']}\n\n"
        "🔄 Check again anytime with /status."
    )


async def show_service(query, context, service_id):
    service = services[service_id]
    context.user_data.clear()
    context.user_data["pending_service_id"] = service_id
    context.user_data["request_stage"] = "details"
    await query.edit_message_text(
        f"{service['name']}\n\n💰 Price: {service['price']}\n\n{service['description']}\n\n"
        "📝 Step 1 of 3\n\nPlease describe what you need.\n\n"
        'Example:\n"I need an Excel file from my survey coordinates"\n'
        'or\n"I need a professional CV for a surveyor job."',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Services", callback_data="services_menu")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        ]),
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text.strip()
    stage = context.user_data.get("request_stage")

    if await send_admin_support_text(update, context):
        return
    if stage == "support":
        await send_support_text_to_admin(update, context)
        return

    if stage == "details":
        context.user_data["request_details"] = text
        context.user_data["request_stage"] = "phone"
        await message.reply_text("📱 Step 2 of 3\n\nPlease send your phone number.\n\nExample: 09XXXXXXXX")
        return

    if stage == "phone":
        if len(text) < 7:
            await message.reply_text("⚠️ Please enter a valid phone number.")
            return
        service_id = context.user_data.get("pending_service_id")
        request_details = context.user_data.get("request_details", "")
        if not service_id or service_id not in services:
            context.user_data.clear()
            await message.reply_text("❌ Session expired.\n\nPlease use /start and choose a service again.")
            return
        service = services[service_id]
        user = update.effective_user
        order_id = create_order(user.id, user.full_name, user.username or "", service_id, service["name"], service["price"], request_details, text)
        context.user_data.update({"order_id": order_id, "service_id": service_id, "request_stage": "file"})
        await message.reply_text(
            "📎 Step 3 of 3\n\nDo you have a file related to your request?\n\n"
            "You can send:\n• PDF\n• Word document\n• Excel file\n• Image\n• KML/KMZ\n• Other project files\n\nIf you don't have a file, tap Skip File.",
            reply_markup=file_menu(),
        )
        return

    await message.reply_text("Please choose a service from the menu.", reply_markup=main_menu())


async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    order_id = context.user_data.get("order_id")
    stage = context.user_data.get("request_stage")

    # Admin final-work delivery: send the finished file directly to the customer.
    final_order_id = context.user_data.get("final_work_order_id")
    if update.effective_user.id == ADMIN_ID and final_order_id:
        order = get_order(final_order_id)
        if not order:
            context.user_data.pop("final_work_order_id", None)
            await message.reply_text("❌ Order not found.")
            return

        file_id = None
        file_type = None
        file_name = None
        if message.document:
            file_id = message.document.file_id
            file_type = "document"
            file_name = message.document.file_name or "Final_Work"
        elif message.photo:
            file_id = message.photo[-1].file_id
            file_type = "photo"
            file_name = "Final_Work_Photo"

        if not file_id:
            await message.reply_text("⚠️ Please send the final work as a document or photo.")
            return

        try:
            if file_type == "document":
                await context.bot.send_document(
                    chat_id=order["user_id"],
                    document=file_id,
                    caption=(
                        "🎉 YOUR ORDER IS COMPLETED!\n\n"
                        f"🆔 Order ID: {final_order_id}\n"
                        f"🛠 Service: {order['service_name']}\n\n"
                        "📎 Your final work is attached above.\n"
                        "Thank you for using Engineering Services. 🙏"
                    ),
                )
            else:
                await context.bot.send_photo(
                    chat_id=order["user_id"],
                    photo=file_id,
                    caption=(
                        "🎉 YOUR ORDER IS COMPLETED!\n\n"
                        f"🆔 Order ID: {final_order_id}\n"
                        f"🛠 Service: {order['service_name']}\n\n"
                        "📎 Your final work is attached above.\n"
                        "Thank you for using Engineering Services. 🙏"
                    ),
                )
            update_final_file(final_order_id, file_id, file_type, file_name)
            update_order_status(final_order_id, "Completed")
            context.user_data.pop("final_work_order_id", None)
            await message.reply_text(
                "✅ Final work delivered successfully!\n\n"
                f"🆔 Order ID: {final_order_id}\n"
                "📌 Status: Completed\n"
                "👤 Customer has received the file."
            )
        except Exception as exc:
            await message.reply_text(f"❌ Could not deliver the final work.\n\n{exc}")
        return

    if await send_admin_support_media(update, context):
        return
    if stage == "support":
        await send_support_media_to_admin(update, context)
        return

    if stage == "file":
        if not order_id:
            await message.reply_text("❌ Order session not found.\n\nPlease use /start again.")
            return
        order = get_order(order_id)
        if not order:
            await message.reply_text("❌ Order not found.\n\nPlease use /start again.")
            return

        file_id = None
        file_type = None
        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "photo"
        elif message.document:
            file_id = message.document.file_id
            file_type = "document"

        if not file_id:
            await message.reply_text("⚠️ Please send a photo or document.")
            return

        update_order_file(order_id, file_id, file_type)
        context.user_data["request_stage"] = None
        caption = (
            "📥 NEW SERVICE REQUEST FILE\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"👤 Customer: {order['customer_name']}\n"
            f"🔗 Username: @{order['username'] or 'N/A'}\n"
            f"📱 Phone: {order['phone'] or 'N/A'}\n"
            f"🛠 Service: {order['service_name']}\n"
            f"💰 Price: {order['price']}\n\n"
            f"📝 Request:\n{order['request_details'] or 'N/A'}"
        )
        if message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption)
        else:
            await context.bot.send_document(chat_id=ADMIN_ID, document=file_id, caption=caption)
        await message.reply_text(
            f"✅ Your project file has been received.\n\n🆔 Order ID: {order_id}\n\nNow choose your payment method:",
            reply_markup=payment_after_request_menu(),
        )
        return

    await receipt_handler(update, context)


async def skip_file(query, context):
    order_id = context.user_data.get("order_id")
    if not order_id:
        await query.answer("Order not found.", show_alert=True)
        return
    context.user_data["request_stage"] = None
    await query.edit_message_text(
        f"✅ Request information completed.\n\n🆔 Order ID: {order_id}\n\nNow choose your payment method:",
        reply_markup=payment_after_request_menu(),
    )


async def show_payment(query, context, payment_method):
    order_id = context.user_data.get("order_id")
    if not order_id:
        await query.answer("Please choose a service first.", show_alert=True)
        return
    order = get_order(order_id)
    if not order:
        await query.answer("Order not found.", show_alert=True)
        return

    info = payment_info[payment_method]
    update_order_payment(order_id, payment_method)
    context.user_data["payment_method"] = payment_method
    context.user_data["request_stage"] = "receipt"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Send Receipt", callback_data="receipt_info")],
        [InlineKeyboardButton("💳 Change Payment Method", callback_data="payment")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
    ])
    await query.edit_message_text(
        f"{info['name']}\n\n🆔 Order ID: {order_id}\n🛠 Service: {order['service_name']}\n💰 Price: {order['price']}\n\n"
        f"💳 Payment Information:\n{info['account']}\n\n"
        "📸 After payment, send your payment receipt here as a photo or document.\n\nYour receipt will be reviewed by our team.",
        reply_markup=keyboard,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        context.user_data.clear()
        await query.edit_message_text("👋 Welcome to Engineering Services!\n\n👇 Choose a service:", reply_markup=main_menu())
        return

    if data == "services_menu":
        context.user_data.clear()
        await query.edit_message_text(
            "🛠 Our Services\n\n"
            "📐 Surveying & Engineering — 500 ETB irraa\n"
            "📊 Excel / KML / Coordinate — 300 ETB irraa\n"
            "📄 Professional CV — 800 ETB\n"
            "📝 Cover Letter — 200 ETB\n"
            "💼 Job Application Support — 300 ETB irraa\n"
            "🤖 AI Services — 200 ETB \n"
            "🎨 Poster & Design — 350 ETB \n"
            "🌐 Translation — 150 ETB \n\n👇 Choose a service:",
            reply_markup=main_menu(),
        )
        return

    if data == "status_help":
        await query.edit_message_text(
            "📦 ORDER STATUS\n\nTo check your latest order, send:\n\n/status\n\nTo check a specific order, send:\n\n/status ORD-00001",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]]),
        )
        return

    if data == "cv_menu":
        await query.edit_message_text("📄 CV & Career Services\n\nChoose a service:", reply_markup=cv_menu())
        return

    if data == "payment":
        if not context.user_data.get("order_id"):
            await query.answer("Please choose a service first.", show_alert=True)
            return
        await query.edit_message_text("💳 Choose your payment method:", reply_markup=payment_menu())
        return

    if data == "receipt_info":
        if not context.user_data.get("order_id"):
            await query.answer("Please choose a service first.", show_alert=True)
            return
        context.user_data["request_stage"] = "receipt"
        await query.edit_message_text("📸 Please send your payment receipt now.\n\nYou can send it as a photo or document.")
        return

    if data == "skip_file":
        await skip_file(query, context)
        return

    if data == "support":
        context.user_data["request_stage"] = "support"
        await query.edit_message_text("🆘 Engineering Services Support\n\nPlease type your question or problem below.\n\nYou can also send a photo or document if it helps explain the problem.\n\n💬 Your message will be sent directly to our Support team.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]]))
        return

    if data.startswith("support_reply|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("Not authorized.", show_alert=True); return
        customer_id=data.split("|",1)[1]
        context.user_data["support_reply_to"]=customer_id
        await query.message.reply_text(f"💬 Reply Mode\n\n👤 Customer ID: {customer_id}\n\nType your reply now.\nYou can also send a photo or document.")
        return

    if data.startswith("send_final|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("Not authorized.", show_alert=True)
            return
        order_id = data.split("|", 1)[1]
        order = get_order(order_id)
        if not order:
            await query.answer("Order not found.", show_alert=True)
            return
        if order["status"] not in ("In Progress", "Payment Submitted"):
            await query.answer("This order is not ready for final delivery.", show_alert=True)
            return
        context.user_data["final_work_order_id"] = order_id
        await query.message.reply_text(
            "📤 SEND FINAL WORK\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"👤 Customer: {order['customer_name']}\n"
            f"🛠 Service: {order['service_name']}\n\n"
            "Now send the finished file as PDF, Word, Excel, KML/KMZ, ZIP, or an image.\n\n"
            "The bot will deliver it directly to the customer and mark the order Completed."
        )
        return

    if data.startswith("service_"):
        service_id = data.replace("service_", "", 1)
        if service_id in services:
            await show_service(query, context, service_id)
        return

    if data.startswith("payment_"):
        payment_method = data.replace("payment_", "", 1)
        if payment_method in payment_info:
            await show_payment(query, context, payment_method)
        return

    if data.startswith("approve|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("Not authorized.", show_alert=True)
            return
        order_id = data.split("|", 1)[1]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("❌ Order not found.")
            return
        update_order_status(order_id, "In Progress")
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 Send Final Work", callback_data=f"send_final|{order_id}")
            ]])
        )
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ Payment Approved!\n\n"
                f"🆔 Order ID: {order_id}\n"
                f"🛠 Service: {order['service_name']}\n\n"
                "Your order is now being processed.\n"
                f"Check your order anytime with:\n/status {order_id}\n\n"
                "Thank you for using Engineering Services."
            ),
        )
        return

    if data.startswith("reject|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("Not authorized.", show_alert=True)
            return
        order_id = data.split("|", 1)[1]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("❌ Order not found.")
            return
        update_order_status(order_id, "Payment Rejected")
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ Payment receipt rejected.\n\n"
                f"🆔 Order ID: {order_id}\n\n"
                "Please make sure the receipt is clear and resend it."
            ),
        )
        return


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("order_id")
    if not order_id:
        await update.message.reply_text("⚠️ Please choose a service first.")
        return

    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.\n\nPlease start again with /start.")
        return

    payment_method = order["payment_method"]
    if not payment_method:
        await update.message.reply_text("⚠️ Please choose a payment method first.")
        return

    update_order_status(order_id, "Payment Submitted")
    caption = (
        "💰 NEW PAYMENT RECEIPT\n\n"
        f"🆔 Order ID: {order_id}\n"
        f"👤 Customer: {order['customer_name']}\n"
        f"🔗 Username: @{order['username'] or 'N/A'}\n"
        f"📱 Phone: {order['phone'] or 'N/A'}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {payment_method}\n\n"
        f"📝 Request:\n{order['request_details'] or 'N/A'}\n\n"
        "📌 Status: Payment Submitted"
    )
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve|{order_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject|{order_id}"),
    ]])

    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=markup)
    elif update.message.document:
        await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=caption, reply_markup=markup)

    await update.message.reply_text(
        f"✅ Receipt received successfully!\n\n🆔 Order ID: {order_id}\n⏳ Your payment is being reviewed.\n\nYou will receive a confirmation after approval."
    )


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    orders = get_recent_orders(20)
    if not orders:
        await update.message.reply_text("📦 No orders found.")
        return
    text = "📦 Recent Orders\n\n"
    for order in orders:
        text += (
            f"🆔 {order['order_id']}\n"
            f"👤 {order['customer_name']}\n"
            f"📱 {order['phone'] or 'N/A'}\n"
            f"🛠 {order['service_name']}\n"
            f"💰 {order['price']}\n"
            f"💳 {order['payment_method'] or 'Not selected'}\n"
            f"📌 {order['status']}\n"
            f"📎 {'Yes' if order['file_id'] else 'No'}\n"
            f"📅 {order['created_at']}\n\n"
        )
    await update.message.reply_text(text)


async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage:\n/order ORD-00001")
        return
    order_id = context.args[0].strip().upper()
    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return
    await update.message.reply_text(
        "📦 Order Details\n\n"
        f"🆔 {order['order_id']}\n"
        f"👤 {order['customer_name']}\n"
        f"🔗 @{order['username'] or 'N/A'}\n"
        f"📱 Phone: {order['phone'] or 'N/A'}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {order['payment_method'] or 'Not selected'}\n"
        f"📌 Status: {order['status']}\n"
        f"📎 {'File attached' if order['file_id'] else 'No file'}\n\n"
        f"📝 Request Details:\n{order['request_details'] or 'N/A'}\n\n"
        f"📅 Created: {order['created_at']}\n"
        f"🔄 Updated: {order['updated_at']}"
    , reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("📤 Send Final Work", callback_data=f"send_final|{order_id}")
    ]]) if order["status"] == "In Progress" else None)


async def complete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage:\n/complete ORD-00001")
        return
    order_id = context.args[0].strip().upper()
    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return
    update_order_status(order_id, "Completed")
    await update.message.reply_text(f"✅ Order completed.\n\n🆔 Order ID: {order_id}\n📌 Status: Completed")
    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "🎉 Your order has been completed!\n\n"
                f"🆔 Order ID: {order_id}\n"
                f"🛠 Service: {order['service_name']}\n"
                "📌 Status: Completed\n\nThank you for using Engineering Services."
            ),
        )
    except Exception as exc:
        print(f"Customer notification failed: {exc}")


# =========================================================
# TELEGRAM HANDLERS
# =========================================================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("services", services_command))
telegram_app.add_handler(CommandHandler("orders", orders_command))
telegram_app.add_handler(CommandHandler("order", order_command))
telegram_app.add_handler(CommandHandler("status", status_command))
telegram_app.add_handler(CommandHandler("complete", complete_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))
telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, file_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))


@app.get("/")
async def root():
    return {"status": "Engineering Services Bot is running"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    print("Telegram update received")
    print(f"Update ID: {update.update_id}")
    await telegram_app.process_update(update)
    print("Telegram update processed successfully")
    return {"ok": True}


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        print("ERROR: RENDER_EXTERNAL_URL is missing!")
        return
    webhook_url = f"{base_url.rstrip('/')}/telegram"
    print(f"Setting Telegram webhook: {webhook_url}")
    await telegram_app.bot.delete_webhook(drop_pending_updates=False)
    await telegram_app.bot.set_webhook(url=webhook_url)
    info = await telegram_app.bot.get_webhook_info()
    print(f"Webhook URL: {info.url}")
    print(f"Pending updates: {info.pending_update_count}")
    print("Telegram webhook set successfully!")


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()
