from flask import Blueprint

# Setting up a navigation blueprint for the flask application
views = Blueprint('views', __name__)

@views.route('/') # The main page of the website
def home():
    return "<h1>Test</h1>"