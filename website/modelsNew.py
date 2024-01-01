from . import db
from flask_login import UserMixin

limit = 150 # Max character storage
"""NOTE!!
db.Date stored as '2023-12-31'
db.Time stored as '09:00:00'
"""

class User(db.Model, UserMixin): # Flash SQLAlchemy database
    # Holds all the user information for the system
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(limit), unique=True)
    passwordHash = db.Column(db.String(limit))
    email = db.Column(db.String(limit), unique=True)
    firstName = db.Column(db.String(limit))
    lastName = db.Column(db.String(limit))
    dob = db.Column(db.Date)
    type = db.Column(db.String(8)) # Either a host XOR a delegate
    topics = db.relationship('DelTopics') # A relationship to recall all the topics a delegate is interested in
    hostings = db.relationship('ConfHosts') # A relationship to recall all the conferences a host creates 
    # Will be blank for HOSTS

class ConfDeleg(db.Model): # When users sign up to a conference
    confID = db.Column(db.Integer, db.ForeignKey('conference.id'), primary_key=True)
    delegID = db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key to user table - given they are a DELEGATE
    
class Conferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    confName = db.Column(db.String(limit))
    confURL = db.Column(db.String(limit * 2), unique=True)
    paperSubDeadline = db.Column(db.Date) # The following are measured as per date times and days
    delegSignUpDeadline = db.Column(db.Date)
    confStart = db.Column(db.Date)
    confEnd = db.Column(db.Date)
    confLength = db.Column(db.Integer) # To be calculated by the software
    dayStart = db.Column(db.Time) # What time each day starts
    dayEnd = db.Column(db.Time)
    dayDuration = db.Column(db.Integer) # Number of hours - To be calculated by the software
    delegates = db.relationship('ConfDeleg')
    
class ConfDayTimings(db.Model):
    """Note:
    - Stores talks, breaks AND lunches for all conferences
    - dayNum is relative to dayDuration
    """
    # Accomodate for this in the 'Create Conference' page
    timingId = db.Column(db.Integer, primary_key=True)
    talkId = db.Column(db.Integer, db.ForeignKey('talks.id')) # Foreign key from talk table
    slotStart = db.Column(db.Time) # In hundred-hours like '0900' or '1734'
    slotEnd = db.Column(db.Time)
    dayNum = db.Column(db.Integer) # Relative to the dayDuration column in Conferences table
    description = db.Column(db.String(limit * 2))
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table

class ConfHosts(db.Model):
    """NOTE:
    - Hosts create conferences first before this table is accessed.
    """
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    hostId = db.Column(db.Integer, db.ForeignKey('users.id')) # Foreign key from user table - given they are a HOST

class Talks(db.Model):
    """Note:
    This does not account for breaks, and lunches
    """
    id = db.Column(db.Integer, primary_key=True)
    talkName = db.Column(db.String(limit))
    speakerId = db.Column(db.Integer, db.ForeignKey('speakers.id')) # Foreign key from Speakers table
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    topicId = db.Column(db.Integer, db.ForeignKey('topics.id')) # Foreign key from Topic table

class Speakers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delegId = db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key from the user table - given they are a DELEGATE
    talks = db.relationship('Talks')
    # Hosts are not speakers, since they do not participate in the conference.
    # Delegates will want to participate in the conference but still be speakers.

class Topics(db.Model):
    """Note:
    A single topic can be associated with multiple talks 
    from multiple conferences"""
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(limit))
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table

class DelTopics(db.Model):
    delegId = db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key from user table - given they are a 'delegate'
    topicId = db.Column(db.Integer, db.ForeignKey('topics.id')) # Foreign key from Topic table