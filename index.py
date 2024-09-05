import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

API_TOKEN = '7254708854:AAEop3TvQaazXTo8ZWx7djq8jBy1PMo4w-Q'
CHANNEL_ID = '-1002181122538'
BOT_NICKNAME='Practice_app_bot'
TOTAL_SUPPLY = 100_000_000_000  # 100 миллиардов токенов

bot = telebot.TeleBot(API_TOKEN)

# Создаем или подключаемся к базе данных SQLite
conn = sqlite3.connect('tokens.db', check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицы, если они еще не созданы
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    tokens INTEGER DEFAULT 0,
    referred_by INTEGER,
    referral_count INTEGER DEFAULT 0,
    received_initial_tokens BOOLEAN DEFAULT 0
)''')
conn.commit()

def create_markup(include_menu=False, include_balance=False):
    """Создаем клавиатуру с кнопками. Кнопка Menu добавляется только если include_menu=True, Balance — если include_balance=True."""
    markup = InlineKeyboardMarkup()
    subscribe_button = InlineKeyboardButton("Subscribe", url="https://t.me/nuriknik")
    
    if not include_menu:  # Включаем кнопку Check только до нажатия Menu
        check_button = InlineKeyboardButton("Check", callback_data="check")
        markup.add(subscribe_button, check_button)
    else:
        markup.add(subscribe_button)
    
    if include_balance:
        balance_button = InlineKeyboardButton("Balance", callback_data="balance")
        markup.add(balance_button)
    
    if include_menu:
        menu_button = InlineKeyboardButton("Menu", callback_data="menu")
        reference_button = InlineKeyboardButton("Reference", callback_data="reference")
        all_tokens_button = InlineKeyboardButton("All Tokens", callback_data="all_tokens")
        markup.add(menu_button, reference_button, all_tokens_button)
    
    return markup

# Функция для расчета оставшихся токенов
def get_remaining_tokens():
    cursor.execute("SELECT SUM(tokens) FROM users")
    used_tokens = cursor.fetchone()[0] or 0
    remaining_tokens = TOTAL_SUPPLY - used_tokens
    return remaining_tokens

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Проверяем, есть ли пользователь в базе данных, если нет - добавляем
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referrer_id = message.text.split()[-1] if len(message.text.split()) > 1 else None
        cursor.execute("INSERT INTO users (user_id, username, tokens, referred_by, received_initial_tokens) VALUES (?, ?, 0, ?, 0)", 
                       (user_id, username, referrer_id))
        conn.commit()

        # Обновляем количество рефералов у реферера и добавляем токены
        if referrer_id:
            cursor.execute("SELECT referral_count, tokens FROM users WHERE user_id = ?", (referrer_id,))
            referrer = cursor.fetchone()
            if referrer:
                if referrer[0] < 5:  # Даем токены только до 5 рефералов
                    new_referral_count = referrer[0] + 1
                    new_tokens = referrer[1] + 50  # Добавляем 50 токенов за реферала
                    cursor.execute("UPDATE users SET referral_count = ?, tokens = ? WHERE user_id = ?", 
                                   (new_referral_count, new_tokens, referrer_id))
                    conn.commit()

    markup = create_markup()  # Только Subscribe и Check
    bot.send_message(message.chat.id, "Hi! Please subscribe to our channel and click /check to check, then, receive tokens.", reply_markup=markup)

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == "check":
        markup = create_markup(include_menu=True)  # После проверки добавляем Menu и убираем Check
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            # Проверяем, получал ли пользователь уже 5000 токенов за подписку
            cursor.execute("SELECT received_initial_tokens FROM users WHERE user_id = ?", (user_id,))
            received_initial_tokens = cursor.fetchone()[0]
    
            username = call.from_user.username  # Получаем юзернейм
    
            if not received_initial_tokens:
                cursor.execute("UPDATE users SET tokens = tokens + 5000, received_initial_tokens = 1 WHERE user_id = ?", (user_id,))
                conn.commit()

                # Добавляем кнопку Open Web App с параметром юзернейм
                web_app_markup = InlineKeyboardMarkup()
                web_app_button = InlineKeyboardButton(f"Open Web App", url=f"https://nur521.github.io/fhfyuer/?username={username}")
                web_app_markup.add(web_app_button)

                bot.send_message(call.message.chat.id, "Отлично! Вы подписаны. Откройте веб-приложение по кнопке ниже:", reply_markup=web_app_markup)

                # После кнопки Web App выводим сообщение о токенах
                bot.send_message(call.message.chat.id, "Вы заработали 5000 MineCoins.\n\nИспользуйте меню ниже:", reply_markup=markup)
            else:
                web_app_markup = InlineKeyboardMarkup()
                web_app_button = InlineKeyboardButton(f"Open Web App", url=f"https://nur521.github.io/nur/?username={username}")
                web_app_markup.add(web_app_button)
                bot.send_message(call.message.chat.id, "Отлично! Вы подписаны. Откройте веб-приложение по кнопке ниже:", reply_markup=web_app_markup)
                bot.send_message(call.message.chat.id, "Вы уже получили свои 5000 токенов.\n\nИспользуйте меню ниже:", reply_markup=markup)

        else:
            bot.send_message(call.message.chat.id, "You are not subscribed to the channel. Please subscribe and try again.\n\nUse the menu below:", reply_markup=markup)
    
    elif call.data == "balance":
        cursor.execute("SELECT tokens FROM users WHERE user_id = ?", (user_id,))
        tokens = cursor.fetchone()[0]
        markup = create_markup(include_menu=True, include_balance=True)
        bot.send_message(call.message.chat.id, f"You have {tokens} MineCoins.\n\nUse the menu below:", reply_markup=markup)
    
    elif call.data == "menu":
        markup = create_markup(include_menu=True, include_balance=True)
        username = call.from_user.username
        bot.send_message(call.message.chat.id, f"Hi {username}. Welcome to MineCoin!\n\nUse the menu below:", reply_markup=markup)

    elif call.data == "reference":
        cursor.execute("SELECT referral_count, tokens FROM users WHERE user_id = ?", (user_id,))
        referral_count, tokens = cursor.fetchone()
        markup = create_markup(include_menu=True, include_balance=True)
        bot.send_message(call.message.chat.id, f"Your referral link: https://t.me/{BOT_NICKNAME}?start={user_id}\n"
                                               f"Referrals: {referral_count}\n"
                                               f"Tokens earned: {tokens} MineCoins.\n\nUse the menu below:", reply_markup=markup)

    elif call.data == "all_tokens":
        remaining_tokens = get_remaining_tokens()
        bot.send_message(call.message.chat.id, f"Total tokens remaining: {remaining_tokens} MineCoins.\n\nUse the menu below:")

bot.infinity_polling()
