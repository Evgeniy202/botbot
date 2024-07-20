import config
import telebot
from telebot import types
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = config.TOKEN
PATH_JSON_CON = config.PATH_JSON_CON

bot = telebot.TeleBot(TOKEN)

# Налаштування доступу до Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(PATH_JSON_CON, scope)
client = gspread.authorize(creds)
sheet = client.open("HRBot").sheet1

user_data = {}


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_data[message.chat.id] = {
        "id_tg": message.from_user.id,
        "username": message.from_user.username,
        "messages_to_delete": [message.message_id],
    }
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "Додаткова інформація або записатись на співбесіду", callback_data="info"
        )
    )
    markup.add(types.InlineKeyboardButton("Завершити діалог", callback_data="end"))
    bot.send_message(
        message.chat.id,
        "Вітаємо! Вам пропонується вакансія рекрутера.",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message.chat.id not in user_data:
        user_data[call.message.chat.id] = {
            "id_tg": call.from_user.id,
            "username": call.from_user.username,
            "messages_to_delete": [],
        }
    user_data[call.message.chat.id]["messages_to_delete"].append(
        call.message.message_id
    )
    try:
        if call.data == "info":
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "Зв'яжіться в Telegram", callback_data="telegram"
                )
            )
            markup.add(
                types.InlineKeyboardButton("Зателефонуйте", callback_data="call")
            )
            markup.add(
                types.InlineKeyboardButton("Завершити діалог", callback_data="end")
            )
            msg = bot.send_message(
                call.message.chat.id, "Оберіть спосіб зв'язку:", reply_markup=markup
            )
            user_data[call.message.chat.id]["messages_to_delete"].append(msg.message_id)
        elif call.data == "call":
            user_data[call.message.chat.id]["method_of_communication"] = call.data
            msg = bot.send_message(call.message.chat.id, "Напишіть ваш номер телефону:")
            user_data[call.message.chat.id]["messages_to_delete"].append(msg.message_id)
            bot.register_next_step_handler(msg, get_phone)
        elif call.data == "telegram":
            user_data[call.message.chat.id]["method_of_communication"] = call.data
            msg = bot.send_message(call.message.chat.id, "Напишіть ваше ім'я:")
            user_data[call.message.chat.id]["messages_to_delete"].append(msg.message_id)
            bot.register_next_step_handler(msg, get_name)
        elif call.data == "end":
            end_conversation(call.message.chat.id)
        elif call.data == "confirm":
            bot.send_message(
                call.message.chat.id,
                "Вітаємо! З вами зв'яжуться завтра з 10:00 до 13:00 (за Київським часом).",
            )
            save_user_data(call.message.chat.id)
            clear_chat(call.message.chat.id)
        elif call.data == "cancel":
            bot.send_message(
                call.message.chat.id, "Ваш запит скасовано. Дякуємо за ваш час!"
            )
            clear_chat(call.message.chat.id, cancelled=True)
        elif call.data == "start":
            send_welcome(call.message)
    except Exception as e:
        bot.send_message(call.message.chat.id, "Виникла помилка. Спробуйте пізніше.")
        bot.send_message(
            call.message.chat.id,
            "Розпочати новий діалог?",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("Розпочати", callback_data="start")
            ),
        )
        clear_chat(call.message.chat.id)


def get_phone(message):
    user_data[message.chat.id]["number"] = message.text
    msg = bot.send_message(message.chat.id, "Напишіть ваше ім'я:")
    user_data[message.chat.id]["messages_to_delete"].append(msg.message_id)
    bot.register_next_step_handler(msg, get_name)


def get_name(message):
    user_data[message.chat.id]["name"] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Зв'яжуться зі мною", callback_data="confirm")
    )
    markup.add(types.InlineKeyboardButton("Відмінити", callback_data="cancel"))
    msg = bot.send_message(
        message.chat.id,
        "Ваші дані збережено. Оберіть подальшу дію:",
        reply_markup=markup,
    )
    user_data[message.chat.id]["messages_to_delete"].append(msg.message_id)


def save_user_data(chat_id):
    data = user_data[chat_id]
    next_row = len(sheet.get_all_values()) + 1
    sheet.update_cell(next_row, 1, next_row - 1)
    sheet.update_cell(next_row, 2, data["id_tg"])
    sheet.update_cell(next_row, 3, data["username"])
    sheet.update_cell(next_row, 4, data.get("number", ""))
    sheet.update_cell(next_row, 5, data["name"])
    sheet.update_cell(next_row, 6, data["method_of_communication"])
    sheet.update_cell(next_row, 7, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def clear_chat(chat_id, cancelled=False):
    for msg_id in user_data[chat_id]["messages_to_delete"]:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception as e:
            print(f"Could not delete message {msg_id}: {e}")
    if cancelled:
        bot.send_message(
            chat_id,
            "Розпочати новий діалог?",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("Розпочати", callback_data="start")
            ),
        )
    user_data.pop(chat_id, None)


def end_conversation(chat_id):
    bot.send_message(
        chat_id,
        "Дякуємо! Якщо у вас виникнуть питання, звертайтесь до нас.",
    )
    clear_chat(chat_id, cancelled=True)


bot.polling()
