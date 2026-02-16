import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "TON_TOKEN_ICI"
GROUP_CHAT_ID = -1003774994419

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    222222222: "Juan BERRIO",
    333333333: "Houda EL BOUHDIDI",
}

WAITING_AO = set()

# =========================
# 🔎 ANALYSE INTELLIGENTE AO
# =========================

def extract_tjm(text):
    match = re.search(r"(\d{3,4})\s?€?\s?/?\s?(j|jour)", text, re.IGNORECASE)
    return match.group(1) + "€" if match else "Non précisé"

def extract_duration(text):
    match = re.search(r"(\d+)\s?(mois|semaines)", text, re.IGNORECASE)
    return match.group(0) if match else "Non précisée"

def extract_remote(text):
    text = text.lower()
    if "100%" in text and "remote" in text:
        return "100% remote"
    if "remote" in text:
        return "Remote"
    if "hybride" in text:
        return "Hybride"
    if "présentiel" in text or "onsite" in text:
        return "Présentiel"
    return "Non précisé"

def extract_tags(text):
    tags = []
    t = text.lower()

    if any(x in t for x in ["data", "bi", "etl", "power bi"]):
        tags.append("#Data")
    if "sap" in t:
        tags.append("#SAP")
    if any(x in t for x in ["cyber", "ssi", "soc"]):
        tags.append("#Cyber")
    if any(x in t for x in ["cloud", "aws", "azure", "gcp"]):
        tags.append("#Cloud")
    if any(x in t for x in ["dev", "développeur", "python", "java"]):
        tags.append("#Dev")
    if "pmo" in t:
        tags.append("#PMO")
    if any(x in t for x in ["qa", "test"]):
        tags.append("#QA")
    if any(x in t for x in ["infra", "système", "réseau"]):
        tags.append("#Infra")

    return " ".join(tags) if tags else "#Autre"

def smart_summary(text, max_sentences=3):
    sentences = re.split(r'(?<=[.!?]) +', text)
    return " ".join(sentences[:max_sentences])

def build_ao_message(raw_text):
    tjm = extract_tjm(raw_text)
    duration = extract_duration(raw_text)
    remote = extract_remote(raw_text)
    tags = extract_tags(raw_text)
    summary = smart_summary(raw_text)

    return (
        f"📢 *Nouvelle opportunité*\n\n"
        f"💰 *TJM* : {tjm}\n"
        f"⏳ *Durée* : {duration}\n"
        f"🏠 *Mode* : {remote}\n\n"
        f"📝 *Résumé* :\n{summary}\n\n"
        f"{tags}"
    )

# =========================
# 🧠 BOT LOGIC
# =========================

def is_private(update: Update):
    return update.effective_chat.type == "private"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return
    await update.message.reply_text("Bot AO opérationnel ✅")

async def new_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    user_id = update.effective_user.id

    if user_id not in MANAGERS:
        await update.message.reply_text("❌ Seuls les managers peuvent publier.")
        return

    WAITING_AO.add(user_id)
    await update.message.reply_text("Envoie-moi l’appel d’offre brut ✍️")

async def handle_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    user_id = update.effective_user.id

    if user_id not in WAITING_AO:
        return

    WAITING_AO.remove(user_id)

    message_text = build_ao_message(update.message.text)

    keyboard = [[InlineKeyboardButton("✅ Je suis intéressé", callback_data="interested")]]

    sent_message = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.bot_data[sent_message.message_id] = {
        "title": "AO",
        "interested_users": [],
        "manager_map": {}
    }

    await update.message.reply_text("✅ AO publiée dans le groupe.")

# =========================
# 🔘 BOUTONS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # =====================
    # CLIC INTERESSE
    # =====================
    if query.data == "interested":
        message = query.message
        message_id = message.message_id

        data = context.bot_data.get(message_id)
        if not data:
            return

        if user.id in data["interested_users"]:
            await context.bot.send_message(
                chat_id=user.id,
                text="⚠️ Tu as déjà indiqué ton intérêt."
            )
            return

        data["interested_users"].append(user.id)
        count = len(data["interested_users"])

        keyboard = [[InlineKeyboardButton(f"✅ Je suis intéressé ({count})", callback_data="interested")]]

        await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

        await context.bot.send_message(chat_id=user.id, text=message.text, parse_mode="Markdown")

        manager_keyboard = [
            [InlineKeyboardButton(name, callback_data=f"manager|{message_id}|{mid}")]
            for mid, name in MANAGERS.items()
        ]

        await context.bot.send_message(
            chat_id=user.id,
            text="Avec quel manager es-tu en contact ?",
            reply_markup=InlineKeyboardMarkup(manager_keyboard),
        )

    # =====================
    # CHOIX MANAGER
    # =====================
    elif query.data.startswith("manager|"):
        parts = query.data.split("|")
        msg_id = int(parts[1])
        manager_id = int(parts[2])
        manager_name = MANAGERS.get(manager_id, "Manager")

        data = context.bot_data.get(msg_id)
        if not data:
            return

        key = f"{user.id}_{msg_id}"

        if key in data["manager_map"]:
            await context.bot.send_message(
                chat_id=user.id,
                text="⚠️ Manager déjà sélectionné pour cette AO."
            )
            return

        data["manager_map"][key] = manager_id

        # 📩 Liste des intéressés pour ce manager
        interested_names = []
        for uid, mid in data["manager_map"].items():
            if mid == manager_id:
                interested_names.append(uid.split("_")[0])

        await context.bot.send_message(
            chat_id=manager_id,
            text=f"📩 {user.full_name} est intéressé par l’AO.\n\n👥 Intéressés pour toi : {len(interested_names)}"
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=f"✅ Le manager {manager_name} a été notifié."
        )

# =========================
# 🚀 RUN
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new_ao))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ao))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()
