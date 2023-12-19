from flask import Blueprint, render_template

# Setting up a navigation blueprint for the flask application
views = Blueprint('views', __name__)

@views.route('/') # The main page of the website
def home():
    return render_template("index.html")