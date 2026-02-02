import telebot
import sqlite3
import random
import time
from telebot import types

TOKEN = "7481122191:AAEjyGVL0_AMFxDxIlZNpZDUrrbPbId9qJw"
bot = telebot.TeleBot(TOKEN)

# БОЛЬШАЯ БАЗА ДАННЫХ (Учебник, Класс, Модуль, Англ, Рус)
WORDS_DATA = [
    ("Spotlight", "5 класс", "Module 1", "School", "Школа"), ("Spotlight", "5 класс", "Module 1", "Teacher", "Учитель"),
    ("Spotlight", "5 класс", "Module 2", "Family", "Семья"), ("Spotlight", "5 класс", "Module 2", "Home", "Дом"),
    ("Spotlight", "6 класс", "Module 1", "Street", "Улица"), ("Spotlight", "6 класс", "Module 1", "City", "Город"),
    ("Spotlight", "7 класс", "Module 1", "Hobby", "Хобби"), ("Spotlight", "7 класс", "Module 1", "Sport", "Спорт"),
    ("Spotlight", "8 класс", "Module 1", "Character", "Характер"), ("Spotlight", "8 класс", "Module 1", "Social", "Общество"),
    ("Spotlight", "9 класс", "Module 1", "History", "История"), ("Spotlight", "9 класс", "Module 1", "Culture", "Культура"),
    ("Starlight", "5 класс", "Module 1", "Planet", "Планета"), ("Starlight", "5 класс", "Module 1", "Star", "Звезда")
]


print('я вернул свой код')


def init_db():
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS user_progress (user_id INTEGER, word TEXT, module TEXT, class_name TEXT, book TEXT, next_time INTEGER, PRIMARY KEY (user_id, word, module))')
    conn.commit()
    conn.close()

def show_next_word(message, user_id, book, cls, mod):
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()
    all_mod_words = [w for w in WORDS_DATA if w[0] == book and w[1] == cls and w[2] == mod]
    now = int(time.time())
    cursor.execute("SELECT word FROM user_progress WHERE user_id = ? AND module = ? AND next_time > ?", (user_id, mod, now))
    learned = [r[0] for r in cursor.fetchall()]
    remaining = [w for w in all_mod_words if w[3] not in learned]

    markup = types.InlineKeyboardMarkup()
    if remaining:
        word_data = random.choice(remaining)
        eng, rus = word_data[3], word_data[4]
        markup.add(types.InlineKeyboardButton("Легко ✅", callback_data=f"save_3600_{eng}_{mod}_{cls}_{book}"),
                   types.InlineKeyboardButton("Нормально 👍", callback_data=f"save_600_{eng}_{mod}_{cls}_{book}"),
                   types.InlineKeyboardButton("Сложно ⏳", callback_data=f"save_60_{eng}_{mod}_{cls}_{book}"))
        markup.add(types.InlineKeyboardButton("🏠 На главную", callback_data="main_menu"))
        bot.edit_message_text(f"📘 {book} | {cls} | {mod}\nСлово: **{eng}**\nПеревод: <tg-spoiler>{rus}</tg-spoiler>", message.chat.id, message.message_id, reply_markup=markup, parse_mode="HTML")
    else:
        markup.add(types.InlineKeyboardButton("📂 Выбрать другой модуль", callback_data=f"setclass_{book}_{cls}"))
        markup.add(types.InlineKeyboardButton("🏠 На главную", callback_data="main_menu"))
        bot.edit_message_text("🌟 Модуль пройден! Все слова на повторении.", message.chat.id, message.message_id, reply_markup=markup)
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    books = sorted(list(set([w[0] for w in WORDS_DATA])))
    for b in books: markup.add(types.InlineKeyboardButton(text=b, callback_data=f"setbook_{b}"))
    bot.send_message(message.chat.id, "📚 Выбери учебник:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id, data = call.from_user.id, call.data.split("_")
    action = data[0]

    if action == "main_menu":
        markup = types.InlineKeyboardMarkup()
        for b in sorted(list(set([w[0] for w in WORDS_DATA]))): markup.add(types.InlineKeyboardButton(text=b, callback_data=f"setbook_{b}"))
        bot.edit_message_text("📚 Выбери учебник:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "setbook":
        book, markup = data[1], types.InlineKeyboardMarkup()
        for c in sorted(list(set([w[1] for w in WORDS_DATA if w[0] == book]))): markup.add(types.InlineKeyboardButton(text=c, callback_data=f"setclass_{book}_{c}"))
        markup.add(types.InlineKeyboardButton("🏠 На главную", callback_data="main_menu"))
        bot.edit_message_text(f"Учебник: {book}\nВыбери класс:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "setclass":
        book, cls, markup = data[1], data[2], types.InlineKeyboardMarkup()
        for m in sorted(list(set([w[2] for w in WORDS_DATA if w[0] == book and w[1] == cls]))): markup.add(types.InlineKeyboardButton(text=m, callback_data=f"setmod_{book}_{cls}_{m}"))
        markup.add(types.InlineKeyboardButton("🏠 На главную", callback_data="main_menu"))
        bot.edit_message_text(f"Класс: {cls}\nВыбери модуль:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "setmod":
        show_next_word(call.message, user_id, data[1], data[2], data[3])

    elif action == "save":
        sec, eng, mod, cls, book = data[1], data[2], data[3], data[4], data[5]
        conn = sqlite3.connect('base.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO user_progress VALUES (?,?,?,?,?,?)', (user_id, eng, mod, cls, book, int(time.time()) + int(sec)))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "Запомнил!")
        show_next_word(call.message, user_id, book, cls, mod)

if __name__ == '__main__':
    init_db()
    bot.polling(non_stop=True)
