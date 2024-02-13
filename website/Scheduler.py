"""SCHEDULER PROGRAM
- Create a base using IP / LP
- Optimise using Graph Theory

Update install.py with necessary modules to install.
"""
from . import db
from .functions import UpdateLog

def saveSchedulerAsFile(fileName, schedule, conferenceId):
    file = open(f"schedules/{conferenceId}|{fileName}.txt","w")
    file.write(schedule)
    file.close()
    return True

def SCHEDULEConference():
    # UpdateLog("New schedule created")
    pass