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

TOKEN = "7244281986:AAHyQE7rMPElsW77a1LuSrti9ROVXlbCY_M"

GROUP_CHAT_ID = -1003774994419  # 🔴 ID du groupe

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    222222222: "Juan BERRIO",
    333333333: "Houda EL BOUHDIDI",
}

WAITING_TEMPLATE = set()
user_manager_choice = {}
TEMPLATE_FIELDS = [
    "TITRE",
    "ORGANISME",
    "DATE LIMITE",
    "LIEU",
    "DESCRIPTION",
    "LIEN",
]

async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID : {chat.id}")

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
    "title": data["TITRE"],
    "interested_users": []
    }

    await update.message.reply_text("✅ Publié dans le groupe.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # 👉 Clic sur "Je suis intéressé"
    if query.data == "interested":
        message = query.message
        message_id = message.message_id

        data = context.bot_data.get(message_id)

        if not data:
            return

        if "interested_users" not in data:
            data["interested_users"] = []

        if user.id in data["interested_users"]:
            await context.bot.send_message(
                chat_id=user.id,
                text="⚠️ Tu as déjà indiqué ton intérêt pour cette opportunité."
            )
            return

        data["interested_users"].append(user.id)

        count = len(data["interested_users"])

        keyboard = [
            [InlineKeyboardButton(f"✅ Je suis intéressé ({count})", callback_data="interested")]
        ]

        await message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # 📩 Envoi du détail en privé
        await context.bot.send_message(
            chat_id=user.id,
            text=message.text,
            parse_mode="Markdown"
        )

        # 🎯 Boutons choix manager en privé
        manager_keyboard = [
            [
                InlineKeyboardButton(name, callback_data=f"manager|{message_id}|{mid}")
                for mid, name in MANAGERS.items()
            ]
        ]

        await context.bot.send_message(
            chat_id=user.id,
            text="Avec quel manager es-tu en contact ?",
            reply_markup=InlineKeyboardMarkup(manager_keyboard),
        )

    # 👉 Choix du manager (vient du PRIVÉ)
    elif query.data.startswith("manager|"):
        parts = query.data.split("|")

        msg_id = int(parts[1])
        manager_id = int(parts[2])
        manager_name = MANAGERS.get(manager_id, "Manager")

        key = f"{user.id}_{msg_id}"

        if "manager_choices" not in context.bot_data:
        context.bot_data["manager_choices"] = {}

        if key in context.bot_data["manager_choices"]:
            await context.bot.send_message(
                chat_id=user.id,
                text="⚠️ Tu as déjà sélectionné un manager pour cette opportunité."
            )
            return
            
    # 🔒 On enregistre le choix
    context.bot_data["manager_choices"][key] = manager_id

    title = context.bot_data.get(msg_id, {}).get("title", "opportunité")

     # 📩 Message au manager
    await context.bot.send_message(
        chat_id=manager_id,
        text=f"📩 {user.full_name} est intéressé par : {title}",
    )

    # ✅ Confirmation consultant
    await context.bot.send_message(
        chat_id=user.id,
        text=f"✅ Le manager {manager_name} a été notifié."
    )
    

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new_opportunity))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("groupid", get_group_id))


if __name__ == "__main__":
    app.run_polling()



















