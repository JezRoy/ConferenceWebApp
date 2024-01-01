from flask import Blueprint, render_template, request, flash
from . import cursor, conn
from flask_login import login_required, current_user

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
    return render_template("index.html")

""" TODO 
    create: 
        - /find-conference, 
        - /create-conf, 
        - /edit-conf, 
        - /delete-conf, 
        - /register-conf, 
        - /preview-talk, 
        - /leave-conf, 
        - /delete-conf,
        - /change-passwd
    finish index.html as a profile page 
"""