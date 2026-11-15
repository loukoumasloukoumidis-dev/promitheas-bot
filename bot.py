import os
import threading
from flask import Flask

# 1. Δημιουργία ενός απλού Flask server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Το Render δίνει αυτόματα την πόρτα μέσω της μεταβλητής περιβάλλοντος PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. Ξεκινάμε τον Flask server σε ξεχωριστό thread για να μη μπλοκάρει το bot
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Από κάτω συνεχίζει κανονικά ο κώδικας του Telegram Bot σου...

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

# Ενεργοποίηση καταγραφής σφαλμάτων (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Ανάγνωση του κλειδιού από τις μεταβλητές περιβάλλοντος (Environment Variables)
API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not API_KEY:
    raise ValueError("Δεν βρέθηκε το GEMINI_API_KEY στις μεταβλητές περιβάλλοντος!")

if not TELEGRAM_TOKEN:
    raise ValueError("Δεν βρέθηκε το TELEGRAM_TOKEN στις μεταβλητές περιβάλλοντος!")

# Αρχικοποίηση του νέου Google GenAI Client
client = genai.Client(api_key=API_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    try:
        # Χρήση του προτεινόμενου μοντέλου gemini-3.8-flash για γρήγορες απαντήσεις
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_message,
        )
        
        reply_text = response.text
        await context.bot.send_message(chat_id=chat_id, text=reply_text)
        
    except Exception as e:
        logging.error(f"Σφάλμα κατά την επικοινωνία με το Gemini: {e}")
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Προέκυψαν τεχνικά προβλήματα κατά την επεξεργασία του αιτήματος."
        )

def main():
    # Δημιουργία του Telegram Bot Application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Προσθήκη handler για τα μηνύματα κειμένου
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Εκκίνηση του Bot
    print("Το bot ξεκίνησε επιτυχώς και ακούει...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
