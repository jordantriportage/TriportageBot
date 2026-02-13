import re
import sys
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# CONFIGURATION
TOKEN = "8075326221:AAGUWWMNUdvww4-TILy54R8zyZzz--Pvgxc"
ADMIN_IDS = [8493969803]
GROUPE_ID = -5156847371

def start(update, context):
    update.message.reply_text(
        "✅ Bot opérationnel !\n\n"
        "Envoyez une annonce au format :\n"
        "TITRE : ...\n"
        "ORGANISME : ...\n"
        "DATE LIMITE : ...\n"
        "LIEN : ..."
    )

def handle_annonce(update, context):
    # Vérification admin
    if update.effective_user.id not in ADMIN_IDS:
        return

    texte = update.message.text
    
    # Extraction simple
    titre = re.search(r"TITRE\s*:\s*(.+)", texte, re.IGNORECASE)
    organisme = re.search(r"ORGANISME\s*:\s*(.+)", texte, re.IGNORECASE)
    date = re.search(r"DATE LIMITE\s*:\s*(.+)", texte, re.IGNORECASE)
    lien = re.search(r"LIEN\s*:\s*(.+)", texte, re.IGNORECASE)
    
    # Construction du message
    message = "📢 **NOUVEL APPEL D'OFFRES**\n\n"
    message += f"📌 Titre : {titre.group(1).strip() if titre else 'Non spécifié'}\n"
    message += f"🏢 Organisme : {organisme.group(1).strip() if organisme else 'Non spécifié'}\n"
    message += f"📅 Date limite : {date.group(1).strip() if date else 'Non spécifié'}\n"
    message += f"🔗 Lien : {lien.group(1).strip() if lien else 'Non spécifié'}"
    
    # Bouton
    bouton = [[InlineKeyboardButton("✅ JE SUIS INTÉRESSÉ(E)", callback_data="interesse")]]
    
    # Envoi au groupe
    context.bot.send_message(
        chat_id=GROUPE_ID,
        text=message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(bouton)
    )
    
    update.message.reply_text("✅ Publié dans le groupe !")

def handle_button(update, context):
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    nom = user.full_name
    username = f"@{user.username}" if user.username else "pas de pseudo"
    
    # Notification à tous les admins
    for admin_id in ADMIN_IDS:
        context.bot.send_message(
            admin_id,
            f"🔔 Nouvel intérêt !\n\n👤 {nom} ({username})"
        )

def main():
    print("✅ Démarrage du bot...")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_annonce))
    dp.add_handler(CallbackQueryHandler(handle_button, pattern="interesse"))
    
    print("✅ Bot prêt !")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
