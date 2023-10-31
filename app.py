## When running flask, ENSURE YOU ARE DIRECTORY OF APPLICATION.PY
## Run using Cmd use the following commands:
## set FLASK_APP=application.py
## set FLASK_ENV=development
## python -m flask run
## Web App runs on http://127.0.0.1:5000/

import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from datetime import datetime
import sqlite3
from functions import *

# Decelerations
app = Flask(__name__)
now = datetime.now() # The current time of using the program.

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = b'P\x87\xfc\xa9\xe6qQ~)8\x90D\x11\n\xb9\xa1'
# Creating common shorcuts & global items between the front-end and back-end

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.afterRequest
def afterRequest(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET","POST"])
@RequireUser
def index():
    if request.method == 'POST':
        pass
    else:
        return render_template("index.html")

"""
if error:
    return StatusCode("Error message", 404)
"""