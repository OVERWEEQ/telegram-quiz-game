import sqlite3

# Создаем соединение с базой данных
conn = sqlite3.connect('users.db')

# Создаем курсор для выполнения операций с базой данных
cursor = conn.cursor()

# Очищаем столбец answered_questions
cursor.execute('UPDATE users SET answered_questions = NULL')

# Сохраняем изменения
conn.commit()

# Закрываем соединение
conn.close()