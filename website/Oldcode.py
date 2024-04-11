
# TODO REMOVE - Automating the creation of 200 test delegates for conference ID 8
import string
import random
from werkzeug.security import generate_password_hash

def generateRandomString(length=7):
    # Define the characters to choose from
    characters = string.ascii_letters + string.digits  # You can add more characters if needed
    
    # Generate the random string
    randomString = ''.join(random.choice(characters) for _ in range(length))
    
    return randomString

def generateRandomDateOfBirth(start_date, end_date):
    # Convert start_date and end_date strings to datetime objects
    startDate = datetime.strptime(start_date, '%Y-%m-%d')
    endDate = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Calculate the range of days between start_date and end_date
    delta = endDate - startDate
    
    # Generate a random number of days within the range
    randomNumberOfDays = random.randint(0, delta.days)
    
    # Add the random number of days to start_date to get the random date of birth
    randomDateOfBirth = startDate + timedelta(days=randomNumberOfDays)
    
    return randomDateOfBirth

# Create new delegates and assign random preference scores for each talk
def createNewDelegates(app, conference_id):
    def MessageMe(thing):
        """
        Tracking scheduler output seprately from the rest of the app.
        """
        myFile = open("autoGen.txt", "a")
        contents = f"{thing}\n"
        myFile.write(contents)
        myFile.close()
        return True
    
    with app.app_context():
        MessageMe("Starting to run autoGen >>>>")
        # Create random user details
        username = generateRandomString(6)
        password = generate_password_hash(generateRandomString(13))
        emailAddr = generateRandomString(6).join("@gmail.com")
        firstName = username
        lastName = generateRandomString(6)
        dateObj = generateRandomDateOfBirth('1950-01-01', '2005-12-31')
        dateStr = dateObj.strftime('%Y-%m-%d')
        # Parse the string date
        dob = datetime.strptime(dateStr, '%Y-%m-%d').date()
        usertype = 'delegate'
        newUser = User(
            username=username,
            passwordHash=password,
            email=emailAddr,
            firstName=firstName,
            lastName=lastName,
            dob=dob,
            type=usertype
        )
        db.session.add(newUser)
        db.session.commit()
        MessageMe(f"--> User {newUser.id} : {[username, password, emailAddr, firstName, lastName, dob]}")
        # Register the user for the conference
        userId = newUser.id
        registration = ConfDeleg(
            confId=conference_id,
            delegId=userId
        )
        db.session.add(registration)
        db.session.commit()
        # Retrieve all talks associated with the conference
        talks = Talks.query.filter_by(confId=conference_id).all()
        collection = []
        for thing in talks:
            talkId = thing.id
            topicIDs = []
            assoTopics = TopicTalks.query.filter_by(talkId=talkId).all()
            for topic in assoTopics:
                topicIDs.append(topic.topicId)
            record = [talkId, topicIDs]
            collection.append(record)
        # And rate the talks
        for talk in collection:
            rating = random.randint(1, 10)
            recording = DelegTalks(
                delegId=userId,
                talkId=talk[0],
                confId=conference_id,
                prefLvl=rating
            )
            db.session.add(recording)
            db.session.commit()
            MessageMe(f"--|--|--> {userId} : {talk[0]}, {rating}")
            if rating >= 6:
                # Add a record to DelTopics table too
                for topicId in talk[1]:
                    entry = DelTopics(
                        delegId=userId,
                        topicId=topicId,
                        confId=conference_id
                    )
                    db.session.add(entry)
                    db.session.commit()
                    MessageMe(f"--|--|--|--|--> {userId} : {topicId}")
        return True
    
'''# Usage example
conference_id = 8 # ID of the new conference
num_delegates = 193 # Number of delegates to create
runTime = datetime.now() + timedelta(seconds=10)
jobArgs = (app, conference_id)'''          
                
                
                
                """FIX THIS VVVVV """
                
                """NO USERS IN EITHER TABLE CAN HAVE THE SAME USERNAME"""
                # Check the username does not already exists
                # If the pre-existing user is a host
                finderHost = findHost(cursor, username)
                # If the pre-existing user is a delegate
                finderDele = findDelegate(cursor, username) # Basic search used here - Array type returned
                # User is not a host or a delegate --> Username does not already exist
                if (finderHost[0] == False) and (finderDele[0] == False):
                    type = "USER NOT FOUND!"
                if type == "USER NOT FOUND!":
                    if len(password) == 0:
                        flash("Please enter a strong password.", category='error')
                    elif len(confirm) == 0:
                        flash("Please re-enter your password.", category='error')
                    elif len(dob) == 0:
                        flash("Please enter a date of birth.", category='error')
                    elif len(email) == 0 or "@" not in email:
                        flash("Please enter a valid email.", category='error')
                    else:
                        passwdHash = generate_password_hash(password, method="sha256")
                        if check_password_hash(passwdHash, confirm) == False:
                            flash("Please enter matching passwords.", category="error")
                        else:
                            if email != "" or "@" not in email:
                                emailAddr = "None"
                            else:
                                emailAddr = email
                                
                            # Add user to database.
                            if usertype == 'delegate': 
                                addDelegate(cursor, username, passwdHash, dob, emailAddr)
                                
                            else:
                                addHost(cursor, username, passwdHash, dob, emailAddr)
                            idUsed = cursor.lastrowid
                            userinfo = [username, passwdHash, email, idUsed]
                            try:
                                conn.commit()
                                cursor.close()
                                conn.close()
                                flash("Successfully signed up!", category='success')
                                UpdateLog(f"New User: {username} added to the system.")
                                sessionUsr = User(userinfo, idUsed, usertype)
                                login_user(sessionUsr, remember=True) # Create session for user
                                return redirect(url_for("views.home"))
                            except Exception as e:
                                flash(f"Error registering account: {e}", category='error')
                else:
                    
                    
                    
                    type = "host"
        try:
            # If the logging in user is a host
            finder = findHost(cursor, username)
            if finder[0]:
                user = finder[1]
            else: # User is not a host
                type = "delegate"
        except Exception as e:
            UpdateLog(f"(1) SQL ERROR: {e}")
            type = "delegate"
        # If the logging in user is a delegate
        if type == "delegate":
            try:
                # Basic search used here - Array type returned
                finder = findDelegate(cursor, username)
                if finder[0]:
                    user = finder[1]
                else: # User is not a delegate
                    type = "USER NOT FOUND!"
            except Exception as e:
                UpdateLog(f"(2) SQL ERROR: {e}")
                # Otherwise the user seeminly does not exist
                type = "USER NOT FOUND!"