# Initialisations
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime, date, time
from .models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from .functions import UpdateLog

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
        
    if session['type'] == "Host":
        userConferences = ConfDeleg.query.filter_by(delegId=userData.id).all()
    else:
        userConferences = ConfHosts.query.filter_by(hostId=userData.id).all()
    print(userConferences)
        # Get the conference IDs the user is registered to
    conferenceIds = [conference.confId for conference in userConferences]
        # Query the Conferences table to get the details of the conferences
    conferencesUserRegister = Conferences.query.filter(Conferences.id.in_(conferenceIds)).all()
        # Get the current date and time
    rightNow = datetime.now()
        # Filter out conferences that have already started and store them in a list
    upcomingConferences = [
        conference for conference in conferencesUserRegister
        if conference.confStart >= rightNow
    ]
        # Sort the upcoming_conferences based on their start date
    sortedConferences = sorted(upcomingConferences, key=lambda x: x.confStart)
    if sortedConferences:
        NextConf = sortedConferences[0]
        # Fetch additional information about the next upcoming conference from the database
        ConferenceData = Conferences.query.filter_by(id=NextConf.id).first()
    else:
        ConferenceData = None
    #print(ConferenceData)
    # A DUMMY conference for testing - this should be database queried in future
    ConferenceData = {
        "id": 0,
        "name":"Blank2024",
        "url":"conf.blank.2024",
        "signUpDeadline":date.today().strftime('%d-%m-%Y'),
        "startDate": datetime(2023, 1, 9).strftime('%d-%m-%Y'),
        "endDate": datetime(2023, 1, 12).strftime('%d-%m-%Y')
    }
    
    # Find most optimised schedule from the schedules created for the upcoming conference
    
    # Load HTML page
    return render_template("index.html", 
                           user=current_user,
                           userData=userData,
                           currentDate=date.today().strftime("%d-%m-%Y"),
                           #schedule=schedule,
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
                    UpdateLog(f"Host '{userData.username}' created conference:\n{referalCheck} ")
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
        print(talkNames, talkSpeakers, talkTopics)
        # Creating a structure for created talks
        """A user is not obliged to create a talk at this stage...
        But should they choose to, a talk needs a name.
        """
        talksGenerated = []
        for i in range(len(talkNames)):
            talksGenerated.append([talkNames[i], talkSpeakers[i], talkTopics[i]])
            # Entities involved include:
            # Talks, Topics, Topicsconf
            
            speaker = Speakers(
                deleg=talkSpeakers[i]
            )
            db.session.add(speaker)
            db.session.commit()
            speakerId = speaker.id
            topics = talkTopics[i].split(', ')
            for word in topics:
                # Example: [topic1, topic2, topic3, topic4]
                topicWord = Topics(
                    topic=word
                )
                db.session.add(topicWord)
                db.session.commit()
                wordId = topicWord.id
                talks = Talks(
                    talkName=talkNames[i],
                    speakerId=speakerId,
                    confId=conferenceId,
                    topicId=wordId
                )
                db.session.add(talks)
                db.session.commit()
            
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

""" TODO 
    create: 
        - /find-conference, 
        - /edit-conference, 
        - /delete-conference, 
        - /register-conference, 
        - /preview-talks, 
        - /leave-conference, 
        - /delete-conference,
        - /change-passwd
"""