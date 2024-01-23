from flask import Flask, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from datetime import timedelta

"""CREDITS:
This web app functionality was created with help from a tutorial on YouTube
created by creator 'Tech with Tim'. Found at:
- https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim
- Accessed December 20th 2023.
"""

db = SQLAlchemy()
DB_NAME = "ConfWebApp.db"

def CreateApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'irgjghrebhuirbhgjenvbeirghiubwegsdvibug ewbuiwerjkgrhweibhg ewhi ewb hjewb ihj b4hjweb gin243wb ihjeb j1'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Example: 1 hour
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Set session lifetime to 1 day
    
    db.init_app(app)
    db.app = app
    from .routesAndviews import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    from .models import User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
    from .functions import UpdateLog
    
    with app.app_context():
        db.create_all()
    
    UpdateLog("Created Database.")
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(id):
        idFound = User.query.get(int(id))
        return idFound
    
    return app