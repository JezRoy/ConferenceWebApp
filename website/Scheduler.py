"""SCHEDULER PROGRAM
- Create a base using IP / LP
- Optimise using Graph Theory
"""
from . import db

def saveSchedulerAsFile(fileName, schedule, conferenceId):
    file = open(f"schedules/{conferenceId}|{fileName}.txt","w")
    file.write(schedule)
    file.close()
    return True

def SCHEDULEConference():
    pass