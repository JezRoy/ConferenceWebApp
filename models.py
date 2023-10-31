import sqlite3

# Create a SQLite database file
conn = sqlite3.connect('ConferenceWebApp.db')
cursor = conn.cursor()

def initialise():
    """ Initialise the entire database. """
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delegates
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hosts
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conferences
                id Integer PRIMARY KEY,
                name Text NOT NULL,
                hostID INTEGER,
                paperSubDeadline DATE,
                delegateSignupDeadline DATE,
                confStart DATE,
                confEnd DATE
                       ''')
        return True
    except:
        return False

conn.close()
