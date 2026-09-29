import os

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]

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
            InlineKeyboardButton("📄 CV", callback_data="cv"),
            InlineKeyboardButton("📝 Cover Letter", callback_data="cover"),
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
# SERVICES COMMAND
# =========================

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🛠 Our Services\n\n"
        "📐 Surveying & Engineering\n"
        "📊 Excel / KML / Coordinate\n"
        "📄 Professional CV — 800 ETB\n"
        "📝 Cover Letter — 200 ETB\n"
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


    # MAIN MENU
    if data == "menu":

        await query.edit_message_text(
            "🏠 Main Menu\n\n"
            "Choose a service below:",
            reply_markup=main_menu()
        )

        return


    # PAYMENT MENU
    if data == "payment":

        await query.edit_message_text(
            "💳 Payment Methods\n\n"
            "Choose your preferred payment method:",
            reply_markup=payment_menu()
        )

        return


    # PAYMENT METHODS
    payment_names = {
        "bank": "🏦 Bank Transfer",
        "telebirr": "📱 Telebirr",
        "cbe_birr": "💳 CBE Birr",
        "coopay": "🟢 Coopay-Ebirr",
        "awash": "🟠 Awash"
    }


    if data in payment_names:

        method = payment_names[data]

        await query.edit_message_text(
            f"{method}\n\n"
            "Payment integration is being prepared.\n\n"
            "Your order will be connected to this payment method.\n"
            "Please wait for payment instructions.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 Other Payment Methods",
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


    # SERVICE
    if data in services:

        service = services[data]

        keyboard = [
            [
                InlineKeyboardButton(
                    f"🛒 Order Now — {service['price']}",
                    callback_data=f"order_{data}"
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


    # ORDER
    if data.startswith("order_"):

        service_id = data.replace("order_", "")

        if service_id not in services:
            return

        service = services[service_id]

        await query.edit_message_text(
            "🛒 Order Request\n\n"
            f"Service: {service['name']}\n"
            f"Price: {service['price']}\n\n"
            "Choose your payment method:",
            reply_markup=InlineKeyboardMarkup([
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
                        "🏠 Main Menu",
                        callback_data="menu"
                    )
                ]
            ])
        )

        return


    # SUPPORT
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