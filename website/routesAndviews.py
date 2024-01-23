from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime, date, time
from .models import User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
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

@views.route('/create-conference', methods=['GET', 'POST'])
@login_required
def createConference(): # For a host to a create a conference
    # Find logged in user data
    userId = current_user._get_current_object().id
    userData = User.query.get(userId)
    if request.method == 'POST':
        session['conference_created_id'] = 0
        pass
    else:
        if session['type'] != "host":
            flash("Incorrect access rights: User is not a host.", category="error")
            return redirect(url_for("views.home"))
        else:
            return render_template("createconf.html",
                                   user=current_user,
                                   userData=userData,
                                   stage=1)

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
    finish index.html as a profile page 
"""