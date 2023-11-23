import sqlite3

# Create a SQLite database file
conn = sqlite3.connect('ConferenceWebApp.db')
cursor = conn.cursor()

def initialise(cursor):
    """ Initialise the entire database. """
    try:
        # Delegates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delegates (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                )
                       ''')
        # Host users for conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                passwordHash TEXT NOT NULL
                )
                       ''')
        # Conferences created
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conferences (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                hostID INTEGER,
                paperSubDeadline DATE,
                delegateSignUpDeadline DATE,
                confStart DATE,
                confEnd DATE
                )
                       ''')
        # Speakers for the conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speakers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                delegateID INTEGER,
                FOREIGN KEY (delegateID) REFERENCES delegates(id)
                )
                       ''')
        # Talks being given at conferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS talks (
                talkID INTEGER PRIMARY KEY,
                talkName TEXT NOT NULL,
                speakerID INTEGER,
                confID INTEGER,
                FOREIGN KEY (speakerID) REFERENCES speakers(id),
                FOREIGN KEY (confID) REFERENCES conferences(id)
                )
                       ''')
        # Table for tastes and prefernces
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tastes (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                confID INTEGER,
                FOREIGN KEY (confID) REFERENCES conferences(id)
                )
                       ''')
        # Delegates like certain topics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delLikes (
                delegID INTEGER,
                topicID INTEGER,
                FOREIGN KEY (delegID) REFERENCES delegates(id),
                FOREIGN KEY (topicID) REFERENCES tastes(id)
                )
                       ''')
        # Hosts direct a conference
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hostConf (
                confID INTEGER,
                hostID INTEGER,
                FOREIGN KEY (confID) REFERENCES conferences(id),
                FOREIGN KEY (hostID) REFERENCES hosts(id)
                )
                       ''') 
        return True
    except sqlite3.Error as e:
        return False, f"Error adding user: {e}"

def addUser(cursor, username, passwdHash):
    # Adding a user to the database
    try:
        cursor.execute("INSERT INTO delegates (username, passwordHash) VALUES (?, ?)", (username, passwdHash))
        return True
    except sqlite3.Error as e:
        return False, f"Error adding user: {e}"

def editUser(cursor, username, email, passwdHash, topicPreferences):
    try:
        # Update password for the user
        cursor.execute("UPDATE delegates SET passwordHash = ?, email = ? WHERE username = ?", (passwdHash, email, username))

        # Get the existing delegate's ID
        delegate_id = cursor.execute("SELECT id FROM delegates WHERE username = ?", (username,)).fetchone()[0]

        # Clear existing topic preferences for the user in delLikes table
        cursor.execute("DELETE FROM delLikes WHERE delegID = ?", (delegate_id,))

        # Insert new topic preferences for the user in delLikes table
        taste_ids = []
        for topic in topicPreferences:
            # Get the ID of the topic from tastes table
            taste_id = cursor.execute("SELECT id FROM tastes WHERE topic = ?", (topic,)).fetchone()
            if taste_id:
                taste_ids.append(taste_id[0])

        for taste_id in taste_ids:
            cursor.execute("INSERT INTO delLikes (delegID, topicID) VALUES (?, ?)", (delegate_id, taste_id))

        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def findDelegate(cursor, username, fullSearch=False):
    try:
        # Find delegate's basic information (ID, Username)
        cursor.execute("SELECT id, username, email FROM delegates WHERE username = ?", (username,))
        delegate = cursor.fetchone()

        if delegate:
            delegate_id = delegate[0]
            delegate_username = delegate[1]
            delegate_email = delegate[2]

            if not fullSearch:
                # Return basic information (Username) if fullSearch is False
                return delegate_username, delegate_email
            else:
                # Fetch delegate's tastes of preferences along with associated conferences
                cursor.execute("""
                    SELECT tastes.topic, conferences.name
                    FROM delLikes
                    INNER JOIN tastes ON delLikes.topicID = tastes.id
                    INNER JOIN conferences ON delLikes.confID = conferences.id
                    WHERE delLikes.delegID = ?
                """, (delegate_id,))
                tastes_conferences = cursor.fetchall()

                # Prepare and return all information if fullSearch is True
                delegate_info = {
                    "Username": delegate_username,
                    "email": delegate_email,
                    "Tastes_Conferences": tastes_conferences
                    # Add more information if needed
                }
                return delegate_info
        else:
            return False, "Delegate not found"
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def delUser(cursor, username):
    try:
        # Get the delegate ID
        delegate_id = cursor.execute("SELECT id FROM delegates WHERE username = ?", (username,)).fetchone()

        if delegate_id:
            delegate_id = delegate_id[0]

            # Delete user's topic preferences
            cursor.execute("DELETE FROM delLikes WHERE delegID = ?", (delegate_id,))

            # Delete the user from delegates table
            cursor.execute("DELETE FROM delegates WHERE username = ?", (username,))
            return True
        else:
            return False
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def closeDatabase(cursor, conn):
    # Close the cursor and connection
    try:
        cursor.close()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error occurred: {e}")
        return False
