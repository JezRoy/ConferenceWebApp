from . import db
from flask_login import UserMixin

limit = 150 # Max character storage
"""NOTE!!
db.Date stored as '2023-12-31'
db.Time stored as '09:00:00'
"""

class User(db.Model, UserMixin): # Flash SQLAlchemy database
    # Holds all the user information for the system
    id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column(db.String(limit), unique=True)
    passwordHash = db.Column(db.String(limit))
    email = db.Column(db.String(limit))
    firstName = db.Column(db.String(limit))
    lastName = db.Column(db.String(limit), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    type = db.Column(db.String(8)) # Either a host XOR a delegate
    # Will be blank for HOSTS
    def __init__(self, username, passwordHash, email, firstName, lastName, dob, type):
        self.username = username
        self.passwordHash = passwordHash
        self.email = email
        self.firstName = firstName
        self.lastName = lastName
        self.dob = dob
        self.type = type

class ConfDeleg(db.Model): # When users sign up to a conference
    id = db.Column(db.Integer, primary_key=True)
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    delegId= db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key to user table - given they are a DELEGATE
    def __init__(self, confId, delegId):
        self.confId = confId
        self.delegId = delegId
           
class Conferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    confName = db.Column(db.String(limit))
    confURL = db.Column(db.String(limit * 2))
    paperFinalisationDate = db.Column(db.Date) # The following are measured as per date times and days
    delegSignUpDeadline = db.Column(db.Date)
    confStart = db.Column(db.Date)
    confEnd = db.Column(db.Date)
    confLength = db.Column(db.Integer) # To be calculated by the software
    dayStart = db.Column(db.Time) # What time each day starts
    dayEnd = db.Column(db.Time)
    dayDuration = db.Column(db.Integer) # Number of hours - To be calculated by the software
    talkPerSession = db.Column(db.Integer)
    talkLength = db.Column(db.Integer) # Average talk length - in minutes
    numSessions = db.Column(db.Integer) # Number of parallel sessions during each day - though the system can override this if it finds a better solution
    def __init__(self, confName, confURL, paperFinalisationDate, delegSignUpDeadline, confStart, confEnd, confLength, dayStart, dayEnd, dayDuration, talkPerSession, talkLength, numSessions):
        self.confName = confName
        self.confURL = confURL
        self.paperFinalisationDate = paperFinalisationDate
        self.delegSignUpDeadline = delegSignUpDeadline
        self.confStart = confStart
        self.confEnd = confEnd
        self.confLength = confLength
        self.dayStart = dayStart
        self.dayEnd = dayEnd
        self.dayDuration = dayDuration
        self.talkPerSession = talkPerSession
        self.talkLength = talkLength
        self.numSessions = numSessions
    
class ConfDaySessions(db.Model):
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
    def __init__(self, timingId, talkId, slotStart, slotEnd, dayNum, description, confId):
        self.timingId = timingId
        self.talkId = talkId
        self.slotStart = slotStart
        self.slotEnd = slotEnd
        self.dayNum = dayNum
        self.description = description
        self.confId = confId

class ConfHosts(db.Model):
    """NOTE:
    - Hosts create conferences first before this table is accessed.
    """
    id = db.Column(db.Integer, primary_key=True)
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    hostId = db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key from user table - given they are a HOST
    def __init__(self, confId, hostId):
        self.confId = confId
        self.hostId = hostId

class Talks(db.Model):
    """Note:
    This does not account for breaks, and lunches
    """
    id = db.Column(db.Integer, primary_key=True)
    talkName = db.Column(db.String(limit))
    speakerId = db.Column(db.Integer, db.ForeignKey('speakers.id')) # Foreign key from Speakers table
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    def __init__(self, talkName, speakerId, confId):
        self.talkName = talkName
        self.speakerId = speakerId
        self.confId = confId

class DelegTalks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delegId = db.Column(db.Integer, db.ForeignKey('user.id')) # Given they are a DELEGATE
    talkId = db.Column(db.Integer, db.ForeignKey('talks.id'))
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    prefLvl = db.Column(db.Integer) # Preference level of going to a talk
    def __init__(self, delegId, talkId, confId, prefLvl):
        self.delegId = delegId
        self.talkId = talkId
        self.confId = confId
        self.prefLvl = prefLvl

class Speakers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deleg = db.Column(db.String(limit)) # Foreign key from the user table - given they are a DELEGATE
    # Hosts are not speakers, since they do not participate in the conference.
    # Delegates will want to participate in the conference but still be speakers.
    def __init__(self, deleg):
        self.deleg = deleg

class Topics(db.Model):
    """Note:
    A single topic can be associated with multiple talks 
    from multiple conferences"""
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(limit)) # Topic name for each id
    def __init__(self, topic):
        self.topic = topic

class TopicTalks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    talkId = db.Column(db.Integer, db.ForeignKey('talks.id'))
    topicId = db.Column(db.Integer, db.ForeignKey('topics.id')) # Foreign key from Topic table
    def __init__(self, talkId, topicId):
        self.talkId = talkId
        self.topicId = topicId
    
class Topicsconf(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Uniquely identify each conference topic (even if some share the same name)
    topicId = db.Column(db.Integer, db.ForeignKey('topics.id')) # Foreign key from topic table
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    def __init__(self, topicId, confId):
        self.topicId = topicId
        self.confId = confId

class DelTopics(db.Model): # Only recorded for topics in talks that have a preference of 6/10 or higher.
    id = db.Column(db.Integer, primary_key=True)
    delegId = db.Column(db.Integer, db.ForeignKey('user.id')) # Foreign key from user table - given they are a 'delegate'
    topicId = db.Column(db.Integer, db.ForeignKey('topicsconf.id')) # Foreign key from Topic table
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    def __init__(self, delegId, topicId, confId):
        self.delegId = delegId
        self.topicId = topicId
        self.confId = confId

class Schedules(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    confId = db.Column(db.Integer, db.ForeignKey('conferences.id')) # Foreign key from Conferences table
    file = db.Column(db.String(limit), unique=True)
    dayOfConf = db.Column(db.Integer) # Should a conference have multiple days, there will be multiple schedules for each day of the conference
    score = db.Column(db.Integer) # Delegate satisfaction 
    paraSesh = db.Column(db.Integer) # Number of parallel sessions during each day in the conference
    def __init__(self, confId, file, dayOfConf, score, paraSesh):
        self.confId = confId
        self.file = file
        self.dayOfConf = dayOfConf
        self.score = score
        self.paraSesh = paraSesh