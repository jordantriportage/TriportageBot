import re
import os
import uuid
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

# =========================
# ⚙️ CONFIG
# =========================

TOKEN = os.getenv("TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

client = OpenAI(api_key=OPENAI_API_KEY)

MANAGERS = {
    8493969803: "Jordan DIOCHOT",
    6432931206: "Juan BERRIO",
    8578401455: "Houda EL BOUHDIDI",
}

WAITING_AO = set()

# =========================
# 🔐 MARKDOWN SAFE
# =========================

def escape_md(text: str):
    if not text:
        return ""
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))

# =========================
# 🧠 OPENAI ANALYSE UNIQUE
# =========================

async def analyze_ao_with_ai(raw_text):

    prompt = f"""
Tu es un recruteur IT.

Analyse cette mission et retourne un JSON STRICT avec ces champs :

summary : résumé en 2 phrases max (role + techno + contexte)
tjm : TJM ou "Non précisé"
duration : durée ou "Non précisée"
location : ville ou "Non précisée"
remote : "100% remote", "Remote", "Hybride", "Présentiel" ou "Non précisé"
seniority : niveau ou années d'expérience ou "Non précisée"
start : date de démarrage ou "ASAP" ou "Non précisé"
tags : liste de 2 à 4 hashtags sans accents (ex: ["#Data", "#AWS"])

Mission :
{raw_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)

        return {
            "summary": data.get("summary", "Non précisé"),
            "tjm": data.get("tjm", "Non précisé"),
            "duration": data.get("duration", "Non précisée"),
            "location": data.get("location", "Non précisée"),
            "remote": data.get("remote", "Non précisé"),
            "seniority": data.get("seniority", "Non précisée"),
            "start": data.get("start", "Non précisé"),
            "tags": " ".join(data.get("tags", ["#IT"])),
        }

    except Exception as e:
        print("Erreur analyse AI :", e)

        return {
            "summary": raw_text[:150],
            "tjm": "Non précisé",
            "duration": "Non précisée",
            "location": "Non précisée",
            "remote": "Non précisé",
            "seniority": "Non précisée",
            "start": "Non précisé",
            "tags": "#IT",
        }

# =========================
# 🧱 BUILD MESSAGE
# =========================

async def build_ao_message(raw_text):

    data = await analyze_ao_with_ai(raw_text)
    reference = str(uuid.uuid4())[:8].upper()

    message = (
        f"📢 *Nouvelle opportunité* \\- Ref : *{escape_md(reference)}*\n\n"
        f"📝 *Mission* : {escape_md(data['summary'])}\n"
        f"📍 *Localisation* : {escape_md(data['location'])}\n"
        f"💰 *TJM* : {escape_md(data['tjm'])}\n"
        f"⏳ *Durée* : {escape_md(data['duration'])}\n"
        f"🚀 *Démarrage* : {escape_md(data['start'])}\n"
        f"🎯 *Séniorité* : {escape_md(data['seniority'])}\n"
        f"🏠 *Remote* : {escape_md(data['remote'])}\n\n"
        f"{escape_md(data['tags'])}\n\n"
        f"👀 *Intéressés* : 0"
    )

    return message, reference

# =========================
# 🤖 COMMANDES
# =========================

def is_private(update: Update):
    return update.effective_chat.type == "private"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_private(update):
        await update.message.reply_text("Bot AO intelligent opérationnel ✅")

async def new_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in MANAGERS:
        await update.message.reply_text("❌ Seuls les managers peuvent publier.")
        return

    WAITING_AO.add(update.effective_user.id)
    await update.message.reply_text("Envoie-moi l’AO brut ✍️")

# =========================
# 📩 RECEPTION AO
# =========================

async def handle_ao(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id not in WAITING_AO:
        return

    WAITING_AO.remove(user_id)

    message_text, reference = await build_ao_message(update.message.text)

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
        "text": message_text,
        "reference": reference,
    }

    await update.message.reply_text(f"✅ AO publiée \\- Ref : {escape_md(reference)}", parse_mode="MarkdownV2")

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

        new_text = re.sub(
            r"\*Intéressés\* : \d+",
            f"*Intéressés* : {count}",
            data["text"],
        )

        keyboard = [[InlineKeyboardButton(f"✅ Je suis intéressé ({count})", callback_data="interested")]]

        await message.edit_text(
            text=new_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        manager_keyboard = [
            [InlineKeyboardButton(name, callback_data=f"manager|{message_id}|{mid}")]
            for mid, name in MANAGERS.items()
        ]

        await context.bot.send_message(
            chat_id=user.id,
            text=f"📌 Référence : {escape_md(data['reference'])}\nAvec quel manager es-tu en contact ?",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(manager_keyboard),
        )

    elif query.data.startswith("manager|"):

        parts = query.data.split("|")
        msg_id = int(parts[1])
        manager_id = int(parts[2])

        data = context.bot_data.get(msg_id)
        if not data:
            return

        key = f"{user.id}_{msg_id}"

        if key in data["manager_map"]:
            await context.bot.send_message(user.id, "⚠️ Déjà envoyé à ce manager.")
            return

        data["manager_map"][key] = manager_id

        count_for_manager = sum(
            1 for m in data["manager_map"].values() if m == manager_id
        )

        await context.bot.send_message(
            chat_id=manager_id,
            text=(
                f"📩 *Nouveau consultant intéressé*\n\n"
                f"👤 Nom : {escape_md(user.full_name)}\n"
                f"📌 Référence : {escape_md(data['reference'])}\n"
                f"👥 Intéressés pour toi : {count_for_manager}"
            ),
            parse_mode="MarkdownV2",
        )

        await context.bot.send_message(
            chat_id=user.id,
            text="✅ Le manager a été notifié.",
        )

# =========================
# ❗ ERROR HANDLER
# =========================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Exception:", context.error)

# =========================
# 🚀 RUN
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_error_handler(error_handler)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new_ao))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ao))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()
