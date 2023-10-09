from flask import redirect, render_template, request, session
from functools import wraps
import os
import sys
from datetime import datetime

def login_required(f):
    """
    Decorate routes to require login. Prevents unauthorised and non-contextual access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def updateLog(action):
    """
    Updates the server log with everything that happens in the app. 
    'action' is a string variable.
    """
    now = datetime.now()
    myFile = open("server.log", "a")
    contents = str(now)[:18]
    print(contents)
    myFile.close()
    return True