"""SCHEDULER PROGRAM
- Create a base using IP / LP
- Optimise using Graph Theory

Update install.py with necessary modules to install.
"""

"""During Development
Set the right python interpreter using:
- cmd+shift+p
- 'python select interpreter'
- python3.8.8 (NOT conda)
"""

from flask import session, current_app
import networkx as nx
import pulp
from website import CreateApp
# This web app has been created with help from
# https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim
from website.functions import UpdateLog
from website.models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, TopicTalks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from website.__init__ import parallelSys

app = CreateApp()

# Running the scheduler
def scheduleStuff():
    #with app.app_context():
    message = "Scheduler is still running... Designed to run once every 30 mins for every conference..."
    SchedulerOUT(message)
    SchedulerOUT(app)
    SCHEDULEConference(app)

def SCHEDULEConference(app):
    # Create a LP problem
    with app.app_context():
        conferenceIds = db.session.query(Conferences).all()
        SchedulerOUT(conferenceIds)
        for confId in conferenceIds:
            SchedulerOUT(confId.confName, confId.confURL, confId.confLength)
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

def saveScheduleAsFile(fileName, schedule, conferenceId):
    file = open(f"schedules/{conferenceId}|{fileName}.txt","w")
    file.write(schedule)
    file.close()

def SchedulerOUT(thing):
    """
    Tracking scheduler output seprately from the rest of the app.
    """
    myFile = open("schedulerOutput.txt", "a")
    contents = f"{thing}\n"
    myFile.write(contents)
    myFile.close()
    return True

if __name__ == '__main__':
    # Run app
    parallelSys.add_job(scheduleStuff, trigger='interval', minutes=0.5)
    parallelSys.start()
    app.run(debug=True)