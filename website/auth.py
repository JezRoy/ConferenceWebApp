from flask import Blueprint, render_template

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template("login.html")

@auth.route('/logout')
def logout():
    return "<p>logout</p>"

@auth.route('/sign-up')
def signUp():
    return render_template("signup.html")