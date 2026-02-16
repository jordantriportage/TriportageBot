from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================

TOKEN = "7244281986:AAF_ojoZVFL6fG41j01ckDcDsBGYJ592c6Q"
GROUP_ID = -5156847371

MANAGERS = {8493969803}

user_states = {}
opportunities = {}        # opp_id -> text
interests = {}            # opp_id -> set(user_ids)
message_map = {}          # opp_id -> group_message_id

# =====================
# /start
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in MANAGERS:
        await update.message.reply_text(
            "👔 Espace Manager prêt.\nUtilisez /new pour publier une opportunité."
        )
    else:
        await update.message.reply_text(
            "👤 Espace Consultant prêt.\nCliquez sur 'Je suis intéressé' dans le groupe."
        )

# =====================
# /new (managers only)
# =====================

async def new_opportunity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in MANAGERS:
        await update.message.reply_text("❌ Non autorisé.")
        return

    user_states[user_id] = "WAITING_TEMPLATE"

    await update.message.reply_text(
        "Merci d'envoyer l'appel d'offres au format :\n\n"
        "Client:\nMission:\nLocalisation:\nDurée:\nTJM:\nDeadline:\n\n"
        "Envoyez tout en un seul message."
    )

# =====================
# TEMPLATE RECEPTION
# =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "WAITING_TEMPLATE":
        return

    text = update.message.text

    if "Client:" not in text:
        await update.message.reply_text("❌ Format invalide. Merci de renvoyer le template.")
        return

    opp_id = update.message.message_id
    opportunities[opp_id] = text
    interests[opp_id] = set()

    formatted = f"📢 *NOUVEL APPEL D’OFFRES*\n\n{text}\n\n👥 Intéressés : 0"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Je suis intéressé", callback_data=f"interested_{opp_id}")]]
    )

    msg = await context.bot.send_message(
        chat_id=GROUP_ID,
        text=formatted,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    message_map[opp_id] = msg.message_id

    await update.message.reply_text("✅ Opportunité publiée dans le groupe.")

    user_states.pop(user_id)

# =====================
# CLICK "INTERESSE"
# =====================

async def interested(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    await query.answer()

    # ❌ empêcher les managers
    if user_id in MANAGERS:
        await query.answer("❌ Réservé aux consultants", show_alert=True)
        return

    # ✅ vérifier membre du groupe
    member = await context.bot.get_chat_member(GROUP_ID, user_id)
    if member.status in ["left", "kicked"]:
        await query.answer("❌ Vous devez être membre du groupe", show_alert=True)
        return

    opp_id = int(query.data.split("_")[1])

    # ❌ anti double clic
    if user_id in interests.get(opp_id, set()):
        await query.answer("⚠️ Vous avez déjà manifesté votre intérêt", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("Manager 1", callback_data=f"choose_{opp_id}_11111111")],
        [InlineKeyboardButton("Manager 2", callback_data=f"choose_{opp_id}_22222222")],
    ]

    await query.message.reply_text(
        "Choisissez votre Commercial Manager :",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# =====================
# CHOIX MANAGER
# =====================

async def choose_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    await query.answer()

    _, opp_id, manager_id = query.data.split("_")
    opp_id = int(opp_id)
    manager_id = int(manager_id)

    # anti double clic sécurité
    if user_id in interests.get(opp_id, set()):
        await query.answer("⚠️ Déjà enregistré", show_alert=True)
        return

    interests[opp_id].add(user_id)

    opp_text = opportunities.get(opp_id, "Opportunité")

    # 🔔 notif manager
    await context.bot.send_message(
        chat_id=manager_id,
        text=(
            "🔔 Nouveau consultant intéressé\n\n"
            f"👤 Consultant : {user.full_name}\n"
            f"🆔 ID : {user.id}\n\n"
            f"{opp_text}"
        ),
    )

    # ✅ confirmation consultant
    await query.message.reply_text(
        "✅ Ton intérêt a été envoyé.\nLe manager a bien été notifié."
    )

    # 🔄 mise à jour compteur dans le groupe
    count = len(interests[opp_id])
    new_text = f"📢 *NOUVEL APPEL D’OFFRES*\n\n{opp_text}\n\n👥 Intéressés : {count}"

    await context.bot.edit_message_text(
        chat_id=GROUP_ID,
        message_id=message_map[opp_id],
        text=new_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Je suis intéressé", callback_data=f"interested_{opp_id}")]]
        ),
    )

# =====================
# MAIN
# =====================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("new", new_opportunity))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(interested, pattern=r"^interested_"))
app.add_handler(CallbackQueryHandler(choose_manager, pattern=r"^choose_"))

app.run_polling()
