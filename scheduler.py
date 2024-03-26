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
from datetime import datetime, timedelta, time
import pulp
import random
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
    SCHEDULEConference(app)

def SCHEDULEConference(app):
    '''Each conference is computed one-at-a-time'''
    dataset = []
    with app.app_context():
        '''DATA EXTRACTION'''
        # Extract conference information
        conferences = db.session.query(Conferences).all()
        if conferences:
            for conferId in conferences:
                ConferenceData = []
                # Extract host info
                hoster = ConfHosts.query.filter_by(confId=conferId.id).all()
                hostId = hoster[0].hostId
                host = User.query.filter_by(id=hostId).all()[0]

                # Extract Delegate information
                DelegateInfo = []
                DelegatesFound = ConfDeleg.query.filter_by(confId=conferId.id).all()
                for thing in DelegatesFound:
                    person = User.query.filter_by(id=thing.delegId).all()[0]
                    DelegateInfo.append([person.id, person.username])

                # Extract talk information
                talksFound = Talks.query.filter_by(confId=conferId.id).all()
                talks = []
                Deleg2Talks = []
                for talk in talksFound:
                    data = [talk.id, talk.talkName]
                    speaker = Speakers.query.filter_by(id=talk.speakerId).all()[0]
                    data.append([speaker.id, speaker.deleg])

                    # Extract topic information
                    topics = []
                    topicsAsso = TopicTalks.query.filter_by(talkId=talk.id).all()
                    # Relate topic to talks
                    for topicId in topicsAsso:
                        tag = Topics.query.filter_by(id=topicId.id).first().topic
                        topics.append([topicId.topicId, tag])
                    data.append(topics)
                    talks.append(data)
                
                    # Relate delegates to talks
                    for item in DelegateInfo:
                        queryMade = DelegTalks.query.filter(DelegTalks.delegId == item[0]).filter(DelegTalks.confId == conferId.id).filter(DelegTalks.talkId == talk.id).all()
                        for queried in queryMade:
                            if [queried.talkId, queried.delegId, queried.prefLvl] not in Deleg2Talks:
                                Deleg2Talks.append([queried.talkId, queried.delegId, queried.prefLvl])

                # Relate topics to delegates
                SchedulerOUT("--------------------------------")
                ConferenceData = {
                            "ConfName": conferId.confName, 
                            "Host": host.username, 
                            "NumOfDays": conferId.confLength,
                            "StartDate": conferId.confStart,
                            "EndDate": conferId.confEnd,
                            "DayStartTime": conferId.dayStart,
                            "DayEndTime": conferId.dayEnd,
                            "IdealNoTalkPerSession": conferId.talkPerSession,
                            "AverageTalkLength": conferId.talkLength, # In minutes
                            "MaxNumParallelSessions": conferId.numSessions, # Number of parallel sessions
                            "TalkInfo": talks,
                            "DelegLikesTalks": Deleg2Talks,
                            "DelegateInfo": DelegateInfo
                }
                SchedulerOUT(ConferenceData)
                dataset.append(ConferenceData)

                # Track breaks, lunches and talks for all conferences
                
                '''SCHEDULE CREATION Pt 1 - Timing Setup & Graph Theory'''
                SCHEDULETimeData = { # THE ACTUAL SCHEDULE
                    # Each time slot is saved as a datetime structure
                }
                
                timeLength = ConferenceData["AverageTalkLength"] # In minutes
                maxTalks = ConferenceData["IdealNoTalkPerSession"]
                breakTime = 15 # Possibly an option to give users

                for i in range(ConferenceData["NumOfDays"]):
                    day = i + 1
                    SCHEDULETimeData[day] = {}
                    lunchMade = False
                    
                    #dayInQ = ConferenceData["StartDate"] + timedelta(days=i)

                    # Initialize the current datetime
                    currentTime = ConferenceData["DayStartTime"] # 'datetime.time' object
                    sessionCount = 0 # TODO ACCOUNT FOR LUNCH
    
                    # Iterate over the datetime frames with the fixed interval to create a set of slots
                    while currentTime <= ConferenceData["DayEndTime"]:
                        # Convert currentTime to seconds since midnight
                        totalS = currentTime.hour * 3600 + currentTime.minute * 60 + currentTime.second

                        if currentTime.hour >= 12 and lunchMade == False: # Time for lunch - 60 minutes
                            SCHEDULETimeData[day][currentTime] = "LUNCH & REFRESHMENTS"
                            totalS += 3600
                            sessionCount = 0
                            lunchMade = True
                        else:
                            if sessionCount < maxTalks:
                                SCHEDULETimeData[day][currentTime] = None # Space for an actual talk to be scheduled here
                                sessionCount += 1

                                # Add or subtract the specified hours, minutes, and seconds
                                minutes = timeLength # If timeLength is less than 60 minutes
                                hours = 0
                                if timeLength >= 60:
                                    hours = timeLength // 60
                                    minutes = timeLength - (hours * 60)
                                totalS += hours * 3600 + minutes * 60
                            else:
                                SCHEDULETimeData[day][currentTime] = "BREAK" # An extended break is placed after a session
                                sessionCount = 0
                                totalS += breakTime * 60

                        # Ensure the result is within a 24-hour period
                        totalS %= 24 * 3600
                        # Convert the total seconds back to a time object AND increment currentTime by the interval
                        currentTime = time(totalS // 3600, (totalS % 3600) // 60, totalS % 60)

                #print(SCHEDULETimeData)

                with open(f"scheduleTIME_{conferId.confName}.txt", "w") as file:
                    file.write(f"{ConferenceData}\n")
                    # Iterate over dictionary items
                    things = SCHEDULETimeData.items()
                    for key1, value1 in things:
                        # Write each key-value pair to a new line
                        file.write(f"{key1}:\n")
                        for key2, value2 in value1.items():
                            file.write(f"{key2}: {value2}\n")
                
                '''SCHEDULE CREATION Pt 2 - IP Scheduler
                # Create a LP problem
                SchedulePt1model = pulp.LpProblem("PseudoRandomSchedule", pulp.LpMaximize)

                #### ScheduleVars = pulp.LpVariable.dicts("Schedule", ((s, t) for s in range(ConferenceData[8]) for t in range(ConferenceData[6])), 0, 1, pulp.LpBinary)

                # Decision variables
                ScheduleVars = {}
                for day in range(ConferenceData["NumOfDays"]):
                    for session in range(ConferenceData["MaxNumParallelSessions"]):
                        for talkId, _, _ in ConferenceData["TalkInfo"]:
                            ScheduleVars[(day, session, talkId)] = pulp.LpVariable(
                                f"Talk_{day}_{session}_{talkId}", 0, 1, pulp.LpBinary)

                # Associating talk data with the decision variables in the IP
                TalksToModel = {}

                numOfTalks = len(talks)
                for i in range(numOfTalks):
                    TalksToModel[i+1] = talks[i]
                SchedulerOUT(TalksToModel)
                SchedulerOUT("--------------------------------")


                # Constraints
                # Each talk is scheduled only once
                for talkId, _, _ in ConferenceData["TalkInfo"]:
                    SchedulePt1model += pulp.lpSum(ScheduleVars[(day, session, talkId)] 
                                        for day in range(ConferenceData["NumOfDays"]) 
                                        for session in range(ConferenceData["MaxNumParallelSessions"])) <= 1
                
                # One talk per time slot in a session
                for day in range(ConferenceData["NumOfDays"]):
                    for session in range(ConferenceData["MaxNumParallelSessions"]):
                        SchedulePt1model += pulp.lpSum(ScheduleVars[(day, session, talkId)] 
                                            for talkId, _, _ in ConferenceData["TalkInfo"]) <= 1
                
                '''
                SchedulerOUT("--------------------------------")
                # TODO:
                # Handle an empty conference
                # Creating a conference using IP, and Graphs
            
                # Define decision variables
                #x = pulp.LpVariable("x", lowBound=0)
                #y = pulp.LpVariable("y", lowBound=0)
                
                # Write schedule to a text file and save a trace to it

                #UpdateLog("New schedule created")
                pass
        else:
            UpdateLog("Scheduler cannot create any schedules, as the conference database is empty.")
            return False

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