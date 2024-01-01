from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from .functions import UpdateLog
from .models import * 
from flask_login import login_user, login_required, logout_user, UserMixin, current_user

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, userinfo, user_id, type, is_active=True):
        self.id = user_id
        self.type = type
        self.username = userinfo[0]
        self.passwdHash = userinfo[1]
        self.email = userinfo[2]
    def is_authenticated(self):
        return True
    def is_active(self):
        return self.is_active
    def is_anonymous(self):
        return False
    def get_id(self):
        return str(self.id)

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
                sessionUsr = User(user, user[3], type)
                login_user(sessionUsr, remember=True) # Create session for user
                return redirect(url_for("views.home"))
            else:
                flash("Incorrect password, please try again.", category="error")
    return render_template("login.html")

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

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
                    flash("A user by this username already exists. Please use a different username, or log in.", category='error')
    return render_template("signup.html")