import telebot
from telebot import types
from Edit import TOKEN, ADMINS
import sqlite3
import random
import string
from datetime import datetime
import time

bot = telebot.TeleBot(TOKEN)
global user_id, finded_user_id


# Creating a connection to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Creating a table to store user data
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

# Saving changes and close connection
conn.commit()
conn.close()

# Creating a dictionary to store the time of the last message from each user
last_message_time = {}

# Antispam-function
def antispam(func):
    def wrapper(message):
        global last_message_time
        user_id = message.from_user.id
        current_time = time.time()
        if user_id in last_message_time:
            # If less than 1 second has passed since the last message, ignore the new message
            if current_time - last_message_time[user_id] < 1:
                return
        func(message)
        last_message_time[user_id] = current_time
    return wrapper

# Function for generate new 8-digit refferal code from letters and numbers
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Selecting a random question
def get_random_question(message):
    with open("Questions.txt", "r", encoding="utf-8") as file:
        questions = file.read().split("#")
    questions = [q.strip() for q in questions if q.strip()]

    # Checking if all questions have already been answered
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
    return datetime.now().strftime('%d.%m.%Y')

def is_admin(user_id):
    return user_id in ADMINS

# /start command handler
@bot.message_handler(commands=['start'])
@antispam
def start_handler(message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_date = get_current_date()
    if user_data is None:
        id_report_chat = -1001914206356
        bot.send_message(id_report_chat, f"New user @{message.chat.username}, id: {message.chat.id}")
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
    itemPlay = types.KeyboardButton('🕹 Play')
    itemProfile = types.KeyboardButton('👤 My profile')
    itemLanguage = types.KeyboardButton('🇬🇧 Language')
    itemReport = types.KeyboardButton('📬 Report')
    itemTop = types.KeyboardButton('📊 Top players')
    markup.add(itemPlay)
    markup.add(itemProfile, itemTop)
    if is_admin(message.from_user.id):
        itemAdmin = types.KeyboardButton('🔒 Admin menu')
        markup.add(itemAdmin, itemReport)
    else:
        markup.add(itemReport)
    bot.send_message(message.chat.id, "Choose an action:", reply_markup=markup)


def get_total_questions():
    with open("Questions.txt", "r", encoding="utf-8") as file:
        questions = file.read().split("#")
    return len(questions)


# "🕹 Play" button handler
@bot.message_handler(func=lambda message: message.text == '🕹 Play')
@antispam
def play_handler(message):
    global correct_answer, from_user
    from_user = message.from_user.id
    total_questions = get_total_questions()

    # Getting a list of questions that the user has already answered
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT answered_questions FROM users WHERE id = ?', (message.from_user.id,))
    result = cursor.fetchone()
    if result is None:
        answered_questions = []
    else:
        answered_questions = result[0].split(',') if result[0] else []

    # If the user has answered all the questions, we inform him about this and end the game
    if len(answered_questions) == total_questions:
        bot.send_message(message.chat.id, "You have answered all the questions! New ones will appear very soon!")
    else:
        # Getting a random question
        question_number, question_text, all_answers, correct_answer = get_random_question(message)

        if question_number is None:
            bot.send_message(message.chat.id, "You have answered all the questions! New ones will appear very soon!")

        else:
            # Checking to see if this question has already been answered
            while str(question_number) in answered_questions:
                # If the question has already been answered, we get a new random question
                question_number, question_text, all_answers, correct_answer = get_random_question(message)

            random_items = random.sample(all_answers, k=len(all_answers))
            item1 = types.KeyboardButton(random_items[0])
            item2 = types.KeyboardButton(random_items[1])
            item3 = types.KeyboardButton(random_items[2])
            item4 = types.KeyboardButton(random_items[3])
            itemBack = types.KeyboardButton('↪️ Back')
            markup = types.ReplyKeyboardMarkup(row_width=2)
            markup.add(item1, item2)
            markup.add(item3, item4)
            markup.add(itemBack)

            bot.send_message(message.chat.id, question_text, reply_markup=markup)

            # Updating information in the database
            if str(question_number) not in answered_questions:
                answered_questions.append(str(question_number))
                answered_questions_str = ','.join(answered_questions)
                cursor.execute('UPDATE users SET answered_questions = ? WHERE id = ?', (answered_questions_str, message.from_user.id))
                conn.commit()
        bot.register_next_step_handler(message, check_answer)
    conn.close()

# User answer handler
def check_answer(message):
    global correct_answer, from_user
    result = message.text
    if result == correct_answer:
        # Creating a keyboard with "Play more" and "Back" buttons
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(types.KeyboardButton('🕹 Play more'))
        markup.add(types.KeyboardButton('↪️ Back'))

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + 2 WHERE id = ?', (from_user,))
        conn.commit()
        conn.close()


        # Sending a response to the user
        bot.send_message(message.chat.id, "✅ Correct! ✅\n" +
                                          "You got 2 points \n" +
                                          " \n" +
                                          "Want to play more??\n", reply_markup=markup)
        bot.register_next_step_handler(message, after_check_answer);
    elif result == "↪️ Back":
        start_handler(message)
    else:
        # Creating a keyboard with "Play more" and "Back" buttons
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(types.KeyboardButton('🕹 Play more'))
        markup.add(types.KeyboardButton('↪️ Back'))

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance - 1 WHERE id = ?', (from_user,))
        conn.commit()
        conn.close()

        # Отправляем ответ пользователю
        bot.send_message(message.chat.id, f"❗️Wrong❗️\n" +
                   f"Currect answer: {correct_answer}\n" +
                   f"You lost 1 point \n" +
                   " \n" +
                   f"Want to play more??\n", reply_markup=markup)
        bot.register_next_step_handler(message, after_check_answer);

def after_check_answer(message):
    global correct_answer
    do = message.text
    if do == "🕹 Play more":
        play_handler(message)
    elif do == '↪️ Back':
        start_handler(message)
    else:
        pass

# "🔒 Admin menu" button handler
@bot.message_handler(func=lambda message: message.text == '🔒 Admin menu')
@antispam
def admin_menu_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemStat = types.KeyboardButton('📆 Statistic')
        itemSend = types.KeyboardButton('📨 Spam')
        itemFindUser = types.KeyboardButton('🕵🏻‍♂️ Person info')
        itemChangeData = types.KeyboardButton('✍🏻 Change person data')
        itemBack = types.KeyboardButton('↪️ Back')
        markup.add(itemStat, itemSend)
        markup.add(itemFindUser, itemChangeData)
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Admin menu", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "You don't have access.")

# "📨 Spam" button handler
@bot.message_handler(func=lambda message: message.text == '📨 Spam')
@antispam
def sender_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itemBack = types.KeyboardButton('↪️ Back')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Enter a message to send. It will fly away EVERYONE.", reply_markup=markup)
        bot.register_next_step_handler(message, sender_send_handler);
    else:
        bot.send_message(message.chat.id, "You don't have access.")


def sender_send_handler(message):
    rassylka_message = message.text
    # Getting a list of all bot users from the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()

    # Send a message to each user
    for user_id in users:
        try:
            bot.send_message(user_id[0], rassylka_message)
        except Exception as e:
            print(f"Error sending message to user {user_id[0]}: {str(e)}")

# Function to get the number of users logged in today
def get_users_today():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    current_date = get_current_date()
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_visit_date = ?', (current_date,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# "Statistic" button handler
@bot.message_handler(func=lambda message: message.text == '📆 Statistic')
@antispam
def statistics_handler(message):
    if message.from_user.id in ADMINS:
        users_today = get_users_today()
        bot.send_message(message.chat.id, f"Number of users logged in today: {users_today}")
    else:
        bot.send_message(message.chat.id, "You don't have access.")


# "🕵🏻‍♂️ Person info" button handler
@bot.message_handler(func=lambda message: message.text == '🕵🏻‍♂️ Person info')
@antispam
def find_user_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemBack = types.KeyboardButton('↪️ Back')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Print his ID and I'll tell you who he is", reply_markup=markup)
        bot.register_next_step_handler(message, finded_user_info_handler);
    else:
        bot.send_message(message.chat.id, "You don't have access.")


def finded_user_info_handler(message):
    finded_user_id = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)

    # Checking if a user with this code exists
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (finded_user_id,))
    user_data = cursor.fetchone()
    if user_data is None:
        if finded_user_id == '↪️ Back':
            pass
        else:
            if not hasattr(message, 'error_message_sent'):
                # Sending an error message
                bot.send_message(message.chat.id, "No such ID exists.")
                message.error_message_sent = True
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
    if message.text == '↪️ Back':
        admin_menu_handler(message)
    else:
        if not hasattr(message, 'error_message_sent'):
            message.error_message_sent = True
            bot.register_next_step_handler(message, finded_user_info_handler)

####################################################################


# "✍🏻 Change person data" button handler
@bot.message_handler(func=lambda message: message.text == '✍🏻 Change person data')
@antispam
def find_user_for_change_handler(message):
    if message.from_user.id in ADMINS:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        itemBack = types.KeyboardButton('↪️ Back')
        markup.add(itemBack)
        bot.send_message(message.chat.id, "Need his ID", reply_markup=markup)
        bot.register_next_step_handler(message, finded_user_for_change_handler);
    else:
        bot.send_message(message.chat.id, "You don't have access.")


def finded_user_for_change_handler(message):
    global finded_user_id
    finded_user_id = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)

    # Checking if a user with this code exists
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (finded_user_id,))
    user_data = cursor.fetchone()
    if user_data is None:
        if finded_user_id == '↪️ Back':
            pass
        else:
            if not hasattr(message, 'error_message_sent'):
                # Sending an error message
                bot.send_message(message.chat.id, "No such ID exists.")
                message.error_message_sent = True
                bot.register_next_step_handler(message, finded_user_for_change_handler)
    else:
        if message.text != '↪️ Back':
            if not hasattr(message, 'error_message_sent'):
                message.error_message_sent = True
                change_what_data_handler(message)
    if message.text == '↪️ Back':
        admin_menu_handler(message)
    else:
        if not hasattr(message, 'error_message_sent'):
            message.error_message_sent = True
            change_what_data_handler(message)

def change_what_data_handler(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itemChanBal = types.KeyboardButton('Change balance')
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemChanBal)
    markup.add(itemBack)
    bot.send_message(message.chat.id, "What to change?", reply_markup=markup)
    bot.register_next_step_handler(message, change_what_data_transport_handler);

def change_what_data_transport_handler(message):
    transport = message.text;
    if transport == "Change balance":
        change_balance_handler(message)
    elif transport == "↪️ Back":
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
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)
    bot.send_message(message.chat.id, f"Now he has on his balance: {balance}, how much to do?", reply_markup=markup)
    bot.register_next_step_handler(message, change_balance_to_handler);


def change_balance_to_handler(message):
    global finded_user_id
    new_balance = message.text;
    if new_balance == "↪️ Back":
        admin_menu_handler(message)
    else:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(f'UPDATE users SET balance = {new_balance} WHERE id = ?', (finded_user_id,))
        conn.commit()
        conn.close()

        # Sending a message about successful entry of the referral code
        bot.send_message(message.chat.id, "Balance successfully changed!")


#####################################################################

# "👤 My profile" button handler
@bot.message_handler(func=lambda message: message.text == '👤 My profile')
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
        itemRefCode = types.KeyboardButton('✍🏻 Enter referral code')
        markup.add(itemRefCode)
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)

    bot.send_message(message.chat.id, "💼 Your profile 💼\n" +
                              " \n" +
                              f"🆔 Your ID: {message.from_user.id}\n" +
                              f"🔖 Your referal code: {referral_code}\n" +
                              f"👉 Send your referral code to your friends and get 10 free games for everyone who uses your code\n" +
                              f"👥 Number of your referrals: {referred_count}\n" +
                              f"💵 Your rating points: {balance}", reply_markup=markup)

def get_top_players():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, balance FROM users ORDER BY balance DESC LIMIT 10')
    top_players = cursor.fetchall()
    conn.close()
    return top_players

# "📊 Top players" button handler
@bot.message_handler(func=lambda message: message.text == '📊 Top players')
@antispam
def top_handler(message):
    top_players = get_top_players()
    current_user_id = message.from_user.id

    # Checking if the current user is in the Top 10
    current_user_position = None
    for idx, (user_id, _) in enumerate(top_players, 1):
        if user_id == current_user_id:
            current_user_position = idx
            break

    top_message = ("📌 Top-10 players by rating points:\n"
                  "\n")
    for idx, (user_id, balance) in enumerate(top_players, 1):
        if user_id == current_user_id:
            top_message += f"{idx} place - {balance} points (You)\n"
        else:
            top_message += f"{idx} place - {balance} points\n"

    if current_user_position:
        pass
    else:
        # If the current user is not in the Top 10, add his place and balance
        cursor.execute('SELECT balance FROM users WHERE id = ?', (current_user_id,))
        result = cursor.fetchone()
        if result:
            user_balance = result[0]
            top_message += f"\n{current_user_position} place - {balance} points (You)"

    bot.send_message(message.chat.id, top_message)

# "✍🏻 Enter referral code" button handler
@bot.message_handler(func=lambda message: message.text == '✍🏻 Enter referral code')
@antispam
def enter_referral_code_handler(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)
    bot.send_message(message.chat.id, "Please enter your friend's code to get 10 free rating points:", reply_markup=markup)
    bot.register_next_step_handler(message, referral_code_handler);

# Checking the entered referral code"
def referral_code_handler(message):
    referral_code = message.text;
    # Checking if a user with this code exists
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE referral_code = ?', (referral_code,))
    referred_user_data = cursor.fetchone()
    if referred_user_data is None:
        # Sending an error message
        bot.send_message(message.chat.id, "Sorry, but such code does not exist. Please try again.")
    else:
        # We update the data of the user who entered the referral code
        user_id = message.from_user.id
        referred_by = referred_user_data[0]
        cursor.execute('UPDATE users SET referred_by = ? WHERE id = ?', (referred_by, user_id))
        cursor.execute('UPDATE users SET referred_count = referred_count + 1 WHERE id = ?', (user_id,))
        cursor.execute('UPDATE users SET balance = balance + 10 WHERE id = ?', (user_id,))
        cursor.execute('UPDATE users SET balance = balance + 10 WHERE id = ?', (referred_by,))
        conn.commit()
        conn.close()

        # Sending a message about successful entry of the referral code
        bot.send_message(message.chat.id, "Referral code successfully used! You have received 10 rating points!")


# "📬 Report" button handler
@bot.message_handler(func=lambda message: message.text == '📬 Report')
@antispam
def report_handler(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    itemBack = types.KeyboardButton('↪️ Back')
    markup.add(itemBack)
    bot.send_message(message.chat.id, "If you find a bug or error, you can share it here.\n" +
                                      "Everything you write here will reach the administrators.", reply_markup=markup)
    bot.register_next_step_handler(message, report_send_handler);

def report_send_handler(message):
    id_report_chat = -1001914206356
    if message.text == '↪️ Back':
        start_handler(message)
    else:
        bot.send_message(id_report_chat, f"Репорт от @{message.chat.username}, id: {message.chat.id}: {message.text}")
        bot.register_next_step_handler(message, report_send_handler);


@bot.message_handler(func=lambda message: message.text == '↪️ Back')
@antispam
def back_handler(message):
    start_handler(message)
bot.polling(none_stop=True)