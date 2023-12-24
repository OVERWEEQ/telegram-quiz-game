import telebot
from telebot import types
from Edit import TOKEN, ADMINS, ID_REPORT_CHAT
import sqlite3
import random
import string
from datetime import datetime
import time

bot = telebot.TeleBot(TOKEN)
global user_id, finded_user_id


# Создаем соединение с базой данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Создаем таблицу для хранения пользовательских данных
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        referral_code TEXT,
        referred_by TEXT,
        referred_count INTEGER,
        balance REAL,
        last_visit_date TEXT,
        answered_questions TEXT
    )
''')

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

# Создадим словарь для хранения времени последнего сообщения от каждого пользователя
last_message_time = {}

# Функция-декоратор для антиспама
def antispam(func):
    def wrapper(message):
        global last_message_time
        user_id = message.from_user.id
        current_time = time.time()
        if user_id in last_message_time:
            # Если прошло менее 1 секунды с момента последнего сообщения, игнорируем новое сообщение
            if current_time - last_message_time[user_id] < 1:
                return
        func(message)
        last_message_time[user_id] = current_time
    return wrapper

# Функция для генерации реферального кода
def generate_referral_code():
    # Генерируем случайный 8-значный код из букв и цифр
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_random_question(message):
    with open("Questions.txt", "r", encoding="utf-8") as file:
        questions = file.read().split("#")
    questions = [q.strip() for q in questions if q.strip()]

    # Проверим, если все вопросы уже были отвечены
    if len(questions) == 0:
        return None, None, None, None

    random_question = random.choice(questions)
    question_parts = random_question.strip().split("\n")
    question_number = question_parts[0].strip()
    question_text = question_parts[1].strip()
    correct_answer = question_parts[2].strip()
    wrong_answers = [answer.strip() for answer in question_parts[3:] if answer.strip()]
    all_answers = [correct_answer] + wrong_answers
    random.shuffle(all_answers)
    return question_number, question_text, all_answers, correct_answer

def get_current_date():
    return datetime.now().strftime('%d.%m.%Y')  # Формат DD.MM.YYYY

def is_admin(user_id):
    return user_id in ADMINS

# Обработчик команды /start
@bot.message_handler(commands=['start'])
@antispam
def start_handler(message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_date = get_current_date()  # Шаг 2: Получение текущей даты
    if user_data is None:
        id_report_chat = ID_REPORT_CHAT
        bot.send_message(id_report_chat, f"Новый пользователь @{message.chat.username}, id: {message.chat.id}")
        bot.register_next_step_handler(message, report_send_handler);
        referral_code = generate_referral_code()
        referred_by = None
        referred_count = 0
        balance = 0.0
        answered_questions = ""
        cursor.execute(
            'INSERT INTO users (id, referral_code, referred_by, referred_count, balance, last_visit_date, answered_questions) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, referral_code, referred_by, referred_count, balance, current_date, answered_questions))

    else:
        cursor.execute('UPDATE users SET last_visit_date = ? WHERE id = ?', (current_date, user_id))

    conn.commit()

    markup = types.ReplyKeyboardMarkup(row_width=3)
    itemPlay = types.KeyboardButton('🕹 Играть')
    itemProfile = types.KeyboardButton('👤 Мой профиль')
    itemReport = types.KeyboardButton('📬 Сообщить')
    itemTop = types.KeyboardButton('📊 Топ игроков')
    markup.add(itemPlay)
    markup.add(itemProfile, itemTop)
    if is_admin(message.from_user.id):
        itemAdmin = types.KeyboardButton('🔒 Меню админа')
        markup.add(itemAdmin, itemReport)
    else:
        markup.add(itemReport)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


def get_total_questions():
    with open("Questions.txt", "r", encoding="utf-8") as file:
        questions = file.read().split("#")
    return len(questions)


# Обработчик кнопки "🕹 Играть"
@bot.message_handler(func=lambda message: message.text == '🕹 Играть')
@antispam
def play_handler(message):
    global correct_answer, from_user
    from_user = message.from_user.id

    # Получаем общее количество вопросов
    total_questions = get_total_questions()

    # Получаем список вопросов, на которые уже ответил пользователь
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT answered_questions FROM users WHERE id = ?', (message.from_user.id,))
    result = cursor.fetchone()
    if result is None:
        answered_questions = []
    else:
        answered_questions = result[0].split(',') if result[0] else []

    # Если пользователь ответил на все вопросы, сообщаем ему об этом и завершаем игру
    if len(answered_questions) == total_questions:
        bot.send_message(message.chat.id, "Вы ответили на все вопросы! Совсем скоро появятся новые!")
        # Можно добавить сюда код для сброса списка answered_questions или выполнения других действий

    else:
        # Получаем случайный вопрос
        question_number, question_text, all_answers, correct_answer = get_random_question(message)

        # Проверяем, если все вопросы уже отвечены, то завершаем игру
        if question_number is None:
            bot.send_message(message.chat.id, "Вы ответили на все вопросы! Совсем скоро появятся новые!")
            # Можно добавить сюда код для сброса списка answered_questions или выполнения других действий

        else:
            # Проверяем, не был ли уже ответен этот вопрос
            while str(question_number) in answered_questions:
                # Если вопрос уже был отвечен, получаем новый случайный вопрос
                question_number, question_text, all_answers, correct_answer = get_random_question(message)

            random_items = random.sample(all_answers, k=len(all_answers))
            item1 = types.KeyboardButton(random_items[0])
            item2 = types.KeyboardButton(random_items[1])
            item3 = types.KeyboardButton(random_items[2])
            item4 = types.KeyboardButton(random_items[3])
            itemBack = types.KeyboardButton('↪️ Назад')
            markup = types.ReplyKeyboardMarkup(row_width=2)
            markup.add(item1, item2)
            markup.add(item3, item4)
            markup.add(itemBack)

            bot.send_message(message.chat.id, question_text, reply_markup=markup)

            # Обновляем информацию о текущем вопросе для пользователя в базе данных
            if str(question_number) not in answered_questions:
                answered_questions.append(str(question_number))
                answered_questions_str = ','.join(answered_questions)
                cursor.execute('UPDATE users SET answered_questions = ? WHERE id = ?', (answered_questions_str, message.from_user.id))
                conn.commit()
        bot.register_next_step_handler(message, check_answer)
    conn.close()


# Обработчик ответов пользователя
def check_answer(message):
    global correct_answer, from_user
    result = message.text
    if result == correct_answer:
        # Создаем клавиатуру с кнопками "Играть еще" и "Назад"
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(types.KeyboardButton('🕹 Играть еще'))
        markup.add(types.KeyboardButton('↪️ Назад'))

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + 2 WHERE id = ?', (from_user,))
        conn.commit()
        conn.close()


        # Отправляем ответ пользователю
        bot.send_message(message.chat.id, "✅ Правильно! ✅\n" +
                                          "Вы получили 2 очка \n" +
                                          " \n" +
                                          "Хотите поиграть еще?\n", reply_markup=markup)
        bot.register_next_step_handler(message, after_check_answer);
    elif result == "↪️ Назад":
        start_handler(message)
    else:
        # Создаем клавиатуру с кнопками "Играть еще" и "Назад"
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(types.KeyboardButton('🕹 Играть еще'))
        markup.add(types.KeyboardButton('↪️ Назад'))

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance - 1 WHERE id = ?', (from_user,))
        conn.commit()
        conn.close()

        # Отправляем ответ пользователю
        bot.send_message(message.chat.id, f"❗️Неправильно❗️\n" +
                   f"Правильный ответ: {correct_answer}\n" +
                   f"Вы потеряли 1 очко \n" +
                   " \n" +
                   f"Хотите поиграть еще?\n", reply_markup=markup)
        bot.register_next_step_handler(message, after_check_answer);

def after_check_answer(message):
    global correct_answer
    do = message.text
    if do == "🕹 Играть еще":
        play_handler(message)
    elif do == '↪️ Назад':
        start_handler(message)
    else:
        pass

# Обработчик кнопки "🔒 Меню админа"
@bot.message_handler(func=lambda message: message.text == '🔒 Меню админа')
@antispam
def admin_menu_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemStat = types.KeyboardButton('📆 Статистика')
        itemSend = types.KeyboardButton('📨 Рассылка')
        itemFindUser = types.KeyboardButton('🕵🏻‍♂️ Пробить человечка')
        itemChangeData = types.KeyboardButton('✍🏻 Изменить данные человечка')
        itemBack = types.KeyboardButton('↪️ Назад')
        markup.add(itemStat, itemSend)
        markup.add(itemFindUser, itemChangeData)
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Меню админа", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа.")

# Обработчик кнопки "📨 Рассылка"
@bot.message_handler(func=lambda message: message.text == '📨 Рассылка')
@antispam
def sender_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itemBack = types.KeyboardButton('↪️ Назад')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Введите сообщение для рассылки. Оно улетит ВСЕМ.", reply_markup=markup)
        bot.register_next_step_handler(message, sender_send_handler);
    else:
        bot.send_message(message.chat.id, "У вас нет доступа.")


def sender_send_handler(message):
    rassylka_message = message.text
    # Получаем список всех пользователей бота из базы данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()

    # Отправляем сообщение рассылки каждому пользователю
    for user_id in users:
        try:
            bot.send_message(user_id[0], rassylka_message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id[0]}: {str(e)}")

# Функция для получения числа пользователей, зашедших сегодня
def get_users_today():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    current_date = get_current_date()
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_visit_date = ?', (current_date,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Обработчик команды "Статистика"
@bot.message_handler(func=lambda message: message.text == '📆 Статистика')
@antispam
def statistics_handler(message):
    if message.from_user.id in ADMINS:
        users_today = get_users_today()
        bot.send_message(message.chat.id, f"Количество пользователей, зашедших сегодня: {users_today}")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа.")


# Обработчик кнопки "🕵🏻‍♂️ Пробить человечка"
@bot.message_handler(func=lambda message: message.text == '🕵🏻‍♂️ Пробить человечка')
@antispam
def find_user_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemBack = types.KeyboardButton('↪️ Назад')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Дай его ID и я тебе скажу кто он", reply_markup=markup)
        bot.register_next_step_handler(message, finded_user_info_handler);
    else:
        bot.send_message(message.chat.id, "У вас нет доступа.")


def finded_user_info_handler(message):
    finded_user_id = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)

    # Проверяем, существует ли пользователь с таким кодом
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (finded_user_id,))
    user_data = cursor.fetchone()
    if user_data is None:
        if finded_user_id == '↪️ Назад':
            pass
        else:
            if not hasattr(message, 'error_message_sent'):
                # Отправляем сообщение об ошибке
                bot.send_message(message.chat.id, "Такого ID не существует.")
                message.error_message_sent = True  # Устанавливаем флаг
                bot.register_next_step_handler(message, finded_user_info_handler)
    else:
        user_id = user_data[0]
        referral_code = user_data[1]
        referred_by = user_data[2]
        referred_count = user_data[3]
        balance = user_data[4]
        bot.send_message(message.chat.id, f"ID: {user_id}\n" +
                         f"referral code: {referral_code}\n" +
                         f"referred by: {referred_by}\n" +
                         f"referred count: {referred_count}\n" +
                         f"balance: {balance}\n", reply_markup=markup)
    if message.text == '↪️ Назад':
        admin_menu_handler(message)
    else:
        if not hasattr(message, 'error_message_sent'):
            message.error_message_sent = True  # Устанавливаем флаг
            bot.register_next_step_handler(message, finded_user_info_handler)

####################################################################


# Обработчик кнопки "✍🏻 Изменить данные человечка"
@bot.message_handler(func=lambda message: message.text == '✍🏻 Изменить данные человечка')
@antispam
def find_user_for_change_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemBack = types.KeyboardButton('↪️ Назад')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Нужен его ID", reply_markup=markup)
        bot.register_next_step_handler(message, finded_user_for_change_handler);
    else:
        bot.send_message(message.chat.id, "У вас нет доступа.")


def finded_user_for_change_handler(message):
    global finded_user_id
    finded_user_id = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)

    # Проверяем, существует ли пользователь с таким кодом
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (finded_user_id,))
    user_data = cursor.fetchone()
    if user_data is None:
        if finded_user_id == '↪️ Назад':
            pass
        else:
            if not hasattr(message, 'error_message_sent'):
                # Отправляем сообщение об ошибке
                bot.send_message(message.chat.id, "Такого ID не существует.")
                message.error_message_sent = True  # Устанавливаем флаг
                bot.register_next_step_handler(message, finded_user_for_change_handler)
    else:
        if message.text != '↪️ Назад':
            if not hasattr(message, 'error_message_sent'):
                message.error_message_sent = True  # Устанавливаем флаг
                change_what_data_handler(message)
    if message.text == '↪️ Назад':
        admin_menu_handler(message)
    else:
        if not hasattr(message, 'error_message_sent'):
            message.error_message_sent = True  # Устанавливаем флаг
            change_what_data_handler(message)

def change_what_data_handler(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemChanBal = types.KeyboardButton('Изменить баланс')
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemChanBal)
    markup.add(itemBack)
    bot.send_message(message.chat.id, "Что изменить?", reply_markup=markup)
    bot.register_next_step_handler(message, change_what_data_transport_handler);

def change_what_data_transport_handler(message):
    transport = message.text;
    if transport == "Изменить баланс":
        change_balance_handler(message)
    elif transport == "↪️ Назад":
        admin_menu_handler(message)
    else:
        pass


def change_balance_handler(message):
    global finded_user_id
    finded_user_id = finded_user_id
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (finded_user_id,))
    user_data = cursor.fetchone()
    balance = user_data[4]
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)
    bot.send_message(message.chat.id, f"Сейчас у него на балансе: {balance}, сколько сделать?", reply_markup=markup)
    bot.register_next_step_handler(message, change_balance_to_handler);


def change_balance_to_handler(message):
    global finded_user_id
    new_balance = message.text;
    if new_balance == "↪️ Назад":
        admin_menu_handler(message)
    else:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(f'UPDATE users SET balance = {new_balance} WHERE id = ?', (finded_user_id,))
        conn.commit()
        conn.close()

        # Отправляем сообщение об успешном вводе реферального кода
        bot.send_message(message.chat.id, "Баланс успешно изменён!")


#####################################################################

# Обработчик кнопки "👤 Мой профиль"
@bot.message_handler(func=lambda message: message.text == '👤 Мой профиль')
@antispam
def profile_handler(message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    referral_code = user_data[1]
    referred_by = user_data[2]
    referred_count = user_data[3]
    balance = user_data[4]

    markup = types.ReplyKeyboardMarkup(row_width=2)


    if referred_by is not None:
        pass
    else:
        itemRefCode = types.KeyboardButton('✍🏻 Ввести реферальный код')
        markup.add(itemRefCode)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)

    bot.send_message(message.chat.id, "💼 Ваш профиль 💼\n" +
                              " \n" +
                              f"🆔 Ваш ID: {message.from_user.id}\n" +
                              f"🔖 Ваш реферальный код: {referral_code}\n" +
                              f"👉 Отправьте ваш реферальный код друзьям и получите 10 бесплатных игр за каждого, кто применит ваш код\n" +
                              f"👥 Кол-во ваших рефералов: {referred_count}\n" +
                              f"💵 Ваши рейтинговые очки: {balance}", reply_markup=markup)

def get_top_players():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, balance FROM users ORDER BY balance DESC LIMIT 10')
    top_players = cursor.fetchall()
    conn.close()
    return top_players

# Обработчик кнопки "📊 Топ игроков"
@bot.message_handler(func=lambda message: message.text == '📊 Топ игроков')
@antispam
def top_handler(message):
    top_players = get_top_players()
    current_user_id = message.from_user.id

    # Проверяем, находится ли текущий пользователь в Топ-10
    current_user_position = None
    for idx, (user_id, _) in enumerate(top_players, 1):
        if user_id == current_user_id:
            current_user_position = idx
            break

    top_message = ("📌 Топ-10 игроков по рейтинговым очкам:\n"
                  "\n")
    for idx, (user_id, balance) in enumerate(top_players, 1):
        if user_id == current_user_id:
            top_message += f"{idx} место - {balance} баллов (Вы)\n"
        else:
            top_message += f"{idx} место - {balance} баллов\n"

    if current_user_position:
        pass
    else:
        # Если текущий пользователь не в Топ-10, добавляем его место и баланс
        cursor.execute('SELECT balance FROM users WHERE id = ?', (current_user_id,))
        result = cursor.fetchone()
        if result:
            user_balance = result[0]
            top_message += f"\n{current_user_position} место - {balance} баллов (Вы)"

    bot.send_message(message.chat.id, top_message)

# Обработчик кнопки "✍🏻 Ввести реферальный код"
@bot.message_handler(func=lambda message: message.text == '✍🏻 Ввести реферальный код')
@antispam
def enter_referral_code_handler(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)
    bot.send_message(message.chat.id, "Пожалуйста, введите код вашего друга, чтобы бесплатно получить 10 рейтинговых очков:", reply_markup=markup)
    bot.register_next_step_handler(message, referral_code_handler);

# Проверка введённого реферального кода"
def referral_code_handler(message):
    referral_code = message.text;
    # Проверяем, существует ли пользователь с таким кодом
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE referral_code = ?', (referral_code,))
    referred_user_data = cursor.fetchone()
    if referred_user_data is None:
        # Отправляем сообщение об ошибке
        bot.send_message(message.chat.id, "Извините, но такого кода не существует. Пожалуйста, попробуйте еще раз.")
    else:
        # Обновляем данные пользователя, который ввел реферальный код
        user_id = message.from_user.id
        referred_by = referred_user_data[0]
        cursor.execute('UPDATE users SET referred_by = ? WHERE id = ?', (referred_by, user_id))
        cursor.execute('UPDATE users SET referred_count = referred_count + 1 WHERE id = ?', (user_id,))
        cursor.execute('UPDATE users SET balance = balance + 10 WHERE id = ?', (user_id,))
        cursor.execute('UPDATE users SET balance = balance + 10 WHERE id = ?', (referred_by,))
        conn.commit()
        conn.close()

        # Отправляем сообщение об успешном вводе реферального кода
        bot.send_message(message.chat.id, "Реферальный код успешно испльзован! Вы получили 10 рейтинговых очков!")


# Обработчик кнопки "📬 Сообщить"
@bot.message_handler(func=lambda message: message.text == '📬 Сообщить')
@antispam
def report_handler(message):
    # Ваше действие по нажатию кнопки "📬 Сообщить"
    markup = types.ReplyKeyboardMarkup(row_width=1)
    itemBack = types.KeyboardButton('↪️ Назад')
    markup.add(itemBack)
    bot.send_message(message.chat.id, "Если вы нашли баг или ошибку, то вы можете поделиться этим здесь.\n" +
                                      "Всё, что вы напишите сюда доёдет до администраторов.", reply_markup=markup)
    bot.register_next_step_handler(message, report_send_handler);
# Проверка введённого реферального кода"
def report_send_handler(message):
    id_report_chat = -1001914206356
    if message.text == '↪️ Назад':
        start_handler(message)
    else:
        bot.send_message(id_report_chat, f"Репорт от @{message.chat.username}, id: {message.chat.id}: {message.text}")
        bot.register_next_step_handler(message, report_send_handler);

@bot.message_handler(func=lambda message: message.text == '↪️ Назад')
@antispam
def back_handler(message):
    start_handler(message)
bot.polling(none_stop=True)
