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
                email TEXT NOT NULL,
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

def addDelegate(cursor, username, email, passwdHash):
    # Adding a user to the database
    try:
        cursor.execute("INSERT INTO delegates (username, email, passwordHash) VALUES (?, ?, ?)", (username, email, passwdHash))
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

def addHost(cursor, username, email, passwdHash):
    try:
        # Add a new host to the hosts table
        cursor.execute("INSERT INTO hosts (username, email, passwordHash) VALUES (?, ?, ?)", (username, email, passwdHash))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"
    
def editHost(cursor, username, passwdHash, email):
    try:
        # Update password and email for the host in the hosts table
        cursor.execute("UPDATE hosts SET passwordHash = ?, email = ? WHERE username = ?", (passwdHash, email, username))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def findHost(cursor, username):
    try:
        # Find host's ID and username in the hosts table based on the username
        cursor.execute("SELECT id, username FROM hosts WHERE username = ?", (username,))
        host = cursor.fetchone()
        return True, host if host else False, "Host not found"
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"
    
def delHost(cursor, username):
    try:
        # Delete the host from the hosts table based on the username
        cursor.execute("DELETE FROM hosts WHERE username = ?", (username,))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def addConference(cursor, name, hostID, paperSubDeadline, delegateSignUpDeadline, confStart, confEnd):
    try:
        # Add a new conference to the conferences table
        cursor.execute("""
            INSERT INTO conferences (name, hostID, paperSubDeadline, delegateSignUpDeadline, confStart, confEnd)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, hostID, paperSubDeadline, delegateSignUpDeadline, confStart, confEnd))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"

def editConference(cursor, conference_id, name, hostID, paperSubDeadline, delegateSignUpDeadline, confStart, confEnd):
    try:
        # Update conference details in the conferences table based on the conference ID
        cursor.execute("""
            UPDATE conferences 
            SET name = ?, hostID = ?, paperSubDeadline = ?, delegateSignUpDeadline = ?, confStart = ?, confEnd = ?
            WHERE id = ?
        """, (name, hostID, paperSubDeadline, delegateSignUpDeadline, confStart, confEnd, conference_id))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"
    
def findConference(cursor, conference_id, fullSearch=False):
    try:
        if not fullSearch:
            # Less detailed search
            cursor.execute("SELECT * FROM conferences WHERE id = ?", (conference_id,))
            conference = cursor.fetchone()
            return True, conference if conference else False, "Conference not found"
        else:
            # More detailed search including talks, speakers, topics, and delegate count
            cursor.execute("""
                SELECT conferences.id, conferences.name, conferences.hostID, conferences.paperSubDeadline, 
                       conferences.delegateSignUpDeadline, conferences.confStart, conferences.confEnd,
                       COUNT(DISTINCT delegates.id) as delegateCount
                FROM conferences
                LEFT JOIN talks ON conferences.id = talks.confID
                LEFT JOIN speakers ON talks.speakerID = speakers.id
                LEFT JOIN delLikes ON conferences.id = delLikes.confID
                LEFT JOIN delegates ON delLikes.delegID = delegates.id
                WHERE conferences.id = ?
                GROUP BY conferences.id
            """, (conference_id,))
            conference = cursor.fetchone()

            if conference:
                # Fetching detailed information about talks, speakers, and topics associated with the conference
                cursor.execute("""
                    SELECT talks.talkName, speakers.name AS speaker, GROUP_CONCAT(tastes.topic) AS topics
                    FROM talks
                    LEFT JOIN speakers ON talks.speakerID = speakers.id
                    LEFT JOIN tastes ON tastes.confID = talks.confID
                    WHERE talks.confID = ?
                    GROUP BY talks.talkName
                """, (conference_id,))
                talks = cursor.fetchall()

                # Assemble detailed conference information
                detailed_info = {
                    "Conference_ID": conference[0],
                    "Conference_Name": conference[1],
                    "Host_ID": conference[2],
                    "Paper_Sub_Deadline": conference[3],
                    "Delegate_SignUp_Deadline": conference[4],
                    "Conf_Start": conference[5],
                    "Conf_End": conference[6],
                    "Delegate_Count": conference[7],
                    "Talks_Info": talks  # Include talks information in the detailed search
                }
                return True, detailed_info
            else:
                return False, "Conference not found"
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"
    
def delConference(cursor, conference_id):
    try:
        # Delete the conference from the conferences table based on the conference ID
        cursor.execute("DELETE FROM conferences WHERE id = ?", (conference_id,))
        return True
    except sqlite3.Error as e:
        return False, f"Error occurred: {e}"
    
  
