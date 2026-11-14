import os
import datetime
import sqlite3
import requests
import telebot
from google import genai
from google.genai import types

# 1. Βάλε εδώ τα κλειδιά σου
TELEGRAM_BOT_TOKEN = "9026273282:AAFkBnN0kIeuD4oHzDlecQF8psH8hNyiSeY"
GEMINI_API_KEY = "AQ.Ab8RN6JFhlLRnnQ7CT4CiNuVEAOQG1uccprPqkzk5vXp3_XT9w"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Συντεταγμένες καταστήματος για τον καιρό (π.χ. Κέντρο Θεσσαλονίκης)
STORE_LAT = 40.6401
STORE_LON = 22.9444

# 2. Αρχικοποίηση Τοπικής Βάσης Δεδομένων SQLite (Αντικαθιστά τα Google Sheets χωρίς κάρτες)
def init_db():
    conn = sqlite3.connect('promitheas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            store TEXT,
            courier TEXT,
            area TEXT,
            fee REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SYSTEM_INSTRUCTIONS = """
Είσαι ο Προμηθέας, ο προσωπικός συντονιστής και βοηθός διανομής για κατάστημα εστίασης. 
Μιλάς ευγενικά, επαγγελματικά και υποστηρικτικά προς τον διανομέα.
- Αν σου αναφέρουν παραγγελία, ανάλυσέ την και δώσε καθαρά τα προϊόντα, τις ποσότητες, τη διεύθυνση και την εκτιμώμενη αμοιβή.
- Αν η παραγγελία είναι ασαφής, απάντησε ακριβώς: "Δεν κατάλαβα την παραγγελία σου. Στείλε ξανά τα προϊόντα και τις ποσότητες (κείμενο ή φωνητικό)."
"""

# Πρόγνωση καιρού για τις επόμενες 8 ώρες
def get_weather_forecast():
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={STORE_LAT}&longitude={STORE_LON}&hourly=temperature_2m,precipitation_probability&forecast_days=1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        current_hour = datetime.datetime.now().hour
        next_hours_temps = data['hourly']['temperature_2m'][current_hour:current_hour+8]
        next_hours_rain = data['hourly']['precipitation_probability'][current_hour:current_hour+8]
        
        avg_temp = sum(next_hours_temps) / len(next_hours_temps)
        max_rain = max(next_hours_rain)
        
        weather_desc = f"Μέση θερμοκρασία γύρω στους {avg_temp:.1f}°C."
        if max_rain > 50:
            weather_desc += " Προσοχή: Υπάρχει πιθανότητα βροχής στις επόμενες ώρες, πάρτε αδιάβροχο!"
        else:
            weather_desc += " Ο καιρός φαίνεται καλός για τη βάρδια."
            
        return weather_desc
    except Exception:
        return "Ο καιρός προβλέπεται καλός για τη βάρδια."

# Χαιρετισμός ανάλογα με την ώρα
def get_time_based_greeting(is_ending=False):
    now = datetime.datetime.now()
    hour = now.hour
    
    if is_ending:
        if 5 <= hour < 18:
            return "Καλή συνέχεια στη μέρα σου, καλή ξεκούραση!"
        else:
            return "Καληνύχτα, καλή ξεκούραση!"
    else:
        if 5 <= hour < 12:
            return "Καλημέρα, είμαι ο Προμηθέας, ο προσωπικός σας συντονιστής."
        elif 12 <= hour < 18:
            return "Καλησπέρα, είμαι ο Προμηθέας, ο προσωπικός σας συντονιστής."
        else:
            return "Καλησπέρα (νυχτερινή βάρδια), είμαι ο Προμηθέας, ο προσωπικός σας συντονιστής."

# Εντολή Έναρξης Βάρδιας
@bot.message_handler(commands=['start', 'shift_start'])
def start_shift(message):
    greeting = get_time_based_greeting(is_ending=False)
    weather_info = get_weather_forecast()
    
    welcome_text = (
        f"{greeting}\n\n"
        f"🌤️ **Πρόγνωση καιρού (επόμενες 8 ώρες):** {weather_info}\n\n"
        "Η βάρδια σου ξεκίνησε επίσημα. Στείλε μου την πρώτη παραγγελία σε κείμενο ή φωνητικό!"
    )
    bot.reply_to(message, welcome_text)

# Εντολή Λήξης Βάρδιας
@bot.message_handler(commands=['shift_end'])
def end_shift(message):
    farewell = get_time_based_greeting(is_ending=True)
    text = f"Η βάρδια ολοκληρώθηκε. {farewell}"
    bot.reply_to(message, text)

# Εντολή Στατιστικών / Αναφοράς
@bot.message_handler(commands=['stats'])
def show_stats(message):
    try:
        conn = sqlite3.connect('promitheas.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(fee) FROM deliveries")
        result = cursor.fetchone()
        conn.close()
        
        count = result[0] if result[0] else 0
        total_fee = result[1] if result[1] else 0.0
        
        text = f"📊 **Στατιστικά Διανομών:**\n\n• Συνολικές Διανομές: {count}\n• Συνολικό Ποσό Αμοιβών: {total_fee:.2f}€"
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"Σφάλμα ανάκτησης στατιστικών: {str(e)}")

# Χειρισμός κειμένου & παραγγελιών
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_text = message.text
    if user_text.startswith('/'):
        return
        
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=f"Μήνυμα: {user_text}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                temperature=0.2
            )
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Σφάλμα: {str(e)}")

# Χειρισμός φωνητικών μηνυμάτων
@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    try:
        bot.reply_to(message, "🎙️ Ο Προμηθέας επεξεργάζεται το φωνητικό...")
        
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        audio_filename = "voice_order.ogg"
        with open(audio_filename, 'wb') as f:
            f.write(downloaded_file)
            
        audio_file_ref = client.files.upload(file=audio_filename)
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',

            contents=[audio_file_ref, "Άκουσε το φωνητικό μήνυμα και δώσε την ανάλυση της παραγγελίας."],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                temperature=0.2
            )
        )
        
        if os.path.exists(audio_filename):
            os.remove(audio_filename)
            
        bot.reply_to(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"Σφάλμα φωνητικού: {str(e)}")

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Promitheas Bot is alive!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

if __name__ == '__main__':
    # Ξεκινάμε τον web server στο παρασκήνιο για να ικανοποιήσουμε το Render
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("Ο Προμηθέας ξεκίνησε και λειτουργεί!")
    bot.infinity_polling()
    
  
