import os
import re
import math
import subprocess
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_tasks = {}

def get_video_info(file_path):
    cmd_dur = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res_dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = float(res_dur.stdout)

    cmd_name = ["ffprobe", "-v", "error", "-show_entries", "format=filename", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res_name = subprocess.run(cmd_name, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw_name = os.path.basename(res_name.stdout.decode().strip())
    base_name = os.path.splitext(raw_name)[0]
    
    if base_name.startswith("input_"):
        base_name = "Audio" if "mp3" in file_path else "Video"

    return duration, base_name

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = (
        "Salut ! Moi c'est **Txddy_encod** 🎬\n\n"
        "Balance-moi un lien Google Drive public.\n"
        "Tu pourras choisir d'exporter la vidéo (1080p / 30fps / 8 Mbps) ou **uniquement l'audio en MP3** !"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_choice(call):
    user_id = call.from_user.id
    if user_id not in user_tasks:
        bot.answer_callback_query(call.id, "Session expirée. Renvoyez le lien.")
        return

    file_id = user_tasks[user_id]
    mode = call.data
    
    bot.edit_message_text("Téléchargement du fichier depuis Drive... ⏳", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    input_file = f"input_{user_id}.mp4"
    try:
        os.system(f'gdown --id {file_id} -O "{input_file}"')

        if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
            bot.edit_message_text("🔒 Erreur : Fichier inaccessible. Assure-toi que le lien est bien public.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return

        duration, original_name = get_video_info(input_file)

        if mode == 'mode_audio':
            bot.edit_message_text("Extraction de la piste audio en MP3... 🎵", chat_id=call.message.chat.id, message_id=call.message.message_id)
            out_audio = f"{original_name}_TE.mp3"
            
            cmd = f'ffmpeg -y -i "{input_file}" -vn -c:a libmp3lame -b:a 320k "{out_audio}"'
            os.system(cmd)

            if os.path.exists(out_audio):
                with open(out_audio, 'rb') as audio_doc:
                    bot.send_document(call.message.chat.id, audio_doc, caption=f"🎵 Piste audio extraite : `{out_audio}`", parse_mode="Markdown")
                os.remove(out_audio)
            bot.delete_message(call.message.chat.id, call.message.message_id)

        elif mode == 'mode_video':
            max_part_duration = 60
            total_parts = math.ceil(duration / max_part_duration)

            for i in range(total_parts):
                start_time = i * max_part_duration
                segment_duration = min(max_part_duration, duration - start_time)
                out_filename = f"{original_name}_TE_part{i+1}.mp4" if total_parts > 1 else f"{original_name}_TE.mp4"

                bot.edit_message_text(f"⚙️ Encodage Vidéo (Partie {i+1}/{total_parts})...", chat_id=call.message.chat.id, message_id=call.message.message_id)

                ffmpeg_cmd = (
                    f'ffmpeg -y -ss {start_time} -i "{input_file}" -t {max_part_duration} '
                    f'-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30" '
                    f'-b:v 8M -maxrate 8M -bufsize 16M -c:v libx264 -preset fast -movflags +faststart '
                    f'-c:a aac -b:a 192k "{out_filename}"'
                )
                os.system(ffmpeg_cmd)

                if os.path.exists(out_filename):
                    caption = f"✨ Vidéo encodée : `{out_filename}`\n🎬 1080p | 30 fps | 8 Mbps (Partie {i+1}/{total_parts})"
                    with open(out_filename, 'rb') as doc:
                        bot.send_document(call.message.chat.id, doc, caption=caption, parse_mode="Markdown")
                    os.remove(out_filename)

            bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        print(f"Erreur : {e}")
        bot.send_message(call.message.chat.id, "Oups, une erreur s'est produite. 😬")
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if user_id in user_tasks:
            del user_tasks[user_id]

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text.strip()
    file_id_match = re.search(r'(/d/|id=)([\w-]+)', text)

    if file_id_match:
        user_id = message.from_user.id
        user_tasks[user_id] = file_id_match.group(2)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🎬 Vidéo (1080p 8Mbps)", callback_data="mode_video"),
            InlineKeyboardButton("🎵 Audio seul (MP3 320k)", callback_data="mode_audio")
        )
        bot.reply_to(message, "Que veux-tu faire avec ce fichier ?", reply_markup=markup)
    else:
        bot.reply_to(message, "Salut ! Balance-moi un lien Google Drive dès que tu veux extraire ou encoder. 👌")

if __name__ == "__main__":
    print("🤖 Txddy_encod prêt sur Koyeb 24/24 !")
    bot.infinity_polling()
