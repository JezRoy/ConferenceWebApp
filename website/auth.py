from flask import Blueprint

# Setting up a navigation blueprint for the flask application
auth = Blueprint('auth', __name__)

auth.route('/login')
def login():
    return "<p>login</p>"

auth.route('/logout')
def logout():
    return "<p>logout</p>"

auth.route('/sign-up')
def signUp():
    return "<p>sign up</p>"