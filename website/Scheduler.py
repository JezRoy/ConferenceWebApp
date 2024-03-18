"""SCHEDULER PROGRAM
- Create a base using IP / LP
- Optimise using Graph Theory

Update install.py with necessary modules to install.
"""

from flask import session
import networkx as nx
import pulp
from .functions import UpdateLog
from .models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, TopicTalks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules

def saveSchedulerAsFile(fileName, schedule, conferenceId):
    file = open(f"schedules/{conferenceId}|{fileName}.txt","w")
    file.write(schedule)
    file.close()
    return True

def SCHEDULEConference():
    # Create a LP problem
    conferenceIds = db.session.query(Conferences).all()
    print(conferenceIds)
    #model = pulp.LpProblem("DelegateSatisfaction", pulp.LpMaximize)
    
    # TODO:
    # Handle a empty database,
    # Handle an empty conference
    # Creating a conference using IP, and Graphs
    
    # Define decision variables
    #x = pulp.LpVariable("x", lowBound=0)
    #y = pulp.LpVariable("y", lowBound=0)


    #UpdateLog("New schedule created")
    pass