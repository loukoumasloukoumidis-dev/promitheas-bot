import os
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Ρύθμιση logging για να βλέπουμε τα μηνύματα στα logs του Render
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ανάκτηση των Tokens από τις Environment Variables του Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Αρχικοποίηση του OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Δημιουργία εφαρμογής Flask (απαραίτητη για να μένει ανοιχτό το bot στο Render)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Απάντηση στην εντολή /start"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Γεια σου {user_name}! Είμαι το bot σου με OpenAI. Πώς μπορώ να σε βοηθήσω;")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Διαχείριση μηνυμάτων κειμένου και αποστολή στο ChatGPT"""
    user_text = update.message.text
    logger.info(f"Λήφθηκε μήνυμα: {user_text}")

    try:
        # Κλήση στο OpenAI API (χρησιμοποιούμε το gpt-4o-mini ή gpt-3.5-turbo για ταχύτητα και σταθερότητα)
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

def main() -> None:
    """Εκκίνηση του Telegram Bot"""
    if not TELEGRAM_TOKEN:
        logger.error("Δεν βρέθηκε TELEGRAM_TOKEN στις μεταβλητές περιβάλλοντος!")
        return

    # Δημιουργία του Application του Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Ορισμός handlers για εντολές και μηνύματα
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Εκκίνηση του bot (Polling)
    logger.info("Εκκίνηση εφαρμογής Telegram...")
    application.run_polling()

if __name__ == "__main__":
    import threading
    
    # Ξεκινάμε το Flask σε ξεχωριστό thread για να περνάει τα health checks του Render
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Τρέχουμε το bot
    main()
