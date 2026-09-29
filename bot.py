import os

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

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

app = FastAPI()

telegram_app = Application.builder().token(TOKEN).build()


# =========================
# MAIN MENU
# =========================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📐 Surveying", callback_data="surveying"),
            InlineKeyboardButton("📊 Excel / KML", callback_data="excel"),
        ],
        [
            InlineKeyboardButton(
                "📄 CV & Cover Letter",
                callback_data="cv_menu"
            ),
        ],
        [
            InlineKeyboardButton("🤖 AI Services", callback_data="ai"),
            InlineKeyboardButton("🎨 Design", callback_data="design"),
        ],
        [
            InlineKeyboardButton("🌐 Translation", callback_data="translation"),
            InlineKeyboardButton("💳 Payment", callback_data="payment"),
        ],
        [
            InlineKeyboardButton("📞 Support", callback_data="support"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# CV MENU
# =========================

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


# =========================
# PAYMENT MENU
# =========================

def payment_menu():
    keyboard = [
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="bank")],
        [InlineKeyboardButton("📱 Telebirr", callback_data="telebirr")],
        [InlineKeyboardButton("💳 CBE Birr", callback_data="cbe_birr")],
        [InlineKeyboardButton("🟢 Coopay-Ebirr", callback_data="coopay")],
        [InlineKeyboardButton("🟠 Awash", callback_data="awash")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu")],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# SERVICE DATA
# =========================

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


# =========================
# PAYMENT INFORMATION
# =========================

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


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\n"
        "Professional digital & engineering services.\n\n"
        "👇 Choose a service:",
        reply_markup=main_menu()
    )


# =========================
# SERVICES
# =========================

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

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


# =========================
# BUTTON HANDLER
# =========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data


    # =========================
    # MAIN MENU
    # =========================

    if data == "menu":

        await query.edit_message_text(
            "🏠 Main Menu\n\n"
            "Choose a service below:",
            reply_markup=main_menu()
        )

        return


    # =========================
    # CV MENU
    # =========================

    if data == "cv_menu":

        await query.edit_message_text(
            "📄 CV & Cover Letter\n\n"
            "Choose the service you need:",
            reply_markup=cv_menu()
        )

        return


    # =========================
    # PAYMENT MENU
    # =========================

    if data == "payment":

        await query.edit_message_text(
            "💳 Payment Methods\n\n"
            "Choose your preferred payment method:",
            reply_markup=payment_menu()
        )

        return


    # =========================
    # SERVICE
    # =========================

    if data in services:

        service = services[data]

        back_button = "cv_menu" if data in [
            "cv",
            "cover",
            "job_support"
        ] else "menu"

        keyboard = [
            [
                InlineKeyboardButton(
                    f"🛒 Order Now — {service['price']}",
                    callback_data=f"order_{data}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=back_button
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
                    callback_data="menu"
                )
            ]
        ]

        await query.edit_message_text(
            f"{service['name']}\n\n"
            f"{service['description']}\n\n"
            f"💰 Price: {service['price']}\n\n"
            "Ready to order?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return


    # =========================
    # ORDER
    # =========================

    if data.startswith("order_"):

        service_id = data.replace("order_", "")

        if service_id not in services:
            return

        service = services[service_id]

        # Save current order
        context.user_data["pending_service"] = service_id

        await query.edit_message_text(
            "🛒 Order Request\n\n"
            f"Service: {service['name']}\n"
            f"Price: {service['price']}\n\n"
            "Choose your payment method:",
            reply_markup=payment_menu()
        )

        return


    # =========================
    # PAYMENT METHOD
    # =========================

    if data in payment_info:

        service_id = context.user_data.get("pending_service")

        if not service_id or service_id not in services:

            await query.edit_message_text(
                "⚠️ Please choose a service first.",
                reply_markup=main_menu()
            )

            return

        service = services[service_id]
        payment = payment_info[data]

        context.user_data["pending_payment"] = data

        await query.edit_message_text(
            f"{payment['name']}\n\n"
            f"🛠 Service: {service['name']}\n"
            f"💰 Price: {service['price']}\n\n"
            f"💳 Payment Information:\n"
            f"{payment['account']}\n\n"
            "📸 After payment, send your payment receipt "
            "here as a photo or document.\n\n"
            "Your receipt will be reviewed by our team.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Payment Methods",
                        callback_data="payment"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="menu"
                    )
                ]
            ])
        )

        return


    # =========================
    # ADMIN APPROVE
    # =========================

    if data.startswith("approve|"):

        parts = data.split("|")

        if len(parts) != 4:
            return

        user_id = int(parts[1])
        service_id = parts[2]
        method = parts[3]

        service = services.get(service_id)

        if not service:
            return

        await query.edit_message_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "✅ Payment Approved"
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Payment Approved!\n\n"
                    f"Service: {service['name']}\n"
                    f"Price: {service['price']}\n"
                    f"Payment: {payment_info[method]['name']}\n\n"
                    "🎉 Your order has been confirmed.\n"
                    "Our team will contact you shortly."
                )
            )
        except Exception:
            pass

        return


    # =========================
    # ADMIN REJECT
    # =========================

    if data.startswith("reject|"):

        parts = data.split("|")

        if len(parts) != 4:
            return

        user_id = int(parts[1])
        service_id = parts[2]
        method = parts[3]

        service = services.get(service_id)

        if not service:
            return

        await query.edit_message_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "❌ Payment Rejected"
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Payment Receipt Rejected\n\n"
                    f"Service: {service['name']}\n\n"
                    "Please check your payment receipt "
                    "and send it again."
                )
            )
        except Exception:
            pass

        return


    # =========================
    # SUPPORT
    # =========================

    if data == "support":

        await query.edit_message_text(
            "📞 Support\n\n"
            "For support, please contact our team.\n\n"
            "We will respond as soon as possible.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="menu"
                    )
                ]
            ])
        )

        return


# =========================
# RECEIPT HANDLER
# =========================

async def receipt_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    service_id = context.user_data.get("pending_service")
    payment_method = context.user_data.get("pending_payment")

    if not service_id or service_id not in services:
        await update.message.reply_text(
            "⚠️ Please choose a service and payment method first."
        )
        return

    if not payment_method or payment_method not in payment_info:
        await update.message.reply_text(
            "⚠️ Please choose a payment method first."
        )
        return

    service = services[service_id]
    payment = payment_info[payment_method]

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    caption = (
        "🔔 NEW PAYMENT RECEIPT\n\n"
        f"👤 Customer: {user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 User ID: {user.id}\n\n"
        f"🛠 Service: {service['name']}\n"
        f"💰 Price: {service['price']}\n"
        f"💳 Payment: {payment['name']}\n\n"
        "Please review the receipt."
    )

    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=(
                    f"approve|{user.id}|{service_id}|{payment_method}"
                )
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=(
                    f"reject|{user.id}|{service_id}|{payment_method}"
                )
            )
        ]
    ])

    try:

        if update.message.photo:

            photo = update.message.photo[-1]

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=caption,
                reply_markup=admin_keyboard
            )

        elif update.message.document:

            document = update.message.document

            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=document.file_id,
                caption=caption,
                reply_markup=admin_keyboard
            )

        await update.message.reply_text(
            "✅ Receipt received!\n\n"
            "Your payment receipt has been sent to our team "
            "for verification.\n\n"
            "Please wait for confirmation."
        )

    except Exception:

        await update.message.reply_text(
            "⚠️ We could not send your receipt.\n"
            "Please try again."
        )


# =========================
# HANDLERS
# =========================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("services", services_command)
)

telegram_app.add_handler(
    CallbackQueryHandler(button)
)

telegram_app.add_handler(
    MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        receipt_handler
    )
)


# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def startup():

    await telegram_app.initialize()

    await telegram_app.start()

    base_url = os.environ.get("RENDER_EXTERNAL_URL")

    if base_url:

        await telegram_app.bot.set_webhook(
            url=f"{base_url}/telegram"
        )


# =========================
# SHUTDOWN
# =========================

@app.on_event("shutdown")
async def shutdown():

    await telegram_app.stop()

    await telegram_app.shutdown()


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.post("/telegram")
async def telegram_webhook(request: Request):

    data = await request.json()

    update = Update.de_json(
        data=data,
        bot=telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}


# =========================
# HEALTH CHECK
# =========================

@app.get("/")
async def home():

    return {
        "status": "Engineering Services Bot is running"
    }