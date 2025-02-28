import os
import uuid
import logging
from datetime import datetime
import telebot
from telebot import types
from sqlite3 import connect, Row

# Configuration directe
TOKEN = "8090189100:AAEE5d9OZ9Mqh8vl7h-g6fvLPwWBb4pSQYQ"
ADMIN_IDS = [7148392834]  # ⚠️ Remplacez par votre ID (pour certaines commandes)
DB_NAME = "files.db"
NAME_INPUT = 1

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialisation du bot
bot = telebot.TeleBot(TOKEN)

# Base de données (création des tables pour les fichiers et les utilisateurs)
def init_db():
    with connect(DB_NAME) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS files
            (id TEXT PRIMARY KEY,
            file_id TEXT,
            file_type TEXT,
            file_name TEXT,
            uploader_id INTEGER,
            timestamp DATETIME)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            updated_at DATETIME)"""
        )
        conn.commit()

def add_file(file_id, tg_file_id, file_type, file_name, uploader_id):
    with connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO files VALUES (?,?,?,?,?,?)",
            (file_id, tg_file_id, file_type, file_name, uploader_id, datetime.now()),
        )
        conn.commit()

def get_file(file_id):
    with connect(DB_NAME) as conn:
        conn.row_factory = Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM files WHERE id=?", (file_id,))
        return cur.fetchone()

def get_all_files():
    with connect(DB_NAME) as conn:
        conn.row_factory = Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM files ORDER BY timestamp DESC")
        return cur.fetchall()

def delete_file(file_id):
    with connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
        return cur.rowcount > 0

# Fonctions pour la gestion des utilisateurs
def register_user(user):
    with connect(DB_NAME) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at) VALUES (?,?,?,?,?)",
            (user.id, user.username, user.first_name, user.last_name, datetime.now()),
        )
        conn.commit()

def get_all_users():
    with connect(DB_NAME) as conn:
        conn.row_factory = Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY updated_at DESC")
        return cur.fetchall()

def get_user(user_id):
    with connect(DB_NAME) as conn:
        conn.row_factory = Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return cur.fetchone()

# Handlers
@bot.message_handler(commands=["start"])
def start(update):
    register_user(update.from_user)
    args = update.text.split()
    if len(args) > 1:
        file_id = args[1]
        if file_data := get_file(file_id):
            caption = f"📤 {file_data['file_name']}"
            if file_data["file_type"] == "photo":
                bot.send_photo(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "document":
                bot.send_document(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "video":
                bot.send_video(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "audio":
                bot.send_audio(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "animation":
                bot.send_animation(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "voice":
                bot.send_voice(update.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "video_note":
                bot.send_video_note(update.chat.id, file_data["file_id"])
            elif file_data["file_type"] == "sticker":
                bot.send_sticker(update.chat.id, file_data["file_id"])
        else:
            bot.send_message(update.chat.id, "❌ Fichier introuvable")
    else:
        bot.send_message(update.chat.id, "🌟 Envoyez-moi un fichier pour commencer !")
    
    # Envoi de la liste des commandes disponibles
    commands_list = (
        "📋 Commandes disponibles :\n"
        "/start - Démarrer le bot\n"
        "/share - Partager un fichier\n"
        "/sendtext - Envoyer un message à un utilisateur\n"
        "/listusers - Voir tous les utilisateurs enregistrés\n"
        "/delete - Supprimer un fichier (admin seulement)"
    )
    bot.send_message(update.chat.id, commands_list)

@bot.message_handler(commands=["share"])
def share(update):
    register_user(update.from_user)
    files = get_all_files()
    if not files:
        bot.send_message(update.chat.id, "📭 Aucun fichier disponible")
        return

    if len(files) > 100:
        file_list = "\n".join([f"🔸 {f['file_name']} - /start {f['id']}" for f in files])
        bot.send_message(update.chat.id, f"📂 Fichiers disponibles :\n\n{file_list}")
    else:
        keyboard = [
            [types.InlineKeyboardButton(f["file_name"], callback_data=f"send_{f['id']}")]
            for f in files
        ]
        bot.send_message(
            update.chat.id,
            "📂 Sélectionnez un fichier :",
            reply_markup=types.InlineKeyboardMarkup(keyboard),
        )

# Commande accessible à tous pour envoyer un message à un utilisateur
@bot.message_handler(commands=["sendtext"])
def send_text_command(message):
    register_user(message.from_user)
    users = get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 Aucun utilisateur trouvé")
        return

    keyboard = [
        [types.InlineKeyboardButton(
            (u["username"] if u["username"] else str(u["user_id"])),
            callback_data=f"sendtext_user_{u['user_id']}"
        )] for u in users
    ]
    markup = types.InlineKeyboardMarkup(keyboard)
    bot.send_message(message.chat.id, "📋 Sélectionnez un utilisateur pour envoyer un message :", reply_markup=markup)

# Nouvelle commande pour lister tous les utilisateurs enregistrés
@bot.message_handler(commands=["listusers"])
def list_users_command(message):
    register_user(message.from_user)
    users = get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 Aucun utilisateur trouvé")
        return

    user_list = "\n".join([f"🔸 {u['username'] if u['username'] else u['user_id']}" for u in users])
    bot.send_message(message.chat.id, f"👥 Utilisateurs enregistrés :\n{user_list}\n\nPour envoyer un message, utilisez la commande /sendtext.")

@bot.message_handler(content_types=["document", "audio", "photo", "video", "animation", "voice", "video_note", "sticker"])
def handle_file(update):
    register_user(update.from_user)
    file = None
    file_type = None

    if update.document:
        file = update.document
        file_type = "document"
    elif update.video:
        file = update.video
        file_type = "video"
    elif update.audio:
        file = update.audio
        file_type = "audio"
    elif update.photo:
        file = update.photo[-1]
        file_type = "photo"
    elif update.animation:
        file = update.animation
        file_type = "animation"
    elif update.voice:
        file = update.voice
        file_type = "voice"
    elif update.video_note:
        file = update.video_note
        file_type = "video_note"
    elif update.sticker:
        file = update.sticker
        file_type = "sticker"

    if file:
        bot.send_message(update.chat.id, "✨ Donnez un nom à ce fichier :")
        # Rappel de l'ID du fichier pour l'enregistrement ultérieur
        bot.register_next_step_handler(update, set_filename, file, file_type)

def set_filename(update, file, file_type):
    file_name = update.text.strip()
    unique_id = str(uuid.uuid4())
    add_file(unique_id, file.file_id, file_type, file_name, update.from_user.id)
    share_link = f"https://t.me/{bot.get_me().username}?start={unique_id}"
    bot.send_message(update.chat.id, f"✅ Fichier enregistré !\n🔗 Lien de partage :\n{share_link}")

@bot.message_handler(commands=["delete"])
def delete(update):
    register_user(update.from_user)
    # La commande /delete reste réservée aux administrateurs
    if update.from_user.id not in ADMIN_IDS:
        bot.send_message(update.chat.id, "🚫 Accès refusé")
        return

    files = get_all_files()
    if not files:
        bot.send_message(update.chat.id, "📭 Aucun fichier à supprimer")
        return

    if len(files) > 100:
        file_list = "\n".join([f"🔸 {f['file_name']} (ID: {f['id']})" for f in files])
        bot.send_message(update.chat.id, f"🗑 Fichiers disponibles :\n\n{file_list}")
    else:
        keyboard = [
            [types.InlineKeyboardButton(f["file_name"], callback_data=f"del_{f['id']}")]
            for f in files
        ]
        bot.send_message(
            update.chat.id,
            "🗑 Sélectionnez un fichier à supprimer :",
            reply_markup=types.InlineKeyboardMarkup(keyboard),
        )

@bot.callback_query_handler(func=lambda call: True)
def button_handler(call):
    data = call.data
    user_id = call.from_user.id

    if data.startswith("send_"):
        file_id = data.split("_")[1]
        if file_data := get_file(file_id):
            caption = f"📤 {file_data['file_name']}"
            if file_data["file_type"] == "photo":
                bot.send_photo(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "document":
                bot.send_document(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "video":
                bot.send_video(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "audio":
                bot.send_audio(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "animation":
                bot.send_animation(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "voice":
                bot.send_voice(call.message.chat.id, file_data["file_id"], caption=caption)
            elif file_data["file_type"] == "video_note":
                bot.send_video_note(call.message.chat.id, file_data["file_id"])
            elif file_data["file_type"] == "sticker":
                bot.send_sticker(call.message.chat.id, file_data["file_id"])
        else:
            bot.send_message(call.message.chat.id, "❌ Fichier introuvable")

    elif data.startswith("del_"):
        if user_id not in ADMIN_IDS:
            bot.send_message(call.message.chat.id, "🚫 Accès refusé")
            return

        file_id = data.split("_")[1]
        if delete_file(file_id):
            bot.send_message(call.message.chat.id, "✅ Fichier supprimé")
        else:
            bot.send_message(call.message.chat.id, "❌ Échec de la suppression")

    elif data.startswith("sendtext_user_"):
        target_user_id = int(data.split("_")[-1])
        target_user = get_user(target_user_id)
        if target_user:
            display = target_user["username"] if target_user["username"] else str(target_user["user_id"])
        else:
            display = str(target_user_id)
        bot.send_message(call.message.chat.id, f"✍️ Envoyez le texte à transmettre à {display} :")
        bot.register_next_step_handler(call.message, process_send_text, target_user_id)

def process_send_text(message, target_user_id):
    text_to_send = message.text
    try:
        bot.send_message(target_user_id, f"✉️ Message reçu : {text_to_send}")
        bot.send_message(message.chat.id, "✅ Message envoyé avec succès.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur lors de l'envoi : {e}")

# Application
def main():
    init_db()
    bot.polling()

if __name__ == "__main__":
    main()
