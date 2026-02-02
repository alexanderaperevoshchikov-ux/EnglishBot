import telebot
import sqlite3
from telebot import types
import random

TOKEN = "7481122191:AAEjyGVL0_AMFxDxIlZNpZDUrrbPbId9qJw"
bot = telebot.TeleBot(TOKEN)

# Расширенный список карточек на 2026 год
DEFAULT_CARDS = [
    ("Game", "Игра"), ("Apple", "Яблоко"), ("Code", "Код"),
    ("Connection", "Соединение"), ("Account", "Аккаунт"),
    ("Update", "Обновление"), ("Security", "Безопасность"),
    ("Available", "Доступный"), ("Opportunity", "Возможность"),
    ("Challenge", "Вызов"), ("Experience", "Опыт"),
    ("Improve", "Улучшать"), ("Confirm", "Подтверждать"),
    ("Current", "Текущий"), ("Develop", "Разрабатывать")
]

print('я украл твой код')

def init_db():
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            english_word TEXT NOT NULL,
            russian_word TEXT NOT NULL,
            UNIQUE(english_word, russian_word)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards (
            user_id INTEGER,
            card_id INTEGER,
            score INTEGER DEFAULT 1000,
            shows_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, card_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (card_id) REFERENCES cards (card_id)
        )
    ''')
    for eng, rus in DEFAULT_CARDS:
        cursor.execute('INSERT OR IGNORE INTO cards (english_word, russian_word) VALUES (?, ?)', (eng, rus))
    conn.commit()
    conn.close()


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))

    cursor.execute('SELECT count(*) FROM user_cards WHERE user_id = ?', (user_id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT card_id FROM cards')
        all_card_ids = cursor.fetchall()
        for (c_id,) in all_card_ids:
            # ИСПРАВЛЕНО: Явно указываем столбцы для вставки
            cursor.execute('''
                INSERT OR IGNORE INTO user_cards (user_id, card_id, score, shows_count) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, c_id, 1000, 0))
        conn.commit()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="🗂 Обучение", callback_data="view_cards"))
    bot.send_message(message.chat.id, " Нажми кнопку ниже Чтобы начать/продолжить обучение.", reply_markup=markup)
    conn.close()


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()

    # "Подогрев" карточек: +50 к score за каждое действие пользователя
    cursor.execute('UPDATE user_cards SET score = score + 50 WHERE user_id = ? AND score < 1000', (user_id,))

    if call.data == "view_cards":
        cursor.execute('''
            SELECT c.english_word, c.russian_word, uc.card_id, uc.shows_count 
            FROM cards c
            JOIN user_cards uc ON c.card_id = uc.card_id
            WHERE uc.user_id = ? AND uc.score >= 1000
        ''', (user_id,))

        ready_cards = cursor.fetchall()

        if ready_cards:
            card = random.choice(ready_cards)
            eng, rus, c_id, shows = card

            markup = types.InlineKeyboardMarkup()
            # Передаем ID и текущие показы в callback
            markup.add(
                types.InlineKeyboardButton("Легко", callback_data=f"ans_easy_{c_id}_{shows}"),
                types.InlineKeyboardButton("Нормально", callback_data=f"ans_norm_{c_id}_{shows}"),
                types.InlineKeyboardButton("Сложно", callback_data=f"ans_hard_{c_id}_{shows}")
            )
            bot.edit_message_text(f"Как легко вспомнил(а)/знал(а) превод слова: **{eng}**?", call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "Все карточки на отдыхе. Нажми кнопку ещё раз через пару секунд!",
                                      show_alert=True)

    elif call.data.startswith("ans_"):
        _, type_ans, card_id, shows = call.data.split("_")
        shows = int(shows)
        card_id = int(card_id)

        # Достаем перевод для показа пользователю
        cursor.execute('SELECT english_word, russian_word FROM cards WHERE card_id = ?', (card_id,))
        card_data = cursor.fetchone()
        eng_w, rus_w = card_data if card_data else ("???", "???")

        # ТВОЯ ФОРМУЛА (Исправлено: сложно = меньший штраф = чаще показ)
        if type_ans == "easy":
            penalty = 300 + (shows * 10)
            status = "Легко! ✅"
        elif type_ans == "norm":
            penalty = 200 + (shows * 10)
            status = "Нормально 👍"
        else:
            penalty = 100 + (shows * 10)
            status = "Сложно ⏳"

        new_score = 1000 - penalty

        cursor.execute('''
            UPDATE user_cards 
            SET score = ?, shows_count = shows_count + 1 
            WHERE user_id = ? AND card_id = ?
        ''', (new_score, user_id, card_id))
        conn.commit()

        # Формируем ответ с переводом
        res_text = (
            f"**{status}**\n\n"
            f"Слово: `{eng_w}`\n"
            f"Перевод: **{rus_w}**\n\n"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Далее ➡️", callback_data="view_cards"))

        bot.edit_message_text(res_text, call.message.chat.id, call.message.message_id,
                              reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    conn.close()


if __name__ == '__main__':
    init_db()
    print("Бот запущен...")
    bot.polling(non_stop=True)
