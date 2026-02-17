import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# =========================
# ⚙️ CONFIG
# =========================

TOKEN = "7244281986:AAHyQE7rMPElsW77a1LuSrti9ROVXlbCY_M"
GROUP_CHAT_ID = -1003774994419

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    222222222: "Juan BERRIO",
    333333333: "Houda EL BOUHDIDI",
}

WAITING_AO = set()

# =========================
# 🔐 MARKDOWN V2 SAFE
# =========================
def escape_md(text: str):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

# =========================
# 🔎 EXTRACTIONS
# =========================

def extract_tjm(text):
    match = re.search(r"(\d{3,4})\s?€?\s?(max|maximum|min|minimum)?", text, re.IGNORECASE)
    if match:
        tjm = match.group(1)
        suffix = match.group(2)
        if suffix:
            return f"{tjm}€ {suffix}"
        return f"{tjm}€"
    return "Non précisé"

def extract_duration(text):
    match = re.search(r"(minimum|min)?\s?(\d+)\s?(mois|semaines)", text, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        value = match.group(2)
        unit = match.group(3)
        if prefix:
            return f"{value} {unit} minimum"
        return f"{value} {unit}"
    return "Non précisée"

def extract_location(text):
    cities = ["lille", "paris", "idf", "lyon", "marseille", "toulouse", "nantes", "bordeaux"]
    t = text.lower()
    for city in cities:
        if city in t:
            return city.upper()
    return "Non précisée"

def extract_remote(text):
    t = text.lower()
    if "100%" in t and "remote" in t:
        return "100% remote"
    if "remote" in t:
        return "Remote"
    if "hybride" in t:
        return "Hybride"
    if "présentiel" in t or "onsite" in t:
        return "Présentiel"
    return "Non précisé"

def extract_start(text):
    if "asap" in text.lower():
        return "ASAP"
    match = re.search(r"d[ée]marrage\s?:?\s?([\w\s]+)", text, re.IGNORECASE)
    return match.group(1) if match else "Non précisé"

def extract_seniority(text):
    t = text.lower()
    if "senior" in t:
        return "Senior"
    if "lead" in t:
        return "Lead"
    match = re.search(r"(\d\+?)\s?ans", t)
    if match:
        return match.group(1) + " ans"
    return "Non précisée"

def extract_mission(text):
    match = re.search(r"chef de projet[^\n.!]*|développeur[^\n.!]*|data engineer[^\n.!]*|crm[^\n.!]*", text, re.IGNORECASE)
    if match:
        return match.group(0)
    return "Mission IT"

def extract_context(text):
    match = re.search(r"migration[^\n.!]*|projet[^\n.!]*|refonte[^\n.!]*", text, re.IGNORECASE)
    return match.group(0) if match else ""

def extract_tags(text):
    tags = []
    t = text.lower()

    if any(x in t for x in ["crm", "adobe campaign", "salesforce"]):
        tags.append("#CRM")
    if any(x in t for x in ["data", "etl", "power bi"]):
        tags.append("#Data")
    if any(x in t for x in ["aws", "azure", "gcp", "cloud"]):
        tags.append("#Cloud")
    if any(x in t for x in ["cyber", "ssi", "soc"]):
        tags.append("#Cyber")
    if any(x in t for x in ["sap"]):
        tags.append("#SAP")

    return " ".join(tags) if tags else "#IT"

# =========================
# 🧱 BUILD MESSAGE
# =========================

def build_ao_message(raw_text):

    mission = extract_mission(raw_text)
    context = extract_context(raw_text)
    tjm = extract_tjm(raw_text)
    duration = extract_duration(raw_text)
    location = extract_location(raw_text)
    remote = extract_remote(raw_text)
    start = extract_start(raw_text)
    seniority = extract_seniority(raw_text)
    tags = extract_tags(raw_text)

    description = f"{mission}"
    if context:
        description += f" – {context}"

    description = escape_md(description)

    return (
        f"📢 *Nouvelle opportunité*\n\n"
        f"🧾 *Mission* : {description}\n"
        f"📍 *Localisation* : {location}\n"
        f"💰 *TJM* : {tjm}\n"
        f"⏳ *Durée* : {duration}\n"
        f"🚀 *Démarrage* : {start}\n"
        f"🎯 *Séniorité* : {seniority}\n"
        f"🏠 *Remote* : {remote}\n\n"
        f"{escape_md(tags)}\n\n"
        f"👀 *Intéressés* : 0"
    )

# =========================
# 🤖 BOT LOGIC
# =========================

def is_private(update: Update):
    return update.effective_chat.type == "private"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_private(update):
        await update.message.reply_text("Bot AO intelligent opérationnel ✅")

async def new_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    if update.effective_user.id not in MANAGERS:
        await update.message.reply_text("❌ Seuls les managers peuvent publier.")
        return

    WAITING_AO.add(update.effective_user.id)
    await update.message.reply_text("Envoie-moi l’AO brut ✍️")

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
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.bot_data[sent_message.message_id] = {
        "interested_users": [],
        "manager_map": {},
        "text": message_text
    }

    await update.message.reply_text("✅ AO publiée dans le groupe.")

# =========================
# 🔘 BOUTONS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "interested":
        message = query.message
        message_id = message.message_id

        data = context.bot_data.get(message_id)
        if not data:
            return

        if user.id in data["interested_users"]:
            await context.bot.send_message(user.id, "⚠️ Déjà indiqué.")
            return

        data["interested_users"].append(user.id)
        count = len(data["interested_users"])

        new_text = re.sub(r"\*Intéressés\* : \d+", f"*Intéressés* : {count}", data["text"])

        keyboard = [[InlineKeyboardButton(f"✅ Je suis intéressé ({count})", callback_data="interested")]]

        await message.edit_text(
            text=new_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        manager_keyboard = [
            [InlineKeyboardButton(name, callback_data=f"manager|{message_id}|{mid}")]
            for mid, name in MANAGERS.items()
        ]

        await context.bot.send_message(
            chat_id=user.id,
            text="Avec quel manager es-tu en contact ?",
            reply_markup=InlineKeyboardMarkup(manager_keyboard),
        )

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
            await context.bot.send_message(user.id, "⚠️ Manager déjà sélectionné.")
            return

        data["manager_map"][key] = manager_id

        count = sum(1 for m in data["manager_map"].values() if m == manager_id)

        await context.bot.send_message(
            chat_id=manager_id,
            text=f"📩 {user.full_name} est intéressé.\n👥 Intéressés pour toi : {count}"
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
