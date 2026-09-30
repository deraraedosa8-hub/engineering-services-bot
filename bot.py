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


def create_order(
    user_id,
    customer_name,
    username,
    service_id,
    service_name,
    price,
):
    conn = get_db()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

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


def update_order_payment(order_id, payment_method):
    conn = get_db()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

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


def update_order_status(order_id, status):
    conn = get_db()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

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
            "• Road construction survey support",
    },

    "excel": {
        "name": "📊 Excel / KML / Coordinate",
        "price": "300 ETB irraa",
        "description":
            "• Excel data processing\n"
            "• KML / KMZ preparation\n"
            "• Coordinate conversion\n"
            "• Survey data formatting",
    },

    "cv": {
        "name": "📄 Professional CV",
        "price": "800 ETB",
        "description":
            "• Professional CV writing\n"
            "• International-style CV\n"
            "• Job-focused formatting\n"
            "• PDF-ready document",
    },

    "cover": {
        "name": "📝 Cover Letter",
        "price": "200 ETB",
        "description":
            "• Professional cover letter\n"
            "• Job-specific application\n"
            "• Clear and professional writing",
    },

    "job_support": {
        "name": "💼 Job Application Support",
        "price": "300 ETB irraa",
        "description":
            "• Job application assistance\n"
            "• CV & Cover Letter review\n"
            "• Job-specific application support\n"
            "• Professional application guidance",
    },

    "ai": {
        "name": "🤖 AI Services",
        "price": "200 ETB irraa",
        "description":
            "• AI writing\n"
            "• Document assistance\n"
            "• AI-generated content\n"
            "• Professional text improvement",
    },

    "design": {
        "name": "🎨 Poster & Design",
        "price": "350 ETB irraa",
        "description":
            "• Business posters\n"
            "• Social media designs\n"
            "• Promotional graphics\n"
            "• Digital designs",
    },

    "translation": {
        "name": "🌐 Translation",
        "price": "150 ETB irraa",
        "description":
            "• Afaan Oromo ↔ English\n"
            "• Afaan Oromo ↔ Amharic\n"
            "• English ↔ Amharic",
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
                callback_data="surveying",
            ),
            InlineKeyboardButton(
                "📊 Excel / KML",
                callback_data="excel",
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
                callback_data="ai",
            ),
            InlineKeyboardButton(
                "🎨 Design",
                callback_data="design",
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Translation",
                callback_data="translation",
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
                callback_data="cv",
            )
        ],
        [
            InlineKeyboardButton(
                "📝 Cover Letter — 200 ETB",
                callback_data="cover",
            )
        ],
        [
            InlineKeyboardButton(
                "💼 Job Application Support — 300 ETB irraa",
                callback_data="job_support",
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
                callback_data="bank",
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Telebirr",
                callback_data="telebirr",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 CBE Birr",
                callback_data="cbe_birr",
            )
        ],
        [
            InlineKeyboardButton(
                "🟢 Coopay-Ebirr",
                callback_data="coopay",
            )
        ],
        [
            InlineKeyboardButton(
                "🟠 Awash",
                callback_data="awash",
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
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
# ADMIN ORDERS COMMAND
# =========================================================

async def orders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ You are not authorized to view orders."
        )
        return

    orders = get_recent_orders(20)

    if not orders:
        await update.message.reply_text(
            "📦 No orders found."
        )
        return

    text = "📦 RECENT ORDERS\n\n"

    for order in orders:
        text += (
            f"🆔 {order['order_id']}\n"
            f"👤 {order['customer_name'] or 'Unknown'}\n"
            f"🛠 {order['service_name']}\n"
            f"💰 {order['price']}\n"
            f"💳 {order['payment_method'] or 'Not selected'}\n"
            f"📌 {order['status']}\n"
            f"🕒 {order['created_at']}\n"
            f"────────────────\n"
        )

    await update.message.reply_text(text)


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

    order_id = context.args[0].upper()

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(
            f"❌ Order {order_id} not found."
        )
        return

    text = (
        f"📦 ORDER DETAILS\n\n"
        f"🆔 Order ID: {order['order_id']}\n"
        f"👤 Customer: {order['customer_name']}\n"
        f"🔹 Username: @{order['username'] or 'N/A'}\n"
        f"🆔 User ID: {order['user_id']}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {order['payment_method'] or 'N/A'}\n"
        f"📌 Status: {order['status']}\n"
        f"🕒 Created: {order['created_at']}\n"
        f"🔄 Updated: {order['updated_at']}"
    )

    await update.message.reply_text(text)


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
        await query.edit_message_text(
            "👋 Welcome to Engineering Services!\n\n"
            "Professional digital & engineering services.\n\n"
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
            "👇 Choose a service:",
            reply_markup=cv_menu(),
        )
        return

    # -----------------------------------------------------
    # PAYMENT MENU
    # -----------------------------------------------------

    if data == "payment":
        order_id = context.user_data.get("order_id")

        if not order_id:
            await query.edit_message_text(
                "💳 Payment\n\n"
                "Please choose a service first, then select "
                "your payment method.",
                reply_markup=main_menu(),
            )
            return

        await query.edit_message_text(
            "💳 Choose your payment method:",
            reply_markup=payment_menu(),
        )
        return

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    if data == "support":
        await query.edit_message_text(
            "📞 Support\n\n"
            "For support, please contact the Engineering "
            "Services team.\n\n"
            "You can also send your question here.",
            reply_markup=main_menu(),
        )
        return

    # -----------------------------------------------------
    # SERVICE SELECTION
    # -----------------------------------------------------

    if data in services:

        service = services[data]

        user = query.from_user

        customer_name = user.full_name
        username = user.username or ""

        order_id = create_order(
            user_id=user.id,
            customer_name=customer_name,
            username=username,
            service_id=data,
            service_name=service["name"],
            price=service["price"],
        )

        context.user_data["order_id"] = order_id
        context.user_data["service_id"] = data

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

        await query.edit_message_text(
            f"{service['name']}\n\n"
            f"💰 Price: {service['price']}\n\n"
            f"{service['description']}\n\n"
            f"🆔 Order ID: {order_id}\n\n"
            f"👇 Continue to payment:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return

    # -----------------------------------------------------
    # PAYMENT METHOD
    # -----------------------------------------------------

    if data in payment_info:

        order_id = context.user_data.get("order_id")

        if not order_id:
            await query.edit_message_text(
                "❌ No active order found.\n\n"
                "Please choose a service first.",
                reply_markup=main_menu(),
            )
            return

        order = get_order(order_id)

        if not order:
            await query.edit_message_text(
                "❌ Order not found.\n\n"
                "Please start again with /start."
            )
            return

        info = payment_info[data]

        update_order_payment(
            order_id,
            data,
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
                    callback_data="menu",
                )
            ]
        ]

        await query.edit_message_text(
            f"{info['name']}\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"🛠 Service: {order['service_name']}\n"
            f"💰 Price: {order['price']}\n\n"
            f"💳 Payment Information:\n"
            f"{info['account']}\n\n"
            f"📸 After payment, send your payment receipt "
            f"here as a photo or document.\n\n"
            f"Your receipt will be reviewed by our team.",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
            "❌ No active order found.\n\n"
            "Please choose a service first using /start."
        )
        return

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(
            "❌ Order not found.\n\n"
            "Please start again with /start."
        )
        return

    payment_method = order["payment_method"] or "Unknown"

    caption = (
        "📥 NEW PAYMENT RECEIPT\n\n"
        f"🆔 Order ID: {order['order_id']}\n"
        f"👤 Customer: {order['customer_name']}\n"
        f"🔹 Username: @{order['username'] or 'N/A'}\n"
        f"🆔 User ID: {order['user_id']}\n"
        f"🛠 Service: {order['service_name']}\n"
        f"💰 Price: {order['price']}\n"
        f"💳 Payment: {payment_method}\n"
        f"📌 Status: {order['status']}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve|{order['order_id']}",
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject|{order['order_id']}",
            ),
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if update.message.photo:
        photo = update.message.photo[-1]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=caption,
            reply_markup=markup,
        )

    elif update.message.document:
        document = update.message.document

        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=document.file_id,
            caption=caption,
            reply_markup=markup,
        )

    update_order_status(
        order_id,
        "Payment Submitted",
    )

    await update.message.reply_text(
        f"✅ Receipt received successfully.\n\n"
        f"🆔 Order ID: {order_id}\n\n"
        f"Our team will review your payment and contact you."
    )


# =========================================================
# ADMIN APPROVE / REJECT
# =========================================================

async def admin_payment_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "⛔ Not authorized.",
            show_alert=True,
        )
        return

    await query.answer()

    data = query.data.split("|")

    action = data[0]
    order_id = data[1]

    order = get_order(order_id)

    if not order:
        await query.edit_message_text(
            "❌ Order not found."
        )
        return

    if action == "approve":

        update_order_status(
            order_id,
            "Payment Approved",
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ PAYMENT APPROVED\n\n"
                f"🆔 Order ID: {order_id}\n"
                f"🛠 Service: {order['service_name']}\n"
                f"💰 Price: {order['price']}\n\n"
                "Your payment has been approved.\n"
                "Your order will now be processed."
            ),
        )

        await query.edit_message_text(
            f"✅ PAYMENT APPROVED\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"👤 Customer: {order['customer_name']}\n"
            f"🛠 Service: {order['service_name']}\n"
            f"💰 Price: {order['price']}"
        )

    elif action == "reject":

        update_order_status(
            order_id,
            "Payment Rejected",
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "❌ PAYMENT REJECTED\n\n"
                f"🆔 Order ID: {order_id}\n\n"
                "Your payment receipt could not be approved.\n"
                "Please contact support or send a valid receipt."
            ),
        )

        await query.edit_message_text(
            f"❌ PAYMENT REJECTED\n\n"
            f"🆔 Order ID: {order_id}\n"
            f"👤 Customer: {order['customer_name']}"
        )


# =========================================================
# FALLBACK TEXT HANDLER
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👇 Please choose an option from the menu.",
        reply_markup=main_menu(),
    )


# =========================================================
# REGISTER HANDLERS
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
)

telegram_app.add_handler(
    CallbackQueryHandler(
        admin_payment_handler,
        pattern=r"^(approve|reject)\|",
    )
)

telegram_app.add_handler(
    CallbackQueryHandler(button_handler)
)

telegram_app.add_handler(
    MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        receipt_handler,
    )
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler,
    )
)


# =========================================================
# WEBHOOK
# =========================================================

@app.get("/")
async def home():
    return {
        "status": "Engineering Services Bot is running"
    }


@app.post("/telegram")
async def telegram_webhook(request: Request):

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
        f"Setting Telegram webhook: {webhook_url}"
    )

    await telegram_app.bot.delete_webhook(
        drop_pending_updates=False
    )

    await telegram_app.bot.set_webhook(
        url=webhook_url
    )

    info = await telegram_app.bot.get_webhook_info()

    print(
        f"Webhook URL: {info.url}"
    )

    print(
        f"Pending updates: "
        f"{info.pending_update_count}"
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