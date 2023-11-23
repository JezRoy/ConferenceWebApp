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
            CREATE TABLE IF NOT EXISTS delLikes
                delegID INTEGER,
                topicID INTEGER,
                FOREIGN KEY (delegID) REFERENCES delegates(id),
                FOREIGN KEY (topicID) REFERENCES tastes(id)
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tastes
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hosts
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conferences
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                hostID INTEGER,
                paperSubDeadline DATE,
                delegateSignupDeadline DATE,
                confStart DATE,
                confEnd DATE
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speakers
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                delegateID INTEGER,
                FOREIGN KEY (delegateID) REFERENCES delegates(id)
                       ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS talks
                talkID INTEGER PRIMARY KEY,
                talkName TEXT NOT NULL,
                speakerID INTEGER,
                confID INTEGER,
                FOREIGN KEY (speakerID) REFERENCES speakers(id),
                FOREIGN KEY (confID) REFERENCES conferences(id)
                       ''')
        return True
    except:
        return False

conn.close()
