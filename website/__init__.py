from flask import Flask
from models import *

def CreateApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'irgjghrebhuirbhgjenvbeirghiubwegsdvibug ewbuiwerjkgrhweibhg ewhi ewb hjewb ihj b4hjweb gin243wb ihjeb j1'
    conn = sqlite3.connect('website/ConferenceWebApp.db')
    cursor = conn.cursor()
    initialise(cursor)
    
    from .routesAndviews import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    return app