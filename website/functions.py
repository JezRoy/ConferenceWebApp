from flask import flash, redirect, render_template, request, session
from functools import wraps
from datetime import datetime

def RequireUser(f, message=""):
    """
    Decorate routes to require login. Prevents unauthorised and non-contextual access.
    """
    @wraps(f)
    def decorate(*args, **kwargs):
        if session.get("username") is None:
            # Stops a non-logged-in user from accessing parts of the website and redirects them.
            if message != "":
                flash(message, "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorate

def UpdateLog(action):
    """
    Updates the server log with everything that happens in the app. 
    'action' is a string variable.
    """
    now = datetime.now()
    myFile = open("server.log", "a", encoding="utf-8")
    contents = f"{str(now)[:19]}: {action}\n"
    myFile.write(contents)
    myFile.close()
    return True

def StatusCode(message, code=400):
    """
    For error codes and maintaining site consistency even when things go wrong.
    'message' is a string.
    'code' refers to context of message.
    """
    def escape(s):
        """
        Escape special characters.
        Original material found for this found:
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("error.html", top=code, bottom=escape(message)), code
    
UpdateLog("Server Log initialisation/update")