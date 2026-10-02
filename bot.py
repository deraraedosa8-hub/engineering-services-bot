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

    # Upgrade existing database safely
    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(orders)"
        ).fetchall()
    }

    if "request_details" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN request_details TEXT"
        )

    if "phone" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN phone TEXT"
        )

    if "file_id" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN file_id TEXT"
        )

    if "file_type" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN file_type TEXT"
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
    request_details,
    phone,
):
    conn = get_db()
    now = now_utc()

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
            updated_at,
            request_details,
            phone,
            file_id,
            file_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            request_details,
            phone,
            None,
            None,
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
        (
            payment_method,
            "Payment Submitted",
            now_utc(),
            order_id,
        ),
    )

    conn.commit()
    conn.close()


def update_order_status(order_id, status):
    conn = get_db()

    conn.execute(
        """
        UPDATE orders
        SET status = ?,
            updated_at = ?
        WHERE order_id = ?
        """,
        (
            status,
            now_utc(),
            order_id,
        ),
    )

    conn.commit()
    conn.close()


def update_order_file(order_id, file_id, file_type):
    conn = get_db()

    conn.execute(
        """
        UPDATE orders
        SET file_id = ?,
            file_type = ?,
            updated_at = ?
        WHERE order_id = ?
        """,
        (
            file_id,
            file_type,
            now_utc(),
            order_id,
        ),
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


def file_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "⏭️ Skip File",
                callback_data="skip_file",
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


def payment_after_request_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Choose Payment",
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

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\n"
        "Professional digital & engineering services.\n\n"
        "👇 Choose a service:",
        reply_markup=main_menu(),
    )


# =========================================================
# SERVICES COMMAND
# =========================================================

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
# SERVICE REQUEST FORM
# =========================================================

async def show_service(
    query,
    context,
    service_id,
):
    service = services[service_id]

    context.user_data.clear()

    context.user_data["pending_service_id"] = service_id
    context.user_data["request_stage"] = "details"

    await query.edit_message_text(
        f"{service['name']}\n\n"
        f"💰 Price: {service['price']}\n\n"
        f"{service['description']}\n\n"
        "📝 Step 1 of 3\n\n"
        "Please describe what you need.\n\n"
        "Example:\n"
        "\"I need an Excel file from my survey coordinates \"\n"
        "or\n"
        "\"I need a professional CV for a surveyor job.\""
    )


# =========================================================
# TEXT FORM HANDLER
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message
    text = message.text.strip()

    stage = context.user_data.get("request_stage")

    # -----------------------------------------------------
    # REQUEST DETAILS
    # -----------------------------------------------------

    if stage == "details":
        context.user_data["request_details"] = text
        context.user_data["request_stage"] = "phone"

        await message.reply_text(
            "📱 Step 2 of 3\n\n"
            "Please send your phone number.\n\n"
            "Example: 09XXXXXXXX"
        )

        return

    # -----------------------------------------------------
    # PHONE
    # -----------------------------------------------------

    if stage == "phone":
        phone = text

        if len(phone) < 7:
            await message.reply_text(
                "⚠️ Please enter a valid phone number."
            )
            return

        service_id = context.user_data.get(
            "pending_service_id"
        )

        request_details = context.user_data.get(
            "request_details",
            "",
        )

        if not service_id or service_id not in services:
            await message.reply_text(
                "❌ Session expired.\n\n"
                "Please use /start and choose a service again."
            )
            context.user_data.clear()
            return

        service = services[service_id]
        user = update.effective_user

        order_id = create_order(
            user.id,
            user.full_name,
            user.username or "",
            service_id,
            service["name"],
            service["price"],
            request_details,
            phone,
        )

        context.user_data["order_id"] = order_id
        context.user_data["service_id"] = service_id
        context.user_data["request_stage"] = "file"

        await message.reply_text(
            "📎 Step 3 of 3\n\n"
            "Do you have a file related to your request?\n\n"
            "You can send:\n"
            "• PDF\n"
            "• Word document\n"
            "• Excel file\n"
            "• Image\n"
            "• KML/KMZ\n"
            "• Other project files\n\n"
            "If you don't have a file, tap Skip File.",
            reply_markup=file_menu(),
        )

        return

    # -----------------------------------------------------
    # NORMAL TEXT
    # -----------------------------------------------------

    await message.reply_text(
        "Please choose a service from the menu.",
        reply_markup=main_menu(),
    )


# =========================================================
# FILE HANDLER
# =========================================================

async def file_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message

    order_id = context.user_data.get("order_id")
    stage = context.user_data.get("request_stage")

    # =====================================================
    # PROJECT FILE
    # =====================================================

    if stage == "file":

        if not order_id:
            await message.reply_text(
                "❌ Order session not found.\n\n"
                "Please use /start again."
            )
            return

        order = get_order(order_id)

        if not order:
            await message.reply_text(
                "❌ Order not found.\n\n"
                "Please use /start again."
            )
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
            await message.reply_text(
                "⚠️ Please send a photo or document."
            )
            return

        update_order_file(
            order_id,
            file_id,
            file_type,
        )

        context.user_data["request_stage"] = None

        # Send project file to admin
        admin_caption = (
            "📥 NEW SERVICE REQUEST FILE\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"👤 Customer: {order['customer_name']}\n"
            f"🔗 Username: "
            f"@{order['username'] or 'N/A'}\n"
            f"📱 Phone: {order['phone'] or 'N/A'}\n"
            f"🛠 Service: {order['service_name']}\n"
            f"💰 Price: {order['price']}\n\n"
            f"📝 Request:\n"
            f"{order['request_details'] or 'N/A'}"
        )

        if message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption=admin_caption,
            )

        elif message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=file_id,
                caption=admin_caption,
            )

        await message.reply_text(
            "✅ Your project file has been received.\n\n"
            f"🆔 Order ID: {order_id}\n\n"
            "Now choose your payment method:",
            reply_markup=payment_after_request_menu(),
        )

        return

    # =====================================================
    # PAYMENT RECEIPT
    # =====================================================

    await receipt_handler(update, context)


# =========================================================
# SKIP FILE
# =========================================================

async def skip_file(
    query,
    context,
):
    order_id = context.user_data.get("order_id")

    if not order_id:
        await query.answer(
            "Order not found.",
            show_alert=True,
        )
        return

    context.user_data["request_stage"] = None

    await query.edit_message_text(
        "✅ Request information completed.\n\n"
        f"🆔 Order ID: {order_id}\n\n"
        "Now choose your payment method:",
        reply_markup=payment_after_request_menu(),
    )


# =========================================================
# PAYMENT
# =========================================================

async def show_payment(
    query,
    context,
    payment_method,
):
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

    update_order_payment(
        order_id,
        payment_method,
    )

    context.user_data["payment_method"] = payment_method
    context.user_data["request_stage"] = "receipt"

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

    # -----------------------------------------------------
    # MAIN MENU
    # -----------------------------------------------------

    if data == "menu":
        context.user_data.clear()

        await query.edit_message_text(
            "👋 Welcome to Engineering Services!\n\n"
            "👇 Choose a service:",
            reply_markup=main_menu(),
        )
        return

    # -----------------------------------------------------
    # CV MENU
    # -----------------------------------------------------

    if data == "cv_menu":
        await query.edit_message_text(
            "📄 CV & Career Services\n\n"
            "Choose a service:",
            reply_markup=cv_menu(),
        )
        return

    # -----------------------------------------------------
    # PAYMENT MENU
    # -----------------------------------------------------

    if data == "payment":
        if not context.user_data.get("order_id"):
            await query.answer(
                "Please choose a service first.",
                show_alert=True,
            )
            return

        await query.edit_message_text(
            "💳 Choose your payment method:",
            reply_markup=payment_menu(),
        )
        return

    # -----------------------------------------------------
    # RECEIPT INFORMATION
    # -----------------------------------------------------

    if data == "receipt_info":
        order_id = context.user_data.get("order_id")

        if not order_id:
            await query.answer(
                "Please choose a service first.",
                show_alert=True,
            )
            return

        context.user_data["request_stage"] = "receipt"

        await query.edit_message_text(
            "📸 Please send your payment receipt now.\n\n"
            "You can send it as a photo or document."
        )
        return

    # -----------------------------------------------------
    # SKIP FILE
    # -----------------------------------------------------

    if data == "skip_file":
        await skip_file(
            query,
            context,
        )
        return

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    if data == "support":
        await query.edit_message_text(
            "📞 Support\n\n"
            "Please contact the Engineering Services team "
            "for assistance."
        )
        return

    # -----------------------------------------------------
    # SERVICE
    # -----------------------------------------------------

    if data.startswith("service_"):
        service_id = data.replace(
            "service_",
            "",
            1,
        )

        if service_id in services:
            await show_service(
                query,
                context,
                service_id,
            )

        return

    # -----------------------------------------------------
    # PAYMENT METHOD
    # -----------------------------------------------------

    if data.startswith("payment_"):
        payment_method = data.replace(
            "payment_",
            "",
            1,
        )

        if payment_method in payment_info:
            await show_payment(
                query,
                context,
                payment_method,
            )

        return

    # -----------------------------------------------------
    # ADMIN APPROVE
    # -----------------------------------------------------

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
            await query.edit_message_text(
                "❌ Order not found."
            )
            return

        update_order_status(
            order_id,
            "In Progress",
        )

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

    # -----------------------------------------------------
    # ADMIN REJECT
    # -----------------------------------------------------

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
            await query.edit_message_text(
                "❌ Order not found."
            )
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
# PAYMENT RECEIPT HANDLER
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
            "❌ Order not found.\n\n"
            "Please start again with /start."
        )
        return

    payment_method = order["payment_method"]

    if not payment_method:
        await update.message.reply_text(
            "⚠️ Please choose a payment method first."
        )
        return

    update_order_status(
        order_id,
        "Payment Submitted",
    )

    caption = (
        "💰 NEW PAYMENT RECEIPT\n\n"
        f"🆔 Order ID: {order_id}\n"
        f"👤 Customer: {order['customer_name']}\n"
        f"🔗 Username: "
        f"@{order['username'] or 'N/A'}\n"
        f"📱 Phone: {order['phone'] or 'N/A'}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {payment_method}\n\n"
        "📝 Request:\n"
        f"{order['request_details'] or 'N/A'}\n\n"
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


# =========================================================
# ADMIN ORDERS
# =========================================================

async def orders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ You are not authorized."
        )
        return

    orders = get_recent_orders(20)

    if not orders:
        await update.message.reply_text(
            "📦 No orders found."
        )
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

    await update.message.reply_text(text)# =========================================================
# CUSTOMER ORDER STATUS
# =========================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    # Specific order: /status ORD-00001
    if context.args:
        order_id = context.args[0].strip().upper()
        order = get_order(order_id)

        if not order:
            await update.message.reply_text(
                "❌ Order not found.\n\n"
                "Example:\n"
                "/status ORD-00001"
            )
            return

        # Customer can only see their own order
        if order["user_id"] != user_id and user_id != ADMIN_ID:
            await update.message.reply_text(
                "⛔ You are not authorized to view this order."
            )
            return

    else:
        # If no ID is given, show customer's latest order
        conn = get_db()

        order = conn.execute(
            """
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        conn.close()

        if not order:
            await update.message.reply_text(
                "📦 You don't have any orders yet.\n\n"
                "Use /start to create a new order."
            )
            return

    await update.message.reply_text(
        "📦 <b>ORDER STATUS</b>\n\n"
        f"🆔 <b>Order ID:</b> <code>{order['order_id']}</code>\n"
        f"🛠 <b>Service:</b> {order['service_name']}\n"
        f"💰 <b>Price:</b> {order['price']}\n"
        f"💳 <b>Payment:</b> "
        f"{order['payment_method'] or 'Not selected'}\n"
        f"📌 <b>Status:</b> {order['status']}\n"
        f"📎 <b>File:</b> "
        f"{'Attached' if order['file_id'] else 'No file'}\n"
        f"📅 <b>Created:</b> {order['created_at']}\n"
        f"🔄 <b>Updated:</b> {order['updated_at']}",
        parse_mode="HTML",
    ) 


# =========================================================
# ADMIN SINGLE ORDER
# =========================================================

async def order_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ You are not authorized."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n/order ORD-00001"
        )
        return

    order_id = context.args[0].strip()

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(
            "❌ Order not found."
        )
        return

    file_status = (
        "📎 File attached"
        if order["file_id"]
        else "📎 No file"
    )

    await update.message.reply_text(
        "📦 Order Details\n\n"
        f"🆔 {order['order_id']}\n"
        f"👤 {order['customer_name']}\n"
        f"🔗 @{order['username'] or 'N/A'}\n"
        f"📱 Phone: {order['phone'] or 'N/A'}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: "
        f"{order['payment_method'] or 'Not selected'}\n"
        f"📌 Status: {order['status']}\n"
        f"{file_status}\n\n"
        "📝 Request Details:\n"
        f"{order['request_details'] or 'N/A'}\n\n"
        f"📅 Created: {order['created_at']}\n"
        f"🔄 Updated: {order['updated_at']}"
    )


# =========================================================
# TELEGRAM HANDLERS
# =========================================================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("services", services_command)
)

telegram_app.add_handler(
    CommandHandler("orders", orders_command)
)

telegram_app.add_handler(
    CommandHandler("order", order_command)
)telegram_app.add_handler(
    CommandHandler("status", status_command)
)

# Admin approval/rejection and all other callbacks
telegram_app.add_handler(
    CallbackQueryHandler(button_handler)
)

# Photos/documents:
# project file during request OR payment receipt
telegram_app.add_handler(
    MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        file_handler,
    )
)

# Text form
telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler,
    )
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
async def root():
    return {
        "status": "Engineering Services Bot is running"
    }


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.post("/telegram")
async def telegram_webhook(
    request: Request,
):
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot,
    )

    print("Telegram update received")
    print(f"Update ID: {update.update_id}")

    await telegram_app.process_update(update)

    print("Telegram update processed successfully")

    return {"ok": True}


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
async def startup():

    await telegram_app.initialize()
    await telegram_app.start()

    base_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )

    if not base_url:
        print(
            "ERROR: RENDER_EXTERNAL_URL is missing!"
        )
        return

    webhook_url = (
        f"{base_url.rstrip('/')}/telegram"
    )

    print(
        f"Setting Telegram webhook: "
        f"{webhook_url}"
    )

    await telegram_app.bot.delete_webhook(
        drop_pending_updates=False
    )

    await telegram_app.bot.set_webhook(
        url=webhook_url
    )

    webhook_info = (
        await telegram_app.bot.get_webhook_info()
    )

    print(
        f"Webhook URL: {webhook_info.url}"
    )

    print(
        f"Pending updates: "
        f"{webhook_info.pending_update_count}"
    )

    print(
        "Telegram webhook set successfully!"
    )


# =========================================================
# SHUTDOWN
# =========================================================

@app.on_event("shutdown")
async def shutdown():

    await telegram_app.stop()
    await telegram_app.shutdown()