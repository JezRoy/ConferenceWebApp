from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime, date, time
from .models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from .functions import UpdateLog

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
    print("-------------\n", session, "\n-------------\n")
    # Find next upcoming conference from list of registered conferences
        # Query the ConfDeleg table to find the conferences a user is registered to
    userConferences = ConfDeleg.query.filter_by(delegId=userData.id).all()
        # Get the conference IDs the user is registered to
    conferenceIds = [conference.confId for conference in userConferences]
        # Query the Conferences table to get the details of the conferences
    conferencesUserRegister = Conferences.query.filter(Conferences.id.in_(conferenceIds)).all()
        # Get the current date and time
    rightNow = datetime.now()
        # Filter out conferences that have already started and store them in a list
    upcomingConferences = [
        conference for conference in conferencesUserRegister
        if conference.confStart >= rightNow.date()
    ]
        # Sort the upcoming_conferences based on their start date
    sortedConferences = sorted(upcomingConferences, key=lambda x: x.confStart)
    if sortedConferences:
        NextConf = sortedConferences[0]
        # Fetch additional information about the next upcoming conference from the database
        ConferenceData = Conferences.query.filter_by(id=NextConf.id).first()
    else:
        ConferenceData = None
    
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
        confLength = (endDay - startDay).days()
        dayStartDate = request.form.get("daystart")
        dayEndDate = request.form.get("dayend")
        startTime = datetime.strptime(dayStartDate, '%H:%M:%S').time()
        endTime = datetime.strptime(dayEndDate, '%H:%M:%S').time()
        dayLength = (endTime - startTime).days()
        numOfSessions = request.form.get("numSessions")
        if confLength > 0:
            if dayLength > 0:
                if numOfSessions > 0:
                    # Setup object for database
                    conference = Conferences(
                        confName = request.form.get("confName"),
                        confURL = request.form.get("confurl"),
                        paperFinalisationDate = request.form.get("paperfinal"),
                        delegSignUpDeadline = request.form.get("delegRegisterDeadline"),
                        confStart = startDay,
                        confEnd = endDay,
                        confLength = confLength,
                        dayStart = startTime,
                        dayEnd = endTime,
                        dayDuration = dayLength,
                        numSessions = numOfSessions
                    )
                    '''
                    # Add and commit to all relevant database tables
                    db.session.add(conference)
                    db.session.commit()
                    confNewId = conference.id
                    hosting = ConfHosts(
                        confId = confNewId,
                        hostId = userId
                    )
                    db.session.add(hosting)
                    db.session.commit()
                    '''
                    flash("Successfully created conference! You can edit / delete your main conference details later.", category="success")
                    return redirect(url_for("views.createConferenceStage2"))
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
                            stage=1)

@views.route('/create-conference-2', methods=['GET', 'POST'])
@login_required
def createConferenceStage2(): # For a host to a create a conference - part 1
    """ Setup conference talks """
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == 'POST':
        talkNames = request.form.getlist("talkname")
        talkSpeakers = request.form.getlist("talkspeaker")
        talkTopics = request.form.getlist("talktags")
        print(talkNames, talkSpeakers)
        
        flash("Talks added to conference successfully!", category="success")
        return redirect(url_for("views.home"))
    else:
        if session['type'] != "host":
            flash("Incorrect access rights: User is not a host.", category="error")
            return redirect(url_for("views.home"))
    return render_template("createconf.html",
                            user=current_user,
                            userData=userData,
                            stage=2)

""" TODO 
    create: 
        - /find-conference, 
        - /create-conference, 
        - /edit-conference, 
        - /delete-conference, 
        - /register-conference, 
        - /preview-talks, 
        - /leave-conference, 
        - /delete-conference,
        - /change-passwd
"""