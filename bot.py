import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# ENVIRONMENT
# =========================================================

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

app = FastAPI()

telegram_app = Application.builder().token(TOKEN).build()

DB_FILE = "orders.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
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
        """
    )
    conn.commit()
    conn.close()


init_db()


def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def create_order(
    user_id,
    customer_name,
    username,
    service_id,
    service_name,
    price,
):
    conn = get_db()
    now = now_utc()

    cursor = conn.execute(
        """
        INSERT INTO orders (
            order_id, user_id, customer_name, username,
            service_id, service_name, price,
            payment_method, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEMP",
            user_id,
            customer_name,
            username,
            service_id,
            service_name,
            price,
            None,
            "Pending Payment",
            now,
            now,
        ),
    )

    database_id = cursor.lastrowid
    order_id = f"ORD-{database_id:05d}"

    conn.execute(
        "UPDATE orders SET order_id = ? WHERE id = ?",
        (order_id, database_id),
    )

    conn.commit()
    conn.close()
    return order_id


def update_order_payment(order_id, payment_method):
    conn = get_db()
    conn.execute(
        """
        UPDATE orders
        SET payment_method = ?,
            status = ?,
            updated_at = ?
        WHERE order_id = ?
        """,
        (payment_method, "Payment Submitted", now_utc(), order_id),
    )
    conn.commit()
    conn.close()


def update_order_status(order_id, status):
    conn = get_db()
    conn.execute(
        """
        UPDATE orders
        SET status = ?, updated_at = ?
        WHERE order_id = ?
        """,
        (status, now_utc(), order_id),
    )
    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    conn.close()
    return row


def get_recent_orders(limit=20):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT * FROM orders
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


# =========================================================
# SERVICES
# =========================================================

services = {
    "surveying": {
        "name": "📐 Surveying & Engineering",
        "price": "500 ETB irraa",
        "description": (
            "• Total Station support\n"
            "• Coordinate processing\n"
            "• Survey data processing\n"
            "• Road construction survey support"
        ),
    },
    "excel": {
        "name": "📊 Excel / KML / Coordinate",
        "price": "300 ETB irraa",
        "description": (
            "• Excel data processing\n"
            "• KML / KMZ preparation\n"
            "• Coordinate conversion\n"
            "• Survey data formatting"
        ),
    },
    "cv": {
        "name": "📄 Professional CV",
        "price": "800 ETB",
        "description": (
            "• Professional CV writing\n"
            "• International-style CV\n"
            "• Job-focused formatting\n"
            "• PDF-ready document"
        ),
    },
    "cover": {
        "name": "📝 Cover Letter",
        "price": "200 ETB",
        "description": (
            "• Professional cover letter\n"
            "• Job-specific application\n"
            "• Clear and professional writing"
        ),
    },
    "job_support": {
        "name": "💼 Job Application Support",
        "price": "300 ETB irraa",
        "description": (
            "• Job application assistance\n"
            "• CV & Cover Letter review\n"
            "• Job-specific application support\n"
            "• Professional application guidance"
        ),
    },
    "ai": {
        "name": "🤖 AI Services",
        "price": "200 ETB irraa",
        "description": (
            "• AI writing\n"
            "• Document assistance\n"
            "• AI-generated content\n"
            "• Professional text improvement"
        ),
    },
    "design": {
        "name": "🎨 Poster & Design",
        "price": "350 ETB irraa",
        "description": (
            "• Business posters\n"
            "• Social media designs\n"
            "• Promotional graphics\n"
            "• Digital designs"
        ),
    },
    "translation": {
        "name": "🌐 Translation",
        "price": "150 ETB irraa",
        "description": (
            "• Afaan Oromo ↔ English\n"
            "• Afaan Oromo ↔ Amharic\n"
            "• English ↔ Amharic"
        ),
    },
}


# =========================================================
# PAYMENT INFORMATION
# =========================================================

payment_info = {
    "bank": {
        "name": "🏦 Bank Transfer",
        "account": os.environ.get(
            "BANK_ACCOUNT",
            "Bank account information is not configured yet.",
        ),
    },
    "telebirr": {
        "name": "📱 Telebirr",
        "account": os.environ.get(
            "TELEBIRR_NUMBER",
            "Telebirr number is not configured yet.",
        ),
    },
    "cbe_birr": {
        "name": "💳 CBE Birr",
        "account": os.environ.get(
            "CBE_BIRR_NUMBER",
            "CBE Birr number is not configured yet.",
        ),
    },
    "coopay": {
        "name": "🟢 Coopay-Ebirr",
        "account": os.environ.get(
            "COOPAY_NUMBER",
            "Coopay-Ebirr number is not configured yet.",
        ),
    },
    "awash": {
        "name": "🟠 Awash",
        "account": os.environ.get(
            "AWASH_ACCOUNT",
            "Awash account information is not configured yet.",
        ),
    },
}


# =========================================================
# MENUS
# =========================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "📐 Surveying",
                callback_data="service_surveying",
            ),
            InlineKeyboardButton(
                "📊 Excel / KML",
                callback_data="service_excel",
            ),
        ],
        [
            InlineKeyboardButton(
                "📄 CV & Cover Letter",
                callback_data="cv_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                "🤖 AI Services",
                callback_data="service_ai",
            ),
            InlineKeyboardButton(
                "🎨 Design",
                callback_data="service_design",
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Translation",
                callback_data="service_translation",
            ),
            InlineKeyboardButton(
                "💳 Payment",
                callback_data="payment",
            ),
        ],
        [
            InlineKeyboardButton(
                "📞 Support",
                callback_data="support",
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def cv_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "📄 Professional CV — 800 ETB",
                callback_data="service_cv",
            )
        ],
        [
            InlineKeyboardButton(
                "📝 Cover Letter — 200 ETB",
                callback_data="service_cover",
            )
        ],
        [
            InlineKeyboardButton(
                "💼 Job Application Support — 300 ETB irraa",
                callback_data="service_job_support",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="menu",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def payment_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🏦 Bank Transfer",
                callback_data="payment_bank",
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Telebirr",
                callback_data="payment_telebirr",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 CBE Birr",
                callback_data="payment_cbe_birr",
            )
        ],
        [
            InlineKeyboardButton(
                "🟢 Coopay-Ebirr",
                callback_data="payment_coopay",
            )
        ],
        [
            InlineKeyboardButton(
                "🟠 Awash",
                callback_data="payment_awash",
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Main Menu",
                callback_data="menu",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# =========================================================
# COMMANDS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\n"
        "Professional digital & engineering services.\n\n"
        "👇 Choose a service:",
        reply_markup=main_menu(),
    )


async def services_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🛠 Our Services\n\n"
        "📐 Surveying & Engineering — 500 ETB irraa\n"
        "📊 Excel / KML / Coordinate — 300 ETB irraa\n"
        "📄 Professional CV — 800 ETB\n"
        "📝 Cover Letter — 200 ETB\n"
        "💼 Job Application Support — 300 ETB irraa\n"
        "🤖 AI Services — 200 ETB irraa\n"
        "🎨 Poster & Design — 350 ETB irraa\n"
        "🌐 Translation — 150 ETB irraa\n\n"
        "👇 Choose a service:",
        reply_markup=main_menu(),
    )


# =========================================================
# SERVICE FLOW
# =========================================================

async def show_service(query, context, service_id):
    service = services[service_id]
    user = query.from_user

    order_id = create_order(
        user.id,
        user.full_name,
        user.username or "",
        service_id,
        service["name"],
        service["price"],
    )

    context.user_data["order_id"] = order_id
    context.user_data["service_id"] = service_id

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Choose Payment",
                callback_data="payment",
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Main Menu",
                callback_data="menu",
            )
        ],
    ]

    await query.edit_message_text(
        f"{service['name']}\n\n"
        f"💰 Price: {service['price']}\n\n"
        f"{service['description']}\n\n"
        f"🆔 Order ID: {order_id}\n\n"
        "👇 Continue to payment:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_payment(query, context, payment_method):
    order_id = context.user_data.get("order_id")

    if not order_id:
        await query.answer(
            "Please choose a service first.",
            show_alert=True,
        )
        return

    order = get_order(order_id)

    if not order:
        await query.answer(
            "Order not found.",
            show_alert=True,
        )
        return

    info = payment_info[payment_method]

    update_order_payment(order_id, payment_method)
    context.user_data["payment_method"] = payment_method

    keyboard = [
        [
            InlineKeyboardButton(
                "📸 Send Receipt",
                callback_data="receipt_info",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Change Payment Method",
                callback_data="payment",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="menu",
            )
        ],
    ]

    await query.edit_message_text(
        f"{info['name']}\n\n"
        f"🆔 Order ID: {order_id}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n\n"
        f"💳 Payment Information:\n"
        f"{info['account']}\n\n"
        "📸 After payment, send your payment receipt "
        "here as a photo or document.\n\n"
        "Your receipt will be reviewed by our team.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu":
        await query.edit_message_text(
            "👋 Welcome to Engineering Services!\n\n"
            "👇 Choose a service:",
            reply_markup=main_menu(),
        )
        return

    if data == "cv_menu":
        await query.edit_message_text(
            "📄 CV & Career Services\n\n"
            "Choose a service:",
            reply_markup=cv_menu(),
        )
        return

    if data == "payment":
        await query.edit_message_text(
            "💳 Choose your payment method:",
            reply_markup=payment_menu(),
        )
        return

    if data == "receipt_info":
        await query.edit_message_text(
            "📸 Please send your payment receipt now.\n\n"
            "You can send it as a photo or document."
        )
        return

    if data == "support":
        await query.edit_message_text(
            "📞 Support\n\n"
            "Please contact the Engineering Services team "
            "for assistance."
        )
        return

    if data.startswith("service_"):
        service_id = data.replace("service_", "", 1)

        if service_id in services:
            await show_service(
                query,
                context,
                service_id,
            )
        return

    if data.startswith("payment_"):
        payment_method = data.replace("payment_", "", 1)

        if payment_method in payment_info:
            await show_payment(
                query,
                context,
                payment_method,
            )
        return

    if data.startswith("approve|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "Not authorized.",
                show_alert=True,
            )
            return

        parts = data.split("|")
        if len(parts) != 2:
            return

        order_id = parts[1]
        order = get_order(order_id)

        if not order:
            await query.edit_message_text("❌ Order not found.")
            return

        update_order_status(order_id, "In Progress")

        await query.edit_message_reply_markup(
            reply_markup=None
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ Payment Approved!\n\n"
                f"🆔 Order ID: {order_id}\n"
                f"🛠 Service: {order['service_name']}\n\n"
                "Your order is now being processed.\n"
                "Thank you for using Engineering Services."
            ),
        )
        return

    if data.startswith("reject|"):
        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "Not authorized.",
                show_alert=True,
            )
            return

        parts = data.split("|")
        if len(parts) != 2:
            return

        order_id = parts[1]
        order = get_order(order_id)

        if not order:
            await query.edit_message_text("❌ Order not found.")
            return

        update_order_status(
            order_id,
            "Payment Rejected",
        )

        await query.edit_message_reply_markup(
            reply_markup=None
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ Payment receipt rejected.\n\n"
                f"🆔 Order ID: {order_id}\n\n"
                "Please make sure the receipt is clear "
                "and resend it."
            ),
        )
        return


# =========================================================
# RECEIPT HANDLER
# =========================================================

async def receipt_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    order_id = context.user_data.get("order_id")

    if not order_id:
        await update.message.reply_text(
            "⚠️ Please choose a service first."
        )
        return

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(
            "❌ Order not found. Please start again with /start."
        )
        return

    payment_method = order["payment_method"] or "Unknown"

    update_order_status(
        order_id,
        "Payment Submitted",
    )

    caption = (
        "💰 NEW PAYMENT RECEIPT\n\n"
        f"🆔 Order ID: {order_id}\n"
        f"👤 Customer: {user.full_name}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {payment_method}\n"
        "📌 Status: Payment Submitted"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve|{order_id}",
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject|{order_id}",
            ),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message.photo:
        photo = update.message.photo[-1]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    elif update.message.document:
        document = update.message.document

        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=document.file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    await update.message.reply_text(
        "✅ Receipt received successfully!\n\n"
        f"🆔 Order ID: {order_id}\n"
        "⏳ Your payment is being reviewed.\n\n"
        "You will receive a confirmation after approval."
    )


# =========================================================# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
async def home():
    return {
        "status": "Engineering Services Bot is running"
    }


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
async def startup():

    print("Starting Engineering Services Bot...")

    await telegram_app.initialize()
    await telegram_app.start()

    base_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not base_url:
        print("ERROR: RENDER_EXTERNAL_URL is missing!")
        return

    webhook_url = f"{base_url.rstrip('/')}/telegram"

    print(f"Setting Telegram webhook: {webhook_url}")

    await telegram_app.bot.delete_webhook(
        drop_pending_updates=False
    )

    await telegram_app.bot.set_webhook(
        url=webhook_url
    )

    webhook_info = await telegram_app.bot.get_webhook_info()

    print(f"Webhook URL: {webhook_info.url}")
    print(
        f"Pending updates: "
        f"{webhook_info.pending_update_count}"
    )

    print("Telegram webhook set successfully!")


# =========================================================
# SHUTDOWN
# =========================================================

@app.on_event("shutdown")
async def shutdown():

    print("Stopping Engineering Services Bot...")

    await telegram_app.stop()
    await telegram_app.shutdown()
