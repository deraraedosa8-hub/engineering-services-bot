import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

# =========================================================
# DATABASE
# =========================================================

DB_FILE = "orders.db"


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


def create_order(
    user_id,
    customer_name,
    username,
    service_id,
    service_name,
    price,
):

    conn = get_db()

    now = datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cursor = conn.execute(
        """
        INSERT INTO orders (
            order_id,
            user_id,
            customer_name,
            username,
            service_id,
            service_name,
            price,
            payment_method,
            status,
            created_at,
            updated_at
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
        """
        UPDATE orders
        SET order_id = ?
        WHERE id = ?
        """,
        (order_id, database_id),
    )

    conn.commit()
    conn.close()

    return order_id


def update_order_payment(
    order_id,
    payment_method
):

    conn = get_db()

    now = datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute(
        """
        UPDATE orders
        SET payment_method = ?,
            status = ?,
            updated_at = ?
        WHERE order_id = ?
        """,
        (
            payment_method,
            "Payment Submitted",
            now,
            order_id,
        ),
    )

    conn.commit()
    conn.close()


def update_order_status(
    order_id,
    status
):

    conn = get_db()

    now = datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn.execute(
        """
        UPDATE orders
        SET status = ?,
            updated_at = ?
        WHERE order_id = ?
        """,
        (
            status,
            now,
            order_id,
        ),
    )

    conn.commit()
    conn.close()


def get_order(order_id):

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,),
    ).fetchone()

    conn.close()

    return row


def get_recent_orders(limit=20):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM orders
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return rows


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "📐 Surveying",
                callback_data="surveying"
            ),
            InlineKeyboardButton(
                "📊 Excel / KML",
                callback_data="excel"
            ),
        ],
        [
            InlineKeyboardButton(
                "📄 CV & Cover Letter",
                callback_data="cv_menu"
            ),
        ],
        [
            InlineKeyboardButton(
                "🤖 AI Services",
                callback_data="ai"
            ),
            InlineKeyboardButton(
                "🎨 Design",
                callback_data="design"
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Translation",
                callback_data="translation"
            ),
            InlineKeyboardButton(
                "💳 Payment",
                callback_data="payment"
            ),
        ],
        [
            InlineKeyboardButton(
                "📞 Support",
                callback_data="support"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# CV MENU
# =========================================================

def cv_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "📄 Professional CV — 800 ETB",
                callback_data="cv"
            )
        ],
        [
            InlineKeyboardButton(
                "📝 Cover Letter — 200 ETB",
                callback_data="cover"
            )
        ],
        [
            InlineKeyboardButton(
                "💼 Job Application Support — 300 ETB irraa",
                callback_data="job_support"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="menu"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# PAYMENT MENU
# =========================================================

def payment_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🏦 Bank Transfer",
                callback_data="bank"
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Telebirr",
                callback_data="telebirr"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 CBE Birr",
                callback_data="cbe_birr"
            )
        ],
        [
            InlineKeyboardButton(
                "🟢 Coopay-Ebirr",
                callback_data="coopay"
            )
        ],
        [
            InlineKeyboardButton(
                "🟠 Awash",
                callback_data="awash"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Main Menu",
                callback_data="menu"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# SERVICES
# =========================================================

services = {

    "surveying": {
        "name": "📐 Surveying & Engineering",
        "price": "500 ETB irraa",
        "description":
            "• Total Station support\n"
            "• Coordinate processing\n"
            "• Survey data processing\n"
            "• Road construction survey support"
    },

    "excel": {
        "name": "📊 Excel / KML / Coordinate",
        "price": "300 ETB irraa",
        "description":
            "• Excel data processing\n"
            "• KML / KMZ preparation\n"
            "• Coordinate conversion\n"
            "• Survey data formatting"
    },

    "cv": {
        "name": "📄 Professional CV",
        "price": "800 ETB",
        "description":
            "• Professional CV writing\n"
            "• International-style CV\n"
            "• Job-focused formatting\n"
            "• PDF-ready document"
    },

    "cover": {
        "name": "📝 Cover Letter",
        "price": "200 ETB",
        "description":
            "• Professional cover letter\n"
            "• Job-specific application\n"
            "• Clear and professional writing"
    },

    "job_support": {
        "name": "💼 Job Application Support",
        "price": "300 ETB irraa",
        "description":
            "• Job application assistance\n"
            "• CV & Cover Letter review\n"
            "• Job-specific application support\n"
            "• Professional application guidance"
    },

    "ai": {
        "name": "🤖 AI Services",
        "price": "200 ETB irraa",
        "description":
            "• AI writing\n"
            "• Document assistance\n"
            "• AI-generated content\n"
            "• Professional text improvement"
    },

    "design": {
        "name": "🎨 Poster & Design",
        "price": "350 ETB irraa",
        "description":
            "• Business posters\n"
            "• Social media designs\n"
            "• Promotional graphics\n"
            "• Digital designs"
    },

    "translation": {
        "name": "🌐 Translation",
        "price": "150 ETB irraa",
        "description":
            "• Afaan Oromo ↔ English\n"
            "• Afaan Oromo ↔ Amharic\n"
            "• English ↔ Amharic"
    }
}


# =========================================================
# PAYMENT INFORMATION
# =========================================================

payment_info = {

    "bank": {
        "name": "🏦 Bank Transfer",
        "account": os.environ.get(
            "BANK_ACCOUNT",
            "Bank account information is not configured yet."
        )
    },

    "telebirr": {
        "name": "📱 Telebirr",
        "account": os.environ.get(
            "TELEBIRR_NUMBER",
            "Telebirr number is not configured yet."
        )
    },

    "cbe_birr": {
        "name": "💳 CBE Birr",
        "account": os.environ.get(
            "CBE_BIRR_NUMBER",
            "CBE Birr number is not configured yet."
        )
    },

    "coopay": {
        "name": "🟢 Coopay-Ebirr",
        "account": os.environ.get(
            "COOPAY_NUMBER",
            "Coopay-Ebirr number is not configured yet."
        )
    },

    "awash": {
        "name": "🟠 Awash",
        "account": os.environ.get(
            "AWASH_ACCOUNT",
            "Awash account information is not configured yet."
        )
    }
}


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\n"
        "Professional digital & engineering services.\n\n"
        "👇 Choose a service:",
        reply_markup=main_menu()
    )


# =========================================================
# SERVICES COMMAND
# =========================================================

async def services_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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
        reply_markup=main_menu()
    )


# =========================================================
# ADMIN ORDERS
# =========================================================

async def orders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ You are not authorized to view orders."
        )
        return

    orders = get_recent