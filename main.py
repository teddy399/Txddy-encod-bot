import os
import subprocess
import requests
import telebot
from telebot import types

# Ton Token Telegram intégré
BOT_TOKEN = "8628583419:AAGJJ54c8UjYd57ZqWLoNHj63krWJMyGuJM"
bot = telebot.TeleBot(BOT_TOKEN)

user_urls = {}

def download_drive_file(url, destination):
    file_id = url.split('/d/')[1].split('/')[0]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    session = requests.Session()
    response = session.get(download_url, stream=True)
    
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            download_url += f"&confirm={value}"
            response = session.get(download_url, stream=True)
            break
            
    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Salut ! Balance-moi un lien Google Drive ou vidéo.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if "http://" in url or "https://" in url:
        user_urls[message.chat.id] = url
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🎬 Vidéo (1080p 8Mbps)", callback_data="video"),
            types.InlineKeyboardButton("🎵 Audio seul (MP3 320k)", callback_data="audio")
        )
        bot.reply_to(message, "Que veux-tu faire avec ce lien ?", reply_markup=markup)
    else:
        bot.reply_to(message, "Envoie un lien URL valide stp.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    url = user_urls.get(chat_id)
    
    if not url:
        bot.answer_callback_query(call.id, "Lien expiré.")
        return

    input_file = f"input_{chat_id}"
    output_file = f"output_{chat_id}.mp4"
    audio_file = f"audio_{chat_id}.mp3"

    if call.data == "video":
        bot.edit_message_text("📥 Téléchargement depuis Drive et re-encodage (1080p 8Mbps)...", chat_id, call.message.message_id)
        try:
            if "drive.google.com" in url:
                download_drive_file(url, input_file)
            else:
                subprocess.run(f'yt-dlp -o "{input_file}" "{url}"', shell=True, check=True)

            cmd = f'ffmpeg -i {input_file} -vf scale=1920:1080 -b:v 8M -c:a aac -b:a 192k {output_file} -y'
            subprocess.run(cmd, shell=True, check=True)

            with open(output_file, 'rb') as video:
                bot.send_video(chat_id, video)

        except Exception as e:
            bot.send_message(chat_id, f"❌ Erreur : {str(e)}")
        finally:
            for f in [input_file, output_file]:
                if os.path.exists(f): os.remove(f)

    elif call.data == "audio":
        bot.edit_message_text("🎵 Extraction audio en cours...", chat_id, call.message.message_id)
        try:
            if "drive.google.com" in url:
                download_drive_file(url, input_file)
            else:
                subprocess.run(f'yt-dlp -o "{input_file}" "{url}"', shell=True, check=True)

            cmd = f'ffmpeg -i {input_file} -vn -ab 320k {audio_file} -y'
            subprocess.run(cmd, shell=True, check=True)

            with open(audio_file, 'rb') as audio:
                bot.send_audio(chat_id, audio)

        except Exception as e:
            bot.send_message(chat_id, f"❌ Erreur : {str(e)}")
        finally:
            for f in [input_file, audio_file]:
                if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    print("🤖 Txddy_encod prêt !")
    bot.infinity_polling()
