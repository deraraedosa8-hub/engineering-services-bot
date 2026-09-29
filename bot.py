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


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📐 Surveying", callback_data="surveying"),
            InlineKeyboardButton("📄 CV & Cover Letter", callback_data="cv"),
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Engineering Services!\n\n"
        "Choose a service below:",
        reply_markup=main_menu(),
    )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 Our Services\n\n"
        "📐 Surveying & Engineering\n"
        "📊 Excel / KML / Coordinate Services\n"
        "📄 CV & Cover Letter\n"
        "🤖 AI Services\n"
        "🎨 Poster & Design\n"
        "🌐 Translation\n\n"
        "Choose from the menu below:",
        reply_markup=main_menu(),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    messages = {
        "surveying":
            "📐 Surveying Services\n\n"
            "• Total Station support\n"
            "• Coordinate processing\n"
            "• KML / Excel work\n"
            "• Survey data processing",

        "cv":
            "📄 CV & Cover Letter\n\n"
            "Professional CV\n"
            "Cover Letter\n"
            "Job application support",

        "ai":
            "🤖 AI Services\n\n"
            "AI writing\n"
            "Translation\n"
            "Document assistance",

        "design":
            "🎨 Design Services\n\n"
            "Posters\n"
            "Social media designs\n"
            "Business graphics",

        "translation":
            "🌐 Translation\n\n"
            "Afaan Oromo ↔ English\n"
            "Afaan Oromo ↔ Amharic\n"
            "English ↔ Amharic",

        "payment":
            "💳 Payment\n\n"
            "Payment system will be connected here.\n"
            "We will add the payment provider next.",

        "support":
            "📞 Support\n\n"
            "Please contact our support team."
    }

    await query.edit_message_text(
        messages.get(query.data, "Please choose a service."),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu")]
        ])
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏠 Main Menu\n\nChoose a service:",
        reply_markup=main_menu()
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("services", services))
telegram_app.add_handler(CallbackQueryHandler(button))


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()

    base_url = os.environ.get("RENDER_EXTERNAL_URL")

    if base_url:
        await telegram_app.bot.set_webhook(
            url=f"{base_url}/telegram"
        )


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data=data,
        bot=telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}


@app.get("/")
async def home():
    return {"status": "Engineering Services Bot is running"}