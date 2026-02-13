import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# === CONFIGURATION ===
TOKEN = "8075326221:AAGUWWMNUdvww4-TILy54R8zyZzz--Pvgxc"
ADMIN_IDS = [8493969803]  # Votre ID
GROUPE_ID = -5156847371  # ID du groupe

# === FONCTION START ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "✅ Bot opérationnel !\n\n"
        "Envoyez une annonce au format :\n"
        "TITRE : [titre]\n"
        "ORGANISME : [organisme]\n"
        "DATE LIMITE : [JJ/MM/AAAA]\n"
        "LIEU : [ville]\n"
        "RÉFÉRENCE : [référence]\n"
        "DESCRIPTION : \n[description]\n"
        "LIEN : [URL]"
    )

# === TRAITEMENT DES ANNONCES ===
def traiter_annonce(update: Update, context: CallbackContext):
    # Vérification admin
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Accès refusé.")
        return

    texte = update.message.text
    
    # Extraction des informations
    titre = re.search(r"TITRE\s*:\s*(.+)", texte, re.IGNORECASE)
    organisme = re.search(r"ORGANISME\s*:\s*(.+)", texte, re.IGNORECASE)
    date = re.search(r"DATE LIMITE\s*:\s*(.+)", texte, re.IGNORECASE)
    lieu = re.search(r"LIEU\s*:\s*(.+)", texte, re.IGNORECASE)
    reference = re.search(r"RÉFÉRENCE\s*:\s*(.+)", texte, re.IGNORECASE)
    description = re.search(r"DESCRIPTION\s*:\s*(.+)", texte, re.IGNORECASE | re.DOTALL)
    lien = re.search(r"LIEN\s*:\s*(.+)", texte, re.IGNORECASE)
    
    # Construction du message formaté
    message = f"📢 NOUVEL APPEL D'OFFRES\n\n"
    message += f"📌 Titre : {titre.group(1).strip() if titre else 'Non spécifié'}\n"
    message += f"🏢 Organisme : {organisme.group(1).strip() if organisme else 'Non spécifié'}\n"
    message += f"📅 Date limite : {date.group(1).strip() if date else 'Non spécifié'}\n"
    message += f"📍 Lieu : {lieu.group(1).strip() if lieu else 'Non spécifié'}\n"
    message += f"🔖 Référence : {reference.group(1).strip() if reference else 'Non spécifié'}\n\n"
    message += f"📝 Description :\n{description.group(1).strip() if description else 'Non spécifiée'}\n\n"
    message += f"🔗 Lien : {lien.group(1).strip() if lien else 'Non spécifié'}\n\n"
    message += f"👤 Publié par : {update.effective_user.full_name}"
    
    # Création du bouton
    bouton = [[InlineKeyboardButton("✅ JE SUIS INTÉRESSÉ(E)", callback_data="interesse")]]
    reply_markup = InlineKeyboardMarkup(bouton)
    
    try:
        # Envoi au groupe
        context.bot.send_message(
            chat_id=GROUPE_ID,
            text=message,
            reply_markup=reply_markup
        )
        update.message.reply_text("✅ Annonce publiée dans le groupe !")
    except Exception as e:
        update.message.reply_text(f"❌ Erreur : {e}")

# === GESTION DES CLICS SUR BOUTON ===
def gestion_bouton(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    nom = user.full_name
    username = f"@{user.username}" if user.username else "pas de pseudo"
    
    # Notification à tous les admins
    for admin_id in ADMIN_IDS:
        try:
            context.bot.send_message(
                admin_id,
                f"🔔 Nouvel intérêt !\n\n"
                f"👤 {nom} ({username})\n"
                f"📌 Annonce : {query.message.text.split(chr(10))[1]}"
            )
        except:
            pass

# === MAIN ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, traiter_annonce))
    dp.add_handler(CallbackQueryHandler(gestion_bouton, pattern="interesse"))
    
    print("✅ Bot démarré avec succès !")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
