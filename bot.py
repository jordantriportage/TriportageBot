import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# === CONFIGURATION ===
TOKEN = "8075326221:AAGUWWMNUdvww4-TILy54R8zyZzz--Pvgxc"
ADMIN_IDS = [8493969803]  # Votre ID
GROUPE_ID = -5156847371  # ID du groupe

# === FONCTION START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot opérationnel !\n\n"
        "Envoyez une annonce au format :\n"
        "TITRE : ...\n"
        "ORGANISME : ...\n"
        "DATE LIMITE : ...\n"
        "LIEU : ...\n"
        "RÉFÉRENCE : ...\n"
        "DESCRIPTION : ...\n"
        "LIEN : ..."
    )

# === TRAITEMENT DES ANNONCES ===
async def traiter_annonce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Vérification admin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return

    texte = update.message.text
    
    # Extraction simple
    titre = re.search(r"TITRE\s*:\s*(.+)", texte, re.IGNORECASE)
    organisme = re.search(r"ORGANISME\s*:\s*(.+)", texte, re.IGNORECASE)
    date = re.search(r"DATE LIMITE\s*:\s*(.+)", texte, re.IGNORECASE)
    lien = re.search(r"LIEN\s*:\s*(.+)", texte, re.IGNORECASE)
    
    # Construction message
    message = f"📢 NOUVEL APPEL D'OFFRES\n\n"
    message += f"📌 Titre : {titre.group(1) if titre else 'Non spécifié'}\n"
    message += f"🏢 Organisme : {organisme.group(1) if organisme else 'Non spécifié'}\n"
    message += f"📅 Date limite : {date.group(1) if date else 'Non spécifié'}\n"
    message += f"🔗 Lien : {lien.group(1) if lien else 'Non spécifié'}"
    
    # Bouton
    bouton = [[InlineKeyboardButton("✅ JE SUIS INTÉRESSÉ(E)", callback_data="interesse")]]
    
    # Envoi au groupe
    await context.bot.send_message(
        chat_id=GROUPE_ID,
        text=message,
        reply_markup=InlineKeyboardMarkup(bouton)
    )
    
    await update.message.reply_text("✅ Publié !")

# === GESTION BOUTON ===
async def gestion_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            admin_id,
            f"🔔 {user.full_name} (@{user.username}) est intéressé !"
        )

# === MAIN ===
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_annonce))
    app.add_handler(CallbackQueryHandler(gestion_bouton, pattern="interesse"))
    print("✅ Bot démarré avec succès !")
    app.run_polling()

if __name__ == "__main__":
    main()
