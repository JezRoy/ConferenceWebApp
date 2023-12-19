from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functions import UpdateLog
from .models import *

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    return render_template("login.html")

@auth.route('/logout')
def logout():
    return "<p>logout</p>"

@auth.route('/sign-up', methods=['GET', 'POST'])
def signUp():
    if request.method == 'POST':
        # Get information
        validAdd = True
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirmation')
        email = request.form.get('email')
        dob = request.form.get('dob')
        try:
            usertype = request.form.get('usertype')
        except:
            usertype = None
        # Check validity
        if len(username) == 0:
            flash("Please enter a username.", category='error')
            return redirect(url_for("auth.signUp"))
        elif len(password) == 0:
            flash("Please enter a strong password.", category='error')
            return redirect(url_for("auth.signUp"))
        elif len(confirm) == 0:
            flash("Please re-enter your password.", category='error')
            return redirect(url_for("auth.signUp"))
        elif len(dob) == 0:
            flash("Please enter a date of birth.", category='error')
            return redirect(url_for("auth.signUp"))
        elif usertype != 'delegate' or usertype != 'host':
            flash("Please choose a user-type.", category='error')
            return redirect(url_for("auth.signUp"))
        else:
            passwdHash = generate_password_hash(password, method="sha256")
            if check_password_hash(passwdHash, confirm) == False:
                flash("Please enter matching passwords.", category="error")
                return redirect(url_for("auth.signUp"))
            else:
                if email != "" or "@" not in email:
                    emailAddr = "None"
                else:
                    emailAddr = email
                # Add user to database.
                conn = sqlite3.connect('website/ConferenceWebApp.db')
                cursor = conn.cursor()
                if usertype == 'delegate': 
                    addDelegate(cursor, username, passwdHash, dob, emailAddr)
                else:
                    addHost(cursor, username, passwdHash, dob, emailAddr)
                flash("Successfully signed up!", category='success')
                UpdateLog(f"New User: {username} added to the system.")
                return redirect(url_for("views.home"))
    else:
        return render_template("signup.html")