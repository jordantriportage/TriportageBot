import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "7244281986:AAF_ojoZVFL6fG41j01ckDcDsBGYJ592c6Q"

GROUP_CHAT_ID = -5156847371  # 🔴 ID du groupe

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    222222222: "Manager 2",
}

WAITING_TEMPLATE = set()

TEMPLATE_FIELDS = [
    "TITRE",
    "ORGANISME",
    "DATE LIMITE",
    "LIEU",
    "DESCRIPTION",
    "LIEN",
]


def parse_template(text: str):
    data = {}
    lines = text.split("\n")

    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()

        if key in TEMPLATE_FIELDS:
            data[key] = value

    if len(data) != len(TEMPLATE_FIELDS):
        return None

    return data


def format_message(data):
    return (
        f"📢 *{data['TITRE']}*\n\n"
        f"🏢 *Organisme* : {data['ORGANISME']}\n"
        f"📍 *Lieu* : {data['LIEU']}\n"
        f"📅 *Date limite* : {data['DATE LIMITE']}\n\n"
        f"📝 *Description* :\n{data['DESCRIPTION']}\n\n"
        f"🔗 [Lien vers l'appel d'offre]({data['LIEN']})"
    )


def is_private(update: Update):
    return update.effective_chat.type == "private"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return
    await update.message.reply_text("Bot opérationnel ✅")


async def new_opportunity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return  # ignore si envoyé dans le groupe

    user_id = update.effective_user.id

    if user_id not in MANAGERS:
        await update.message.reply_text("❌ Seuls les managers peuvent publier.")
        return

    WAITING_TEMPLATE.add(user_id)

    await update.message.reply_text(
        "Envoie le template EXACT :\n\n"
        "TITRE : ...\n"
        "ORGANISME : ...\n"
        "DATE LIMITE : ...\n"
        "LIEU : ...\n"
        "DESCRIPTION : ...\n"
        "LIEN : ..."
    )


async def handle_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return  # ignore tout message groupe

    user_id = update.effective_user.id

    if user_id not in WAITING_TEMPLATE:
        return

    data = parse_template(update.message.text)

    if not data:
        await update.message.reply_text("❌ Format incorrect. Respecte le template.")
        return

    WAITING_TEMPLATE.remove(user_id)

    message_text = format_message(data)

    keyboard = [
        [InlineKeyboardButton("✅ Je suis intéressé", callback_data="interested")]
    ]

    sent_message = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.bot_data[sent_message.message_id] = {
        "title": data["TITRE"]
    }

    await update.message.reply_text("✅ Publié dans le groupe.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    message_id = query.message.message_id

    if query.data == "interested":
        keyboard = [
            [
                InlineKeyboardButton(name, callback_data=f"manager_{mid}")
                for mid, name in MANAGERS.items()
            ]
        ]

        await query.message.reply_text(
            "Choisis ton manager :",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("manager_"):
        manager_id = int(query.data.split("_")[1])
        title = context.bot_data.get(message_id, {}).get("title", "opportunité")

        await context.bot.send_message(
            chat_id=manager_id,
            text=f"📩 {user.full_name} est intéressé par : {title}",
        )

        await query.message.reply_text(
            "✅ Le manager a été notifié en privé."
        )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new_opportunity))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()

