from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from .functions import UpdateLog
from .models import db, User
from flask_login import login_user, login_required, logout_user, UserMixin, current_user

"""DATETIME NOTES:
- date(2023, 12, 31) = 31st December 2023
- time(9, 0, 0) = 9:00am
"""

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.passwordHash, password):
                flash("Logged in successfully!", category="success")
                login_user(user, remember=True)
                return redirect(url_for("views.home"))   
            else:
                flash("Incorrect password, please try again.", category="error")
    return render_template("login.html", user=current_user)

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
        firstName = request.form.get('first_name')
        lastName = request.form.get('last_name')
        password = request.form.get('password')
        confirm = request.form.get('confirmation')
        email = request.form.get('email')
        dob = request.form.get('dob')
        # Check validity
        if len(username) == 0 or len(firstName) == 0:
            flash("Please enter a username and a first name.", category='error')
        else:
            try:
                usertype = request.form.get('usertype')
            except:
                usertype = None
            
            user = User.query.filter_by(username=username).first()
            if user:
                flash("A user by this username already exists. Please use a different username, or log in.", category='error')
            else:
                if len(password) == 0:
                    flash("Please enter a strong password.", category='error')
                elif len(confirm) == 0:
                    flash("Please re-enter your password.", category='error')
                elif len(dob) == 0:
                    flash("Please enter a date of birth.", category='error')
                elif len(email) == 0 or "@" not in email:
                    flash("Please enter a valid email.", category='error')
                elif usertype != 'delegate' and usertype != 'host':
                    flash("Please choose a user-type.", category='error')
                else:
                    passwdHash = generate_password_hash(password)
                    if check_password_hash(passwdHash, confirm) == False:
                        flash("Please enter matching passwords.", category="error")
                    else:
                        if "@" not in email:
                            emailAddr = "None"
                        else:
                            emailAddr = email
                        if dob != '' and dob != 'yyy-mm-dd':
                            dateObj = datetime.strptime(dob, '%Y-%m-%d').date()
                            print(dateObj.year, dateObj.month, dateObj.day)
                            #dateItem = datetime.date(dateObj.year, dateObj.month, dateObj.day)
                        else:
                            dateObj = None
                        newUser = User(username=username, passwordHash=passwdHash,email=emailAddr, firstName=firstName, lastName=lastName, dob=dateObj, type=usertype)
                        db.session.add(newUser)
                        db.session.commit()
                        flash("Successfully signed up!", category='success')
                        UpdateLog(f"New User: {username} added to the system.")
                        return redirect(url_for("views.home"))
    return render_template("signup.html", user=current_user)