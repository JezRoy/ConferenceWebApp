from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from .functions import UpdateLog
from .models import *
#from . import cursor, conn

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        type = "host"
        conn = sqlite3.connect('website/ConferenceWebApp.db')
        cursor = conn.cursor()
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
        cursor.close()
        conn.close()
        # Authentication check
        if type == "USER NOT FOUND!":
            flash("User does not exist, please use a registered username.", category="error")
        else:
            if type == "host":
                passwdStore = user[1]
            else:
                passwdStore = user[1]
            if check_password_hash(passwdStore, password):
                flash("Logged in successfully!", category="success")
                return redirect(url_for("views.home"))
            else:
                flash("Incorrect password, please try again.", category="error")
    return render_template("login.html")

@auth.route('/logout')
def logout():
    return "<p>logout</p>"

@auth.route('/sign-up', methods=['GET', 'POST'])
def signUp():
    if request.method == 'POST':
        # Get information
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirmation')
        email = request.form.get('email')
        dob = request.form.get('dob')
        type = "found"
        # Check validity
        if len(username) == 0:
            flash("Please enter a username.", category='error')
        else:
            try:
                usertype = request.form.get('usertype')
            except:
                usertype = None
                
            if usertype != 'delegate' and usertype != 'host':
                    flash("Please choose a user-type.", category='error')
            else:
                conn = sqlite3.connect('website/ConferenceWebApp.db')
                cursor = conn.cursor()
                # Check the user does not already exists
                if usertype == 'host':
                    # If the pre-existing user is a host
                    finder = findHost(cursor, username)
                else: # If the pre-existing user is a delegate
                    # Basic search used here - Array type returned
                    finder = findDelegate(cursor, username)
                if finder[0] == True:
                    user = finder[1]
                else: # User is not a delegate
                    type = "USER NOT FOUND!"
                if type == "USER NOT FOUND!":
                    if len(password) == 0:
                        flash("Please enter a strong password.", category='error')
                    elif len(confirm) == 0:
                        flash("Please re-enter your password.", category='error')
                    elif len(dob) == 0:
                        flash("Please enter a date of birth.", category='error')
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
                            try:
                                conn.commit()
                                cursor.close()
                                conn.close()
                                flash("Successfully signed up!", category='success')
                                UpdateLog(f"New User: {username} added to the system.")
                                return redirect(url_for("views.home"))
                            except Exception as e:
                                flash(f"Error registering account: {e}", category='error')
                else:
                    flash("This user already exists. Please use a different username, or log in.", category='error')
    return render_template("signup.html")