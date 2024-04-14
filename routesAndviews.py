# Initialisations
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, TopicTalks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from .functions import UpdateLog
from . import parallelSys

dbOrderingConf = [
    'confName',
    'confURL',
    'paperFinalisationDate',
    'delegSignUpDeadline',
    'confStart',
    'confEnd',
    'confLength',
    'dayStart',
    'dayEnd',
    'dayDuration',
    'talkPerSession',
    'talkLength',
    'numSessions'
]

""" TODO
    create:
        - refuse registration past the deadline
        - fix schedule page for delegates
        - genetic scheduler?
        - verify correct host for conference edits
    optional talks vs preferred talks (for those with a low preference level)
    bug fix:
        - search page: show all conferences by default
        
"""

def deduceSchedule(confId, userId, userData, ConferenceData):
    currentDay = 1
    if ConferenceData:
        present = date.today()
        elapsed = (present - ConferenceData["confStart"]).days
        if elapsed <= 0:
            elapsed = 0
        currentDay = elapsed + 1
        ConferenceData["currentDay"] = currentDay

        # Find most optimised schedule from the schedules created for the upcoming conference
        lookup = Schedules.query.filter_by(confId=confId).first()
        if lookup:
            fileToSee = lookup.file
            schedule = {}
            with open(fileToSee, "r") as file:
                content = file.readlines()
            day = 1
            for line in content:
                if line[0:2] == 'D-':
                    day = int(line[2])
                    schedule[day] = {}
                else:
                    hour = int(line[0:2])
                    minute = int(line[3:5])
                    timing = time(hour, minute)
                    try: # A normal set of talk slots is cheduled at this time
                        start = line.index("[")
                        end = len(line) - 1
                        # [35, 'None', 'None'] for example
                        talks = line[start+1:end-1].split(",") # produces ['35', 'None', 'None']
                        paraSesh = []
                        for talk in talks:
                            paraSesh.append(eval(talk))
                        # time(9, 0): [35, None, None] for example
                        schedule[day][timing] = paraSesh
                    except: # Instead a break, or lunch time is scheduled here
                        detail = line[9:-1]
                        schedule[day][timing] = detail


            # TODO Fill in empty slots with optional talks
            # For each talk, determine whether this user needs to see it:
            # A delegate will see things in a single-session style of view        
            delegView = {}
            if userData.type == "delegate": 
                for day, dayTime in schedule.items():
                    delegView[day] = {}
                    for timing, talkIds in dayTime.items(): # Iterate through the whole "Master schedule"
                        if talkIds != "BREAK" or talkIds != "LUNCH & REFRESHMENTS":
                            for index in range(len(talkIds)):
                                thisTalk = talkIds[index]
                                if type(thisTalk) is int: # If there is a talk here
                                    talk = Talks.query.filter_by(confId=confId, id=thisTalk).first() # Find the talk name and speaker
                                    speaker = Speakers.query.filter_by(id=talk.speakerId).first()
                                    delegs = DelegTalks.query.filter_by(talkId=thisTalk, confId=confId).all()
                                    for person in delegs:
                                        if person.prefLvl >= 5: # Find all the delegates who who wanted to see it
                                            if person.id == userId: # If this includes the currently logged in user
                                                stuff = [talk.talkName, speaker.deleg] # Add it to the list of things to see
                                                delegView[day][timing] = stuff
                                                break
                        else:
                            delegView[day][timing] = talkIds   
                schedule = delegView
            else: # Host users can see everything in a multi-session view
                for day, dayTime in schedule.items():
                    for timing, talkIds in dayTime.items():        
                        for index in range(len(talkIds)):
                            thisTalk = talkIds[index]
                            if type(thisTalk) is int:
                                # For each talk Id, replace the talk Id with the talk Name, speaker name, and delegates who are indeed interested
                                talk = Talks.query.filter_by(confId=confId, id=thisTalk).first()
                                speaker = Speakers.query.filter_by(id=talk.speakerId).first()
                                stuff = [talk.id, talk.talkName, speaker.deleg]
                                schedule[day][timing][index] = stuff
        else:
            schedule = None
    else:
        schedule = None
    return schedule, currentDay

# Arguments to consider when rendering a template
"""
DEFAULTS:
- When using flash() to flash alerts and warning there are 3 string categories:
    - error
    - info
    - warning
    - success
- {{ session.username }} defines whether a user is signed in.
- {{ conferenceSigned }} determines if a user is signed up to a conference.
    if so, then present the option to see that conference.
    - May require a conference search up beforehand to also pass in the URL
    to a conference as a link in the navbar:
        - referred to with {{ conferenceURL }}
        - name of the NEXT conference goes in the navbar top: {{ conferenceName }}.
"""

# Setting up a navigation blueprint for the flask application
views = Blueprint('views', __name__)
'''TODO MAYBE UPDATE CONFERENCE ID 8 WITH THE TOPICCONF TABLE'''
@views.route('/') # The main page of the website
@login_required
def home():

    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    session['type'] = userData.type
    #print("-------------\n", session, "\n-------------\n")

    # Find next upcoming conference from list of registered conferences
        # Query the ConfDeleg or ConfHosts table to find the conferences a user is registered to
    # Get the conference IDs the user is registered to
    if session['type'] == "host":
        userConferences = ConfHosts.query.filter_by(hostId=userData.id).all()
    else:
        userConferences = ConfDeleg.query.filter_by(delegId=userData.id).all()
    
    conferenceIds = [conference.confId for conference in userConferences]
        # Query the Conferences table to get the details of the conferences

    conferencesUserRegister = Conferences.query.filter(Conferences.id.in_(conferenceIds)).all()
        # Get the current date and time 
        
    rightNow = datetime.now()
        # Filter out conferences that have yet to be engaged and store them in a list
    upcomingConferences = []
    for conference in conferencesUserRegister:
        if conference.confEnd >= rightNow.date():
            # Sort the upcoming_conferences based on their start date
            upcomingConferences.append(conference)  
    
    confId = None
    sortedConferences = sorted(upcomingConferences, key=lambda x: x.confStart)
    if sortedConferences:
        NextConf = sortedConferences[0]
        confId = NextConf.id
        # Fetch additional information about the next upcoming conference from the database
        ConferenceData = Conferences.query.filter_by(id=NextConf.id).first()
        ConferenceData = ConferenceData.__dict__
        ConferenceData.pop('_sa_instance_state', None)
        ConferenceData = {key: ConferenceData[key] for key in dbOrderingConf if key in ConferenceData}
        ConferenceData["confId"] = confId
    else:
        ConferenceData = None

    schedule, currentDay = deduceSchedule(confId, userId, userData, ConferenceData)

    # This information will be sorted within the front end
    # Load HTML page
    return render_template("index.html", 
                           user=current_user,
                           userData=userData,
                           currentDate=date.today().strftime("%d-%m-%Y"),
                           currentDay=currentDay,
                           schedule=schedule,
                           ConferenceData=ConferenceData)

@views.route('/create-conference-1', methods=['GET', 'POST'])
@login_required
def createConferenceStage1(): # For a host to a create a conference - part 1
    """ Setup conference initial details """
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == 'POST':
        # Data validation
        confStartDate = request.form.get("confstart")
        confEndDate = request.form.get("confend")
        startDay = datetime.strptime(confStartDate, '%Y-%m-%d').date()
        endDay = datetime.strptime(confEndDate, '%Y-%m-%d').date()
        confLength = int((endDay - startDay).days)
        # TODO try and except neeeded here
        dayStartDate = request.form.get("daystart")
        dayEndDate = request.form.get("dayend")
        startTime = datetime.strptime(dayStartDate, '%H:%M').time()
        endTime = datetime.strptime(dayEndDate, '%H:%M').time()
        dayLengthMins = (endTime.hour * 60 + endTime.minute) - (startTime.hour * 60 + startTime.minute)
        dayLength = round(dayLengthMins / 60, 2)
        talkPerSession = int(request.form.get("talksPerSession"))
        talkLength = int(request.form.get("talkLength"))
        numOfSessions = int(request.form.get("numSessions"))
        if confLength > 0:
            if dayLength > 0:
                if numOfSessions > 0:
                    # Setup object for database
                    conference = Conferences(
                        confName = request.form.get("confname"),
                        confURL = request.form.get("confurl"),
                        paperFinalisationDate = datetime.strptime(request.form.get("paperfinal"), '%Y-%m-%d').date(),
                        delegSignUpDeadline = datetime.strptime(request.form.get("delegRegisterDeadline"), '%Y-%m-%d').date(),
                        confStart = startDay,
                        confEnd = endDay,
                        confLength = confLength,
                        dayStart = startTime,
                        dayEnd = endTime,
                        dayDuration = dayLength,
                        talkPerSession = talkPerSession,
                        talkLength = talkLength,
                        numSessions = numOfSessions
                    )
                    # Add and commit to all relevant database tables
                    db.session.add(conference)
                    db.session.commit()
                    confNewId = conference.id
                    referalCheck = Conferences.query.get(confNewId).__dict__ # A handy way of checking the flow of data into the database after creating a conference.
                    referalCheck.pop('_sa_instance_state')
                    referalCheck = {key: referalCheck[key] for key in dbOrderingConf if key in referalCheck}
                    UpdateLog(f"Host '{userData.id}, {userData.username}' created conference:\n{referalCheck} ")
                    hosting = ConfHosts(
                        confId = confNewId,
                        hostId = userId
                    )
                    db.session.add(hosting)
                    db.session.commit()                
                    flash("Successfully created conference! You can edit / delete your main conference details later.", category="success")
                    return redirect(url_for("views.createConferenceStage2", conferenceId=confNewId))
                else:
                    flash("There must be at least one session active in a day.", category="error")
            else:
                flash("The end time must be after the start time.", category="error")
        else:
            flash("The end date must be after the start date.", category="error")
    else:
        if session['type'] != "host":
            flash("Incorrect access rights: User is not a host.", category="error")
            return redirect(url_for("views.home"))
    return render_template("createconf.html",
                            user=current_user,
                            userData=userData,
                            stage=1,
                            confId=None)

@views.route('/create-conference-2/<int:conferenceId>', methods=['GET', 'POST'])
@login_required
def createConferenceStage2(conferenceId): # For a host to a create a conference - part 1
    """ Setup conference talks """
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == 'POST':
        talkNames = request.form.getlist("talkname[]")
        talkSpeakers = request.form.getlist("talkspeaker[]")
        talkTopics = request.form.getlist("talktags[]")

        # Creating a structure for created talks
        """A user is not obliged to create a talk at this stage...
        But should they choose to, a talk needs a name.
        """
        talksGenerated = []
        for i in range(len(talkNames)):
            talksGenerated.append([talkNames[i], talkSpeakers[i], talkTopics[i]])
            # Entities involved include:
            speaker = Speakers(
                deleg=talkSpeakers[i]
            )
            db.session.add(speaker)
            db.session.commit()
            speakerId = speaker.id
            talks = Talks(
                    talkName=talkNames[i],
                    speakerId=speakerId,
                    confId=conferenceId,
                )
            db.session.add(talks)
            db.session.commit()
            talkID = talks.id
            topics = talkTopics[i].split(', ')
            for word in topics:
                # Example: [topic1, topic2, topic3, topic4]
                topicWord = Topics(
                    topic=word
                )
                db.session.add(topicWord)
                db.session.commit()
                wordId = topicWord.id
                talktopic = TopicTalks(
                    talkId=talkID,
                    topicId=wordId
                )
                db.session.add(talktopic)
                db.session.commit()
                topic2conf = Topicsconf(
                    topicId=wordId,
                    confId=conferenceId
                )
                db.session.add(topic2conf)
                db.session.commit()
        UpdateLog(f"Host ID: {userId} successefully added the following Talks to the conference ID {conferenceId}:\n{talksGenerated}")    
        flash("Talks added to conference successfully!", category="success")
        return redirect(url_for("views.home"))
    else:
        if session['type'] != "host":
            flash("Incorrect access rights: User is not a host.", category="error")
            return redirect(url_for("views.home"))
        elif conferenceId == None:
            flash("Incorrect access rights: Conference not provided as context.", category="error")
            return redirect(url_for("views.home"))
    return render_template("createconf.html",
                            user=current_user,
                            userData=userData,
                            stage=2,
                            conferenceId=conferenceId)

@views.route('/find-conference', methods=['GET', 'POST'])
@login_required
def findConferences():
    """Search for conferences"""
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == 'POST':
        query = request.form.get("conferenceSearch", "").strip()
        button = request.form.get('submitButton')
        if button == 1: # Search for conferences that have a similar name to search query.
            results = Conferences.query.filter(Conferences.confName.ilike(f"{query}%")).all()
            results = Conferences.query.filter(Conferences.confName.ilike(f"%{query}%")).all()
            results = list(set(results))
        else: # Just return all registered conferences.
            results = Conferences.query.all()
        setOfResults = []
        for conf in results:
            retrieve = conf.__dict__
            retrieve.pop('_sa_instance_state', None)
            retrieve = {key: retrieve[key] for key in dbOrderingConf if key in retrieve}
            retrieve["confId"] = conf.id
            registered = db.session.query(db.exists().where(ConfDeleg.delegId == userId and ConfDeleg.confId == conf.id)).scalar()
            retrieve["registered"] = registered
            setOfResults.append(retrieve)
        confFound = setOfResults
    else:
        confFound = None
    return render_template("find.html",
                            user=current_user,
                            userData=userData,
                            confFound=confFound
                        )

@views.route('/register-conference', methods=['POST'])
@login_required
def registerConference():
    """To register a user to a conference"""
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    conferenceChoice = request.form.get("conferenceId")
    registration = ConfDeleg(
        confId=conferenceChoice,
        delegId=userId
    )
    # Check the user is not already registered
    preregistered = db.session.query(db.exists().where(ConfDeleg.delegId == userId and ConfDeleg.confId == conferenceChoice)).scalar()
    if not preregistered:
        conf = Conferences.query.get(conferenceChoice).__dict__
        confName = conf['confName']
        # TODO CHECK THE REGISTRATION DEADLINE
        db.session.add(registration)
        db.session.commit()
        flash(f"You have been successfully registered to the '{confName}' conference!", category="success")
        # Get a user to register their talks
        UpdateLog(f"User {userData.username} has signed up for conference {confName} ")
    else:
        flash("You have already registered for this conference.", category="warning")
    return redirect(url_for("views.home"))

@views.route('/cancel-registration/<int:conferenceId>', methods=['POST'])
@login_required
def cancelRegistration(conferenceId):
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    conf = Conferences.query.filter_by(id=conferenceId).first().confName
    if request.method == 'POST':
        if session['type'] == "delegate":
            try:
                registration = ConfDeleg.query.filter_by(delegId=userData.id, confId=conferenceId).first()
                db.session.delete(registration)
                db.session.commit()
                UpdateLog(f"User {userData.id} has been removed from conference {conferenceId}.")
                try:
                    talksFound = DelegTalks.query.filter_by(delegId=userData.id, confId=conferenceId).all()
                    try:
                        for talk in talksFound:
                            db.session.delete(talk)
                            db.session.commit()
                        UpdateLog(f"User {userData.id} has been removed from all talks in conference {conferenceId}.")
                    except:
                        pass
                except:
                    pass
                try:
                    topicsFound = DelTopics.query.filter_by(delegId=userData.id, confId=conferenceId).all()
                    try:
                        for topic in topicsFound:
                            db.session.delete(topic)
                            db.session.commit()
                        UpdateLog(f"User {userData.id} has been removed from all topics in conference {conferenceId}.")
                    except:
                        pass
                except:
                    pass
                flash(f"Your registration for conference {conf} has been cancelled.", category="success")
            except:
                flash(f"Sorry. There was an error cancelling your registration for conference {conf}.", category="error")
    return redirect(url_for("views.home"))

@views.route('/terminate-conference/<int:conferenceId>', methods=['POST'])
@login_required
def terminateConference(conferenceId):
    userId = current_user._get_current_object().id
    conference = Conferences.query.filter_by(id=conferenceId).first()
    if request.method == "POST":
        if session['type'] == "host":
            # Delete conference sessions
            schedules = Schedules.query.filter_by(confId=conferenceId).all()
            for schedule in schedules:
                try:
                    db.session.delete(schedule)
                    db.session.commit()
                except:
                    pass
            # Delete talks and topics associated with a conference
            talks = Talks.query.filter_by(confId=conferenceId).all()
            for talk in talks:
                tid = talk.id
                sid = talk.speakerId
                speakers = Speakers.query.filter_by(id=sid).all()
                for spe in speakers:
                    try:
                        db.session.delete(spe)
                        db.session.commit()
                    except:
                        pass
                preferences = DelegTalks.query.filter_by(talkId=tid, confId=conferenceId).all()
                for thing in preferences:
                    try:
                        db.session.delete(thing)
                        db.session.commit()
                    except:
                        pass
                topAsso = TopicTalks.query.filter_by(talkId=tid).all()
                for top in topAsso:
                    topId = top.topicId
                    topics = Topics.query.filter_by(id=topId).all()
                    for topic in topics:
                        try:
                            db.session.delete(topic)
                            db.session.commit()
                        except:
                            pass
                    topConfs = Topicsconf.query.filter_by(topicId=topId, confId=conferenceId).all()
                    for ting in topConfs:
                        try:
                            db.session.delete(ting)
                            db.session.commit()
                        except:
                            pass
                    dtcs = DelTopics.query.filter_by(topicId=topId, confId=conferenceId).all()
                    for dtc in dtcs:
                        try:
                            db.session.delete(dtc)
                            db.session.commit()
                        except:
                            pass
                    try:
                        db.session.delete(top)
                        db.session.commit()
                    except:
                        pass
                db.session.delete(talk)
                db.session.commit()
            delegates = ConfDeleg.query.filter_by(confId=conferenceId).all()
            for deleg in delegates:
                try:
                    db.session.deletete(deleg)
                    db.session.commit()
                except:
                    pass
            hostings = ConfHosts.query.filter_by(confId=conferenceId).first()
            try:
                db.session.delete(hostings)
                db.session.commit()
            except:
                pass
            name = conference.confName
            try:
                db.session.delete(conference)
                db.session.commit()
            except:
                pass
            flash(f"You have successfully deleted the {name} conference.", category="success")
            UpdateLog(f"User Id {userId} deleted conference {name}.")
            return redirect(url_for("views.home"))
            
@views.route('/preview-talks/<int:conferenceId>', methods=['GET', 'POST'])
@login_required
def previewTalks(conferenceId):
    """Register a user to certain talks and how much they are liked"""
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == "POST":
        talkIds = request.form.getlist('talkIds[]')
        prefLvls = request.form.getlist('talkPref[]')
        for i in range(len(talkIds)):
            # Record / Update the preference of each talk for each delegate
            existing1 = DelegTalks.query.filter_by(delegId=userId, talkId=talkIds[i], confId=conferenceId).first()
            if existing1: # Update an existing preference
                existing1.prefLvl = prefLvls[i]
                db.session.add(existing1)
                db.session.commit()
            else: # Or create a new one
                recording = DelegTalks(
                    delegId=userId,
                    talkId=talkIds[i],
                    confId=conferenceId,
                    prefLvl=prefLvls[i]
                )
                db.session.add(recording)
                db.session.commit()
                
                # Record a delegate's interest in each topic associated with a talk if above preference level 5
                if int(prefLvls[i]) >= 6:
                    topicsTalks = TopicTalks.query.filter_by(talkId=talkIds[i]).all()
                    for record in topicsTalks:
                        recordId = record.topicId
                        newEntry = DelTopics(
                            delegId=userId,
                            topicId=recordId, # Every topic appears to be unique, because of a unique ID by default
                            confId=conferenceId
                        )
                db.session.add(newEntry)
                db.session.commit()
        flash("Your talk preferences for this conference has been saved!", category="success")
        UpdateLog(f"User ID: {userId} has saved their talk preferences for conference ID: {conferenceId}.")
        return redirect(url_for("views.home"))
    else:
        # Find the conference and the talks involved
        # Ensure user is registered
        registered = db.session.query(db.exists().where(
            ConfDeleg.confId == conferenceId,
            ConfDeleg.delegId == userId
        )).scalar()
        if not registered:
            flash("You might register yourself to this conference first.")
            return redirect(url_for("views.findConferences"))
        else:
            talks = Talks.query.filter_by(confId=conferenceId).all()
            # TODO Have a NOTHING message if talks have not been created yet
            collectedTalks = []
            # Assemble Talk information to pass onto to webpage
            for thing in talks:
                speaker = Speakers.query.get(thing.speakerId)
                talk = [thing.talkName, speaker.deleg]
                correspond = TopicTalks.query.filter_by(talkId=thing.id).all()
                topics = []
                for row in correspond:
                    wordSearch = Topics.query.get(row.id)
                    topics.append(wordSearch.topic)
                talk.append(topics)
                talk.append(thing.id)
                # RETRIEVE PREVIOUS PREFERENCES
                delegTalk = DelegTalks.query.filter_by(delegId=userId, talkId=thing.id, confId=conferenceId).all()
                if delegTalk != []: # A previous rating this talk exists
                    talk.append(delegTalk[0].prefLvl)
                else: # This talk has not been rated by the user.
                    talk.append(5)
                collectedTalks.append(talk)
                
    return render_template("talks.html", 
                           user=current_user,
                           userData=userData,
                           conferenceId=conferenceId,
                           collectedTalks=collectedTalks
                        )
   
@views.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def editProfile():
    """Edit a user's profile details"""
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == "POST":
        dataFetch = request.form
        valid = True
        # Validate fields if necesary
        if dataFetch['username'] != '':
            userData.username = dataFetch['username']
        if dataFetch['email'] != '':
            if "@" not in dataFetch['email']:
                flash('Please enter a valid email address','error')
                valid = False
            else:
                userData.email = dataFetch['email']
        if dataFetch['password'] != '':
            if dataFetch['confirmation']:
                same = check_password_hash(generate_password_hash(dataFetch['password']), dataFetch['confirmation'])
                if same:
                    hasher = generate_password_hash(dataFetch['password'])
                    userData.passwordHash = hasher
                else:
                    valid = False
                    flash("Please enter matching passwords.", category="error")
            else:
                valid = False
                flash("If you wish to change your password, please fill in both password fields. ", category="error")
        if dataFetch['first_name'] != '':
            userData.firstName = dataFetch['first_name']
        if dataFetch['last_name'] != '':
            userData.lastName = dataFetch['last_name']
        if valid:
            # Update database with new details
            db.session.commit()
            flash("Profile details successfully changed!", category="success")
            UpdateLog(f"User {userId}: {userData.username} updated their profile with the following details: {dataFetch}.")
            return redirect(url_for("views.home"))
        
    return render_template("profedit.html",
                           user=current_user,
                           userData=userData)

@views.route('/view-conference/<int:conferenceId>', methods=['GET', 'POST'])
@login_required
def viewConference(conferenceId):
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    conference = Conferences.query.filter_by(id=conferenceId).first()
    flash(f"Now showing the conference details for {conference.confName}.", category="success")

    ConferenceData = conference.__dict__
    ConferenceData.pop('_sa_instance_state', None)
    ConferenceData = {key: ConferenceData[key] for key in dbOrderingConf if key in ConferenceData}
    ConferenceData["confId"] = conferenceId

    schedule, currentDay = deduceSchedule(conferenceId, userId, userData, ConferenceData)

    return render_template("index.html", 
                           user=current_user,
                           userData=userData,
                           currentDate=date.today().strftime("%d-%m-%Y"),
                           currentDay=currentDay,
                           schedule=schedule,
                           ConferenceData=ConferenceData)

@views.route('/edit-conference-1/<int:conferenceId>', methods=['GET', 'POST'])
@login_required
def editConference1(conferenceId):
    """Edit the details of a conference."""
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == "POST":
        # Retrieve current data
        currentData = Conferences.query.filter_by(id=conferenceId).first()

        # Check what as an entry
        # See if anything actually changed
        attrChanged = {} # Keeps track of what was actually changed

        confName = request.form.get("confname")
        if confName != "" and confName != currentData.confName:
            attrChanged['confName'] = confName

        confURL = request.form.get("confurl")
        if confURL != "" and confURL != currentData.confURL:
            attrChanged['confURL'] = confURL

        confStartDate = request.form.get("confstart")
        confEndDate = request.form.get("confend")
        startDay = datetime.strptime(confStartDate, '%Y-%m-%d').date()
        endDay = datetime.strptime(confEndDate, '%Y-%m-%d').date()
        if startDay != currentData.confStart:
            attrChanged["confStart"] = startDay
        if endDay != currentData.confEnd:
            attrChanged["confEnd"] = endDay
        if startDay != currentData.confStart or endDay != currentData.confEnd:
            confLength = int((endDay - startDay).days)
            attrChanged["confLength"] = confLength
        else:
            confLength = currentData.confLength

        pfd = request.form.get("paperfinal")
        dsd = request.form.get("delegRegisterDeadline")
        try:
            paperFinalisationDate = datetime.strptime(pfd, '%Y-%m-%d').date()
            if pfd != "" and paperFinalisationDate != currentData.paperFinalisationDate:
                attrChanged["paperFinalisationDate"] = paperFinalisationDate
        except:
            paperFinalisationDate = currentData.paperFinalisationDate
        try:
            delegSignUpDeadline = datetime.strptime(dsd, '%Y-%m-%d').date()
            if dsd != "" and delegSignUpDeadline != currentData.delegSignUpDeadline:
                attrChanged["delegSignUpDeadline"] = delegSignUpDeadline
        except:
            delegSignUpDeadline = currentData.delegSignUpDeadline

        dayStartDate = request.form.get("daystart")
        dayEndDate = request.form.get("dayend")
        try:
            startTime = datetime.strptime(dayStartDate, '%H:%M').time()
            if dayStartDate != "" and startTime != currentData.dayStart:
                attrChanged["dayStart"] = startTime
        except:
            startTime = currentData.dayStart
        try:
            endTime = datetime.strptime(dayEndDate, '%H:%M').time()
            if dayEndDate != "" and endTime != currentData.dayEnd:
                attrChanged["dayEnd"] = endTime
        except:
            endTime = currentData.dayEnd
        
        if startTime != currentData.dayStart or endTime != currentData.dayEnd:
            dayLengthMins = (endTime.hour * 60 + endTime.minute) - (startTime.hour * 60 + startTime.minute)
            dayLength = round(dayLengthMins / 60, 2)
            attrChanged["dayDuration"] = dayLength
        else:
            dayLength = currentData.dayDuration
        
        talkPerSession = int(request.form.get("talksPerSession"))
        if talkPerSession != 0 and talkPerSession != currentData.talkPerSession:
            attrChanged["talkPerSession"] = talkPerSession

        talkLength = int(request.form.get("talkLength"))
        if talkLength != 0 and talkLength != currentData.talkLength:
            attrChanged["talkLength"] = talkLength

        numOfSessions = int(request.form.get("numSessions"))
        if numOfSessions != 0 and numOfSessions != currentData.numSessions:
            attrChanged["numSessions"] = numOfSessions

        # Update changes TODO DOES NOT SAVE PROPERLY
        # TRY ITERATING OVER SQLALCHEMY OBJ
        if attrChanged != {}:
            editedConf = Conferences.query.filter_by(id=conferenceId).first()
            for key, newVal in attrChanged.items():
                setattr(editedConf, key, newVal)
            db.session.commit()

            # Redirect to next page
            flash("Successfully edited conference! You can always edit / delete your main conference details later.", category="success")
            UpdateLog(f"Host id {userId} edited conference id {conferenceId}, fields changed: \n{attrChanged.keys()}")
        return redirect(url_for("views.editConference2", conferenceId=conferenceId))
    else:
        # Check the correct host
        verify = ConfHosts.query.filter_by(confId=conferenceId, hostId=userId).first()
        if verify: # Correct user found
            conference = Conferences.query.filter_by(id=conferenceId).first()
            ConferenceData = conference.__dict__
            ConferenceData.pop('_sa_instance_state', None)
            ConferenceData = {key: ConferenceData[key] for key in dbOrderingConf if key in ConferenceData}
            ConferenceData["confId"] = conferenceId
            return render_template("editconf.html",
                                user=current_user,
                                userData=userData,
                                stage=1,
                                ConferenceData=ConferenceData,
                                conferenceId=conferenceId)
        else:
            flash("Sorry, you do not have the correct authorisation to edit this conference.", category="error")
            return redirect(url_for("views.home"))

@views.route('/edit-conference-2/<int:conferenceId>', methods=['GET', 'POST'])
@login_required
def editConference2(conferenceId): # TODO TEST THIS
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    setOfTalks = Talks.query.filter_by(confId=conferenceId).order_by(Talks.id).all()
    talks = []
    # Retrieving all talk data for a conference
    for thing in setOfTalks:
        data = [thing.id, thing.talkName]
        speaker = Speakers.query.filter_by(id=thing.speakerId).first().deleg
        data.append([thing.speakerId, speaker])
        sets = TopicTalks.query.filter_by(talkId=thing.id).all()
        topicIds = []
        topicWords = []
        for ids in sets:
            topicLit = Topics.query.filter_by(id=ids.topicId).first().topic
            topicIds.append(ids.topicId)
            topicWords.append(topicLit)
        data.append(topicIds)
        data.append(topicWords)
        talks.append(data)

    if request.method == "POST":
        # Retrieve organic information
        talkIds = request.form.getlist("talkid[]")
        talkNames = request.form.getlist("talkname[]")
        speakerIds = request.form.getlist("talkspeakerid[]")
        speakerNames = request.form.getlist("talkspeaker[]")
        topicIds = request.form.getlist("talktagsid[]")
        topicNames = request.form.getlist("talktags[]")

        # Preparation for edits and removals
        talkIdsCle = [] # This should be in chronological order
        talkNamesCle = []
        speakerIdsCle = []
        speakerNamesCle = []
        topicIdsCle = []
        topicNamesCle = []
        # Add new talks
        for i in range(len(talkIds)):
            # Check what needs adding
            taid = int(talkIds[i])
            taName = talkNames[i]
            sid = int(speakerIds[i])
            sName = speakerNames[i]
            toIds = eval(topicIds[i]) # [1, 2] or []
            try:
                toNames = topicNames[i].split(',') # ['topicA', 'topicB']
                for x in range(len(toNames)):
                    ting = toNames[x]
                    if ting[0] == " ":
                        toNames[x] = ting.replace(" ", "", 1)
            except:
                toNames = []
            if taid == -1: # New talk
                if sid == -1: # Only add a new speaker if they currently are not found in the database
                    spFinder = None
                    for tObj in talks:
                        if tObj[2][1] == sName:
                            spFinder = talks.index(tObj)
                            break
                    if spFinder == None:
                        # No existing speaker with this name found
                        speaker = Speakers(
                            deleg = sName
                        )
                        db.session.add(speaker)
                        db.session.commit()
                        assignspId = speaker.id
                    else:
                        assignspId = talks[spFinder][2][0]
                talk = Talks( # Add new talk
                    talkName=taName,
                    speakerId=assignspId,
                    confId=conferenceId
                )
                db.session.add(talk)
                db.session.commit()
                newtaId = talk.id
                # Only create a new topic record if not already existing
                # Observe each topic name, and see if already existing
                if toNames != []:
                    if toIds == []: # Talks are given but they don't have ids
                        for to in toNames:
                            foundId = -1
                            for tObj in talks:
                                if to in tObj[4]:
                                    finder = tObj[4].index(to)
                                    foundId = tObj[3][finder] # If the id exists already
                                    break
                            if foundId != -1: # The topic label exists already
                                contact = TopicTalks( # If existing, find existing topicId
                                    talkId=newtaId,
                                    topicId=recordId
                                )
                                db.session.add(contact)
                                db.session.commit()
                            # Add to TopicTalks entity
                            else: # Completely new topic found
                                topicEntry = Topics( # If not existing, add new topic record
                                    topic = to
                                )
                                db.session.add(topicEntry)
                                db.session.commit()
                                recordId = topicEntry.id
                                contact = TopicTalks(
                                    talkId=newtaId,
                                    topicId=recordId
                                )
                                db.session.add(contact)
                                db.session.commit()
            else:
                talkIdsCle.append(taid)
                talkNamesCle.append(taName)
                speakerIdsCle.append(sid)
                speakerNamesCle.append(sName)
                topicIdsCle.append(toIds)
                topicNamesCle.append(toNames)
            # No more additions to be made
        
        deleted = []
        # Iterate through the before-version of the list of talks to find deleted talks
        for btId, *_ in talks:
            if btId not in talkIdsCle:
                deleted.append([btId, *_])
        for talk in deleted:
            itemFound = Talks.query.filter_by(id=talk[0],confId=conferenceId).first()
            db.session.delete(itemFound)
            db.session.commit()
            talks.remove(talk)

        # Iterate through both before and after versions of the list of talks to implement changes.
        # Hopefully the list of talks after edits and the 'talks' list should be the same size
        for i in range(len(talkIdsCle)):
            taId = talkIdsCle[i]
            updateTalk = Talks.query.filter_by(id=taId, confId=conferenceId).first()
            taName = talkNamesCle[i]
            sId = speakerIdsCle[i]
            sName = speakerNamesCle[i]
            toIds = topicIdsCle[i]
            toNames = topicNamesCle[i]
            # An edit is nothing but a deletion of old data,
            # Then a replacement with new data.

            if talks[i][1] != taName:
                updateTalk.talkName = taName
                db.session.commit()
            updateSp = Speakers.query.filter_by(id=sId).first()
            if talks[i][2][1] != sName:
                updateSp.deleg = sName
                db.session.commit()
            if talks[i][3] != toIds or talks[i][4] != toNames: # Find the differences
                toAdd = []
                toRemove = []
                default = True # Default edit behavior
                # Two things can happen:
                # Either there is a complete wipe of old topics
                # Or some of the old topics stick around
                if len(talks[i][3]) < len(toNames):
                    default = False # Add missing labels
                    # [112, 113, 114]
                    # ['Duality', 'One-Way Functions', 'Average-Case Symmetry of Information'] vs
                    # ['Duality', 'One-Way Functions', 'Average-Case Symmetry of Information', 'Test Topic 1']
                    toAdd = [] # Average-Case Symmetry of Information
                    for x in range(len(toNames)):
                        if toNames[x] not in talks[i][4]:
                            toAdd.append(toNames[x])
                    for word in toAdd:
                        possible = Topics.query.filter_by(topic=word).all()
                        found = False
                        for record in possible:
                            finder = Topicsconf.query.filter_by(topicId=record.id, confId=conferenceId).first() # Find the right record if it exists
                            if finder:
                                found = True
                                assoId = finder.topicId # FOund pre-exising record
                                addition = TopicTalks(
                                    talkId=taId,
                                    topicId=assoId
                                )
                                db.session.add(addition)
                                db.session.commit()
                                break
                        if found == False: # No pre-existing topic existing
                            add1 = Topics( # Add new topic word
                                topic=word
                            )
                            db.session.add(add1)
                            db.session.commit()
                            newId = add1.id
                            add2 = TopicTalks(
                                talkId=taId,
                                topicId=newId
                            )
                            db.session.add(add2)
                            db.session.commit()
                            add3 = Topicsconf(
                                topicId=newId,
                                confId=conferenceId
                            )
                            db.session.add(add3)
                            db.session.commit()
                elif len(talks[i][3]) > len(toNames):
                    default = False # Remove excessive topics
                    # [112, 113, 114]
                    # ['Duality', 'One-Way Functions', 'Average-Case Symmetry of Information'] vs
                    # ['Duality', 'One-Way Functions']
                    toRemove = []
                    for x in range(len(talks[i][4])):
                        if talks[i][4][x] not in toNames:
                            toRemove.append(talks[i][3][x]) # Add corrsponding id for missing word
                    for id in toRemove:
                        record = TopicTalks.query.filter_by(talkId=taId, topicId=id).first()
                        if record:
                            db.session.delete(record)
                            db.session.commit()
                else:
                    # toAdd = [[114, 'Average-Case Symmetry of Information']]
                    # toRemove = [[1, 'Observable Systems']]
                    for j in range(len(toIds)):
                        if toNames[j] not in talks[i][4]:
                            toAdd.append([toIds[j], toNames[j]])
                    for j in range(len(talks[i][3])):
                        if talks[i][4][j] not in toNames:
                            toRemove.append([talks[i][3][j], talks[i][4][j]])
                if default == True:
                    for item in toRemove:
                        # Remove association between talk and old topic - NOT removing topic entirely
                        record = TopicTalks.query.filter_by(talkId=taId, topicId=item[0]).first()
                        if record:
                            db.session.delete(record)
                            db.session.commit()
                    for item in toAdd:
                        # Check if it already exists
                        query = Topics.query.filter_by(id=item[0]).first()
                        assoId = -1
                        if query == None:
                            # If not, add new topic word to database
                            newTopic = Topics(
                                topic=item[1]
                            )
                            db.session.add(newTopic)
                            db.session.commit()
                            assoId = newTopic.id
                        else:
                            assoId = item[0]
                        # Then make new association
                        record = TopicTalks(
                            talkId=taId,
                            topicId=assoId
                        )
                        db.session.add(record)
                        db.session.commit()
        flash("Edited conference talk details have been saved successfully!", category="success")
        UpdateLog(f"Host Id {userId} edited conference {conferenceId}'s talk details")
        return redirect(url_for("views.home"))
    else:
        # Retrieve current set of talks and present them
        return render_template("editconf.html",
                               user=current_user,
                               userData=userData,
                               stage=2,
                               talks=talks,
                               conferenceId=conferenceId)

@views.route('/user-conferences', methods=['GET', 'POST'])
@login_required
def userConferences():
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    typeUser = session['type']
    if userId and userData:
        conferences = []
        if typeUser == "host":
            # Hosts can view and edit a conference
            crossRefer = ConfHosts.query.filter_by(hostId=userId).all()
        else:
            # Delegates can only view the dashboard of a conference
            crossRefer = ConfDeleg.query.filter_by(delegId=userId).all()
        for conf in crossRefer:
            queryMe = Conferences.query.filter_by(id=conf.confId).first()
            data = {
                "id": conf.confId,
                "name": queryMe.confName,
                "pfd": queryMe.paperFinalisationDate,
                "dsd": queryMe.delegSignUpDeadline,
                "start": queryMe.confStart
            }
            conferences.append(data)
        # TODO Sort by start date
        return render_template("userconf.html", user=current_user,
                                                userData=userData,
                                                userType=typeUser,
                                                conferences=conferences)