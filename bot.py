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

TOKEN = "7244281986:AAHyQE7rMPElsW77a1LuSrti9ROVXlbCY_M"
GROUP_CHAT_ID = -1003774994419

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    222222222: "Juan BERRIO",
    333333333: "Houda EL BOUHDIDI",
}

# =========================
# 🔐 MARKDOWN SAFE
# =========================
def escape_markdown(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

# =========================
# 🔎 EXTRACTION DATA
# =========================
def extract_tjm(text):
    match = re.search(r"(\d{3,4})\s?€?\s?/?\s?(j|jour)", text, re.IGNORECASE)
    return match.group(1) + "€" if match else "Non précisé"

def extract_duration(text):
    match = re.search(r"(\d+)\s?(mois|semaines)", text, re.IGNORECASE)
    return match.group(0) if match else "Non précisée"

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

    if not tags:
        tags = ["#Autre"]

    # 🔐 échappe les hashtags pour MarkdownV2
    tags = [escape_markdown(tag) for tag in tags]

    return " ".join(tags)

def smart_summary(text, max_lines=5):
    lines = text.split("\n")

    clean_lines = []

    for line in lines:
        l = line.strip()

        # ❌ supprimer blabla RH / marketing
        if any(x in l.lower() for x in [
            "café", "excellente semaine", "je suis preneuse",
            "envie de relever", "croyez moi", "💪", "☕", "🔥"
        ]):
            continue

        # garder seulement les lignes utiles
        if any(x in l.lower() for x in [
            "mission", "profil", "compétence", "durée", "tjm",
            "démarrage", "localisation", "lieu", "remote",
            "adobe", "imagino", "crm", "data", "cloud"
        ]):
            clean_lines.append(l)

    # fallback si rien détecté
    if not clean_lines:
        clean_lines = lines

    summary = "\n".join(clean_lines[:max_lines])

    return summary

def build_ao_message(raw_text):
    tjm = extract_tjm(raw_text)
    duration = extract_duration(raw_text)
    remote = extract_remote(raw_text)
    tags = extract_tags(raw_text)
    summary = escape_markdown(smart_summary(raw_text))

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

# 📩 Réception directe d’un AO par un manager
async def handle_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    user_id = update.effective_user.id

    if user_id not in MANAGERS:
        await update.message.reply_text("❌ Seuls les managers peuvent publier des AO.")
        return

    raw_text = update.message.text

    message_text = build_ao_message(raw_text)

    keyboard = [[InlineKeyboardButton("✅ Je suis intéressé", callback_data="interested")]]

    sent_message = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.bot_data[sent_message.message_id] = {
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

    # 👉 CLIC INTERESSE
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

        await context.bot.send_message(
            chat_id=user.id,
            text=message.text,
            parse_mode="MarkdownV2"
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

    # 👉 CHOIX MANAGER
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

        count = sum(1 for m in data["manager_map"].values() if m == manager_id)

        await context.bot.send_message(
            chat_id=manager_id,
            text=f"📩 {user.full_name} est intéressé par l’AO.\n👥 Intéressés pour toi : {count}"
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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ao))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    app.run_polling()


