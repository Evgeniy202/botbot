import config
import telebot
from telebot import types
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials


TOKEN = config.TOKEN
PATH_JSON_CON = config.PATH_JSON_CON

bot = telebot.TeleBot(TOKEN)


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
    if call.data == "info":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "Зв'яжіться в Telegram", callback_data="telegram"
            )
        )
        markup.add(types.InlineKeyboardButton("Зателефонуйте", callback_data="call"))
        markup.add(types.InlineKeyboardButton("Завершити діалог", callback_data="end"))
        bot.send_message(
            call.message.chat.id, "Оберіть спосіб зв'язку:", reply_markup=markup
        )
    elif call.data == "call":
        user_data[call.message.chat.id]["method_of_communication"] = call.data
        msg = bot.send_message(call.message.chat.id, "Напишіть ваш номер телефону:")
        bot.register_next_step_handler(msg, get_phone)
    elif call.data == "telegram":
        user_data[call.message.chat.id]["method_of_communication"] = call.data
        msg = bot.send_message(call.message.chat.id, "Напишіть ваше ім'я:")
        bot.register_next_step_handler(msg, get_name)
    elif call.data == "end":
        bot.send_message(
            call.message.chat.id,
            "Дякуємо! Якщо у вас виникнуть питання, звертайтесь до нас.",
        )
        clear_chat(call.message.chat.id)
    elif call.data == "confirm":
        bot.send_message(
            call.message.chat.id,
            "Вітаємо! З вами зв'яжуться завтра з 10:00 до 13:00 (за Київським часом).",
        )
        save_user_data(call.message.chat.id)
    elif call.data == "cancel":
        bot.send_message(
            call.message.chat.id, "Ваш запит скасовано. Дякуємо за ваш час!"
        )
        clear_chat(call.message.chat.id)


def get_phone(message):
    user_data[message.chat.id]["number"] = message.text
    msg = bot.send_message(message.chat.id, "Напишіть ваше ім'я:")
    bot.register_next_step_handler(msg, get_name)


def get_name(message):
    user_data[message.chat.id]["name"] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Зв'яжуться зі мною", callback_data="confirm")
    )
    markup.add(types.InlineKeyboardButton("Відмінити", callback_data="cancel"))
    bot.send_message(
        message.chat.id,
        "Ваші дані збережено. Оберіть подальшу дію:",
        reply_markup=markup,
    )


def save_user_data(chat_id):
    data = user_data[chat_id]
    sheet.append_row(
        [
            data["id_tg"],
            data["username"],
            data.get("number", ""),
            data["name"],
            data["method_of_communication"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]
    )


def clear_chat(chat_id):
    user_data.pop(chat_id, None)
    bot.send_message(
        chat_id,
        "Розпочати новий діалог?",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Розпочати")
        ),
    )


bot.polling()
