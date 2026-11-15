import os
import logging
import tempfile
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Ρύθμιση logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ανάκτηση Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Αρχικοποίηση Groq client
client = Groq(api_key=GROQ_API_KEY)

# Δημιουργία εφαρμογής Flask για το Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Γεια σου {user_name}! Είμαι το bot σου με τη Groq (100% δωρεάν). "
        "Υποστηρίζω κείμενο, ηχητικά μηνύματα και γενικές γνώσεις!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    if not user_text:
        return
    logger.info(f"Λήφθηκε μήνυμα κειμένου: {user_text}")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Είσαι ένας χρήσιμος, ευγενικός βοηθός."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=1000
        )
        reply_text = response.choices[0].message.content
        if reply_text:
            await update.message.reply_text(reply_text)
        else:
            await update.message.reply_text("Δεν μπόρεσα να παράγω απάντηση.")

    except Exception as e:
        logger.error(f"Σφάλμα κατά την επικοινωνία με τη Groq: {e}")
        await update.message.reply_text("Προέκυψαν τεχνικά προβλήματα κατά την επεξεργασία του αιτήματος.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Λήφθηκε ηχητικό μήνυμα...")
    voice = update.message.voice
    
    file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        await file.download_to_drive(temp_audio.name)
        temp_audio_path = temp_audio.name

    try:
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )
        
        user_text = transcript.text if transcript else ""
        logger.info(f"Απομαγνητοφώνηση: {user_text}")

        if not user_text.strip():
            await update.message.reply_text("Δεν μπόρεσα να ακούσω καθαρά το ηχητικό μήνυμα. Δοκίμασε ξανά!")
            return

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Είσαι ένας χρήσιμος, ευγενικός βοηθός."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=1000
        )
        
        reply_text = response.choices[0].message.content
        if reply_text:
            await update.message.reply_text(f"🎤 *Άκουσα:* {user_text}\n\n{reply_text}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"🎤 *Άκουσα:* {user_text}\n\n(Δεν υπήρξε απάντηση από το μοντέλο)")

    except Exception as e:
        logger.error(f"Σφάλμα κατά την απομαγνητοφώνηση/επεξεργασία ηχητικού: {e}")
        await update.message.reply_text("Προέκυψαν τεχνικά προβλήματα κατά την επεξεργασία του ηχητικού μηνύματος.")
    
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("Δεν βρέθηκε TELEGRAM_TOKEN στις μεταβλητές περιβάλλοντος!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Εκκίνηση εφαρμογής Telegram...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import threading
    
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    main()
    
