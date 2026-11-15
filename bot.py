import os
import logging
import tempfile
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Ρύθμιση logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ανάκτηση Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Αρχικοποίηση OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Δημιουργία εφαρμογής Flask για το Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Απάντηση στην εντολή /start"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Γεια σου {user_name}! Είμαι το bot σου με OpenAI και υποστηρίζω και ηχητικά μηνύματα. Πώς μπορώ να σε βοηθήσω;")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Διαχείριση μηνυμάτων κειμένου"""
    user_text = update.message.text
    logger.info(f"Λήφθηκε μήνυμα κειμένου: {user_text}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Είσαι ένας χρήσιμος και ευγενικός βοηθός."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=1000
        )
        reply_text = response.choices[0].message.content
        await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Σφάλμα κατά την επικοινωνία με το OpenAI: {e}")
        await update.message.reply_text("Προέκυψαν τεχνικά προβλήματα κατά την επεξεργασία του αιτήματος.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Διαχείριση ηχητικών μηνυμάτων (Voice notes)"""
    logger.info("Λήφθηκε ηχητικό μήνυμα...")
    voice = update.message.voice
    
    # Κατέβασμα του αρχείου ήχου προσωρινά
    file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        await file.download_to_drive(temp_audio.name)
        temp_audio_path = temp_audio.name

    try:
        # Απομαγνητοφώνηση με το OpenAI Whisper API
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        user_text = transcript.text
        logger.info(f"Απομαγνητοφώνηση: {user_text}")

        # Αποστολή του κειμένου στο ChatGPT για απάντηση
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Είσαι ένας χρήσιμος και ευγενικός βοηθός."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=1000
        )
        
        reply_text = response.choices[0].message.content
        # Στέλνουμε τι κατάλαβε και την απάντηση
        await update.message.reply_text(f"🎤 *Άκουσα:* {user_text}\n\n{reply_text}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Σφάλμα κατά την απομαγνητοφώνηση/επεξεργασία ηχητικού: {e}")
        await update.message.reply_text("Προέκυψαν τεχνικά προβλήματα κατά την επεξεργασία του ηχητικού μηνύματος.")
    
    finally:
        # Καθαρισμός του προσωρινού αρχείου
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

def main() -> None:
    """Εκκίνηση του Telegram Bot"""
    if not TELEGRAM_TOKEN:
        logger.error("Δεν βρέθηκε TELEGRAM_TOKEN στις μεταβλητές περιβάλλοντος!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers για κείμενο, εντολές και ηχητικά
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Εκκίνηση εφαρμογής Telegram...")
    application.run_polling()

if __name__ == "__main__":
    import threading
    
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    main()
    
