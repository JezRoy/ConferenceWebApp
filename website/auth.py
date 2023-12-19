from flask import Blueprint, render_template, request, flash

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
        elif len(password) == 0:
            flash("Please enter a strong password.", category='error')
        elif len(confirm) == 0:
            flash("Please re-enter your password.", category='error')
        elif len(dob) == 0:
            flash("Please enter a date of birth.", category='error')
        elif usertype != 'delegate' or usertype != 'host':
            flash("Please choose a user-type.", category='error')
        else:
            flash("Successfully signed up!", category='success')
            # Add user to database.
    else:
        return render_template("signup.html")