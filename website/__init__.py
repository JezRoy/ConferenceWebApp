from flask import Flask, flash
from .models import *
from flask_login import LoginManager, UserMixin

"""CREDITS:
This web app functionality was created with help from a tutorial on YouTube
created by creator 'Tech with Tim'. Found at:
- https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim
- Accessed December 20th 2023.
"""

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

def CreateApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'irgjghrebhuirbhgjenvbeirghiubwegsdvibug ewbuiwerjkgrhweibhg ewhi ewb hjewb ihj b4hjweb gin243wb ihjeb j1'
    conn = sqlite3.connect('website/ConferenceWebApp.db')
    cursor = conn.cursor()
    initialise(cursor)
    
    from .routesAndviews import views
    from .auth import auth, User
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(id):
        # Now established that any username will ever exist in both host and delegate database tables
        # Try looking in delegate table
        type = ""
        finder = findDelegate(cursor, id=id)
        if finder[0] == True:
            userdata = finder[1]
            type = "delegate"
        else:
            # Try looking in host table if not in delegate
            finder = findHost(cursor, id=id)
            if finder[0] == True:
                userdata = finder[1]
                type = "host"
            else:
                flash("Session could not be created for the user.")
                return None
        user = User(userdata, userdata[3], type)
        return user
    
    return app