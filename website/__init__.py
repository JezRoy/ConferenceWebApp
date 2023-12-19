from flask import Flask

# Arguments to consider when rendering a template
"""
DEFAULTS:
- When using flash() to flash alerts and warning there are 3 string categories:
    - error
    - info
    - warning
- {{ session.username }} defines whether a user is signed in.
- {{ conferenceSigned }} determines if a user is signed up to a conference.
    if so, then present the option to see that conference.
    - May require a conference search up beforehand to also pass in the URL
    to a conference as a link in the navbar:
        - referred to with {{ conferenceURL }}.

"""

def CreateApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'irgjghrebhuirbhgjenvbeirghiubwegsdvibug ewbuiwerjkgrhweibhg ewhi ewb hjewb ihj b4hjweb gin243wb ihjeb j1'
    
    from .routesAndviews import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    return app