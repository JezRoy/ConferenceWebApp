import sqlite3

# Create a SQLite database file
conn = sqlite3.connect('ConferenceWebApp.db')
cursor = conn.cursor()

def initialise():
    """ Initialise the entire database. """
    try:
        # Delegates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delegates
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                       ''')
        # Host users for conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hosts
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                       ''')
        # Conferences created
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conferences
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                hostID INTEGER,
                paperSubDeadline DATE,
                delegateSignUpDeadline DATE,
                confStart DATE,
                confEnd DATE
                       ''')
        # Speakers for the conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speakers
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                delegateID INTEGER,
                FOREIGN KEY (delegateID) REFERENCES delegates(id)
                       ''')
        # Talks being given at conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS talks
                talkID INTEGER PRIMARY KEY,
                talkName TEXT NOT NULL,
                speakerID INTEGER,
                confID INTEGER,
                FOREIGN KEY (speakerID) REFERENCES speakers(id),
                FOREIGN KEY (confID) REFERENCES conferences(id)
                       ''')
        # Table for tastes and prefernces
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tastes
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                confID INTEGER,
                FOREIGN KEY (confID) REFERENCES conferences(id)
                       ''')
        # Delegates like certain topics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delLikes
                delegID INTEGER,
                topicID INTEGER,
                FOREIGN KEY (delegID) REFERENCES delegates(id),
                FOREIGN KEY (topicID) REFERENCES tastes(id),
                       ''')
        # Hosts direct a conference
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hostConf
                confID INTEGER,
                hostID INTEGER,
                FOREIGN KEY (confID) REFERENCES conferences(id),
                FOREIGN KEY (hostID) REFERNCES hosts(id)
                       ''') 
        return True
    except:
        return False

conn.close()
