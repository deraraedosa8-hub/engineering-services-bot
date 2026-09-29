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
        "name": "💼 Job Application Support