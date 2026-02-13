import os
import re
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# === CONFIGURATION DE BASE ===
TOKEN = "8075326221:AAGUWWMNUdvww4-TILy54R8zyZzz--Pvgxc"
GROUPE_ID = -5156847371  # ID de votre groupe

# === GESTION DES ADMINISTRATEURS ===
# Admin principal (vous)
ADMIN_PRINCIPAL = 8493969803

# Liste des administrateurs autorisés
# Ajoutez ici les IDs de vos collègues
ADMIN_IDS = [
    8493969803,  # Vous
    # 123456789,  # Collègue 1 (à décommenter et remplacer)
    # 987654321,  # Collègue 2 (à décommenter et remplacer)
]

# === FONCTION POUR VÉRIFIER LES PERMISSIONS ===
def est_admin(user_id):
    """Vérifie si un utilisateur est administrateur"""
    return user_id in ADMIN_IDS

# === FONCTION POUR LE DÉMARRAGE ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if est_admin(user_id):
        await update.message.reply_text(
            "👋 Bienvenue ! Je suis le bot de diffusion d'appels d'offres.\n\n"
            "📝 En tant qu'administrateur, vous pouvez publier une offre en envoyant un message au format :\n\n"
            "TITRE : [titre de l'offre]\n"
            "ORGANISME : [nom de l'organisme]\n"
            "DATE LIMITE : [JJ/MM/AAAA]\n"
            "LIEU : [ville/pays]\n"
            "RÉFÉRENCE : [numéro de marché]\n"
            "DESCRIPTION : \n[description détaillée]\n"
            "LIEN : [URL]"
        )
    else:
        await update.message.reply_text(
            "👋 Bonjour ! Je suis le bot de diffusion d'appels d'offres.\n"
            "Je suis utilisé par les administrateurs pour publier des annonces dans le groupe.\n"
            "Si vous êtes consultant, rendez-vous dans le groupe pour voir les offres disponibles !"
        )

# === COMMANDE POUR LISTER LES ADMINS (réservée à l'admin principal) ===
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Seul l'admin principal peut lister les admins
    if user_id != ADMIN_PRINCIPAL:
        await update.message.reply_text("❌ Cette commande est réservée à l'administrateur principal.")
        return
    
    message = "👥 **Liste des administrateurs :**\n\n"
    for i, admin_id in enumerate(ADMIN_IDS):
        message += f"{i+1}. `{admin_id}`"
        if admin_id == ADMIN_PRINCIPAL:
            message += " 👑 (Principal)"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# === COMMANDE POUR AJOUTER UN ADMIN (réservée à l'admin principal) ===
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Seul l'admin principal peut ajouter des admins
    if user_id != ADMIN_PRINCIPAL:
        await update.message.reply_text("❌ Cette commande est réservée à l'administrateur principal.")
        return
    
    try:
        # Récupérer l'ID du nouvel admin depuis la commande
        nouvel_admin_id = int(context.args[0])
        
        if nouvel_admin_id in ADMIN_IDS:
            await update.message.reply_text("❌ Cet utilisateur est déjà administrateur.")
        else:
            ADMIN_IDS.append(nouvel_admin_id)
            await update.message.reply_text(f"✅ Administrateur {nouvel_admin_id} ajouté avec succès !\n\n"
                                           f"Il peut maintenant publier des annonces.")
    except (IndexError, ValueError):
        await update.message.reply_text(
            "📝 Utilisation : /addadmin [ID_telegram]\n\n"
            "Pour obtenir l'ID d'une personne, elle peut envoyer un message à @userinfobot"
        )

# === COMMANDE POUR SUPPRIMER UN ADMIN (réservée à l'admin principal) ===
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Seul l'admin principal peut supprimer des admins
    if user_id != ADMIN_PRINCIPAL:
        await update.message.reply_text("❌ Cette commande est réservée à l'administrateur principal.")
        return
    
    # Protection : on ne peut pas supprimer le dernier admin
    if len(ADMIN_IDS) <= 1:
        await update.message.reply_text("❌ Impossible de supprimer le dernier administrateur.")
        return
    
    try:
        admin_a_supprimer = int(context.args[0])
        
        if admin_a_supprimer not in ADMIN_IDS:
            await update.message.reply_text("❌ Cet ID n'est pas dans la liste des administrateurs.")
        elif admin_a_supprimer == ADMIN_PRINCIPAL:
            await update.message.reply_text("❌ Impossible de supprimer l'administrateur principal.")
        else:
            ADMIN_IDS.remove(admin_a_supprimer)
            await update.message.reply_text(f"✅ Administrateur {admin_a_supprimer} supprimé.")
    except (IndexError, ValueError):
        await update.message.reply_text("📝 Utilisation : /removeadmin [ID_telegram]")

# === TRAITEMENT DES ANNONCES ===
async def traiter_annonce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Vérifier que l'utilisateur est administrateur
    if not est_admin(user_id):
        await update.message.reply_text("❌ Désolé, vous n'êtes pas autorisé à publier des annonces.")
        return
    
    # Confirmation de réception
    await update.message.reply_text("✅ Message reçu, je tente la publication...")
    
    texte = update.message.text
    
    # Extraire les informations avec des expressions régulières
    titre = re.search(r"TITRE\s*:\s*(.+)", texte, re.IGNORECASE)
    organisme = re.search(r"ORGANISME\s*:\s*(.+)", texte, re.IGNORECASE)
    date = re.search(r"DATE LIMITE\s*:\s*(.+)", texte, re.IGNORECASE)
    lieu = re.search(r"LIEU\s*:\s*(.+)", texte, re.IGNORECASE)
    reference = re.search(r"RÉFÉRENCE\s*:\s*(.+)", texte, re.IGNORECASE)
    description = re.search(r"DESCRIPTION\s*:\s*(.+)", texte, re.IGNORECASE | re.DOTALL)
    lien = re.search(r"LIEN\s*:\s*(.+)", texte, re.IGNORECASE)
    
    # Construire le message formaté
    message_annonce = f"""📢 <b>NOUVEL APPEL D'OFFRES</b>

📌 <b>Titre</b> : {titre.group(1).strip() if titre else "Non spécifié"}
🏢 <b>Organisme</b> : {organisme.group(1).strip() if organisme else "Non spécifié"}
📅 <b>Date limite</b> : {date.group(1).strip() if date else "Non spécifié"}
📍 <b>Lieu</b> : {lieu.group(1).strip() if lieu else "Non spécifié"}
🔖 <b>Référence</b> : {reference.group(1).strip() if reference else "Non spécifié"}

📝 <b>Description</b> :
{description.group(1).strip() if description else "Non spécifiée"}

🔗 <b>Lien</b> : <a href='{lien.group(1).strip() if lien else "#"}'>{lien.group(1).strip() if lien else "Non spécifié"}</a>

👤 <i>Publié par : {update.effective_user.full_name}</i>"""

    # Créer le bouton d'intérêt
    bouton = [[InlineKeyboardButton("✅ JE SUIS INTÉRESSÉ(E)", callback_data="interesse")]]
    reply_markup = InlineKeyboardMarkup(bouton)
    
    try:
        # Envoyer au groupe
        await context.bot.send_message(
            chat_id=GROUPE_ID,
            text=message_annonce,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        # Confirmer à l'administrateur
        await update.message.reply_text("✅ Annonce publiée dans le groupe !")
    except Exception as e:
        # En cas d'erreur, prévenir l'admin
        await update.message.reply_text(f"❌ Erreur lors de la publication : {e}")

# === GESTION DES CLICS SUR LE BOUTON ===
async def gestion_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Récupérer les infos de l'utilisateur qui a cliqué
    user = query.from_user
    nom = user.full_name
    username = f"@{user.username}" if user.username else "pas de pseudo"
    user_id = user.id
    
    # Récupérer le message original (l'annonce)
    message_original = query.message.text
    # Extraire un aperçu du titre
    titre_match = re.search(r"Titre\s*:\s*(.+)", message_original)
    titre_annonce = titre_match.group(1) if titre_match else "Annonce inconnue"
    
    # Construire le message de notification
    notification = (f"🔔 <b>Nouvel intérêt !</b>\n\n"
                    f"👤 <b>{nom}</b> ({username})\n"
                    f"🆔 ID: {user_id}\n\n"
                    f"📌 <b>Annonce :</b> {titre_annonce}\n\n"
                    f"💬 <a href='https://t.me/{user.username if user.username else ""}'>Contacter sur Telegram</a>")
    
    # Envoyer une notification à TOUS les administrateurs
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification,
                parse_mode="HTML"
            )
        except:
            # Si un admin a bloqué le bot, on ignore l'erreur
            pass

# === FONCTION PRINCIPALE ===
def main():
    # Créer l'application
    app = Application.builder().token(TOKEN).build()
    
    # Commandes publiques
    app.add_handler(CommandHandler("start", start))
    
    # Commandes de gestion des admins (réservées à l'admin principal)
    app.add_handler(CommandHandler("listadmins", list_admins))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    
    # Gestion des messages texte (annonces)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_annonce))
    
    # Gestion des clics sur les boutons
    app.add_handler(CallbackQueryHandler(gestion_bouton, pattern="interesse"))
    
    # Démarrer le bot
    print("🤖 Bot démarré...")
    print(f"👥 Administrateurs : {len(ADMIN_IDS)}")
    app.run_polling()

if __name__ == "__main__":
    main()
    )

# === FONCTION PRINCIPALE ===
def main():
    # Créer l'application
    app = Application.builder().token(TOKEN).build()
    
    # Ajouter les gestionnaires
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_annonce))
    app.add_handler(CallbackQueryHandler(gestion_bouton, pattern="interesse"))
    
    # Démarrer le bot
    print("🤖 Bot démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()