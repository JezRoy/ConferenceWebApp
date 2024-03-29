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
    print(message)
    with app.app_context():
        # Extract conference information
        conferences = db.session.query(Conferences).all()
        if conferences:
            # Check active jobs
            active = [job.id for job in parallelSys.get_jobs()]
            # Start a separate job for each conference
            for conferId in conferences:
                if f"conference_job_{conferId}" not in active:
                    UpdateLog(f"-----Running scheduler for conference {conferId.id}: {conferId.confName}...-----")
                    parallelSys.add_job(SCHEDULEConference, args=(app, conferId,), id=f"conference_job_{conferId}")
                else: 
                    UpdateLog(f"-----Scheduler is already dealing with {conferId.id}: {conferId.confName}!-----")
        else:
            UpdateLog("Scheduler cannot create any schedules, as the conference database is empty.")

def SCHEDULEConference(app, conferId):
    '''Each conference is computed one-at-a-time'''
    dataset = []
    with app.app_context():
        '''DATA EXTRACTION'''
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
        
        if talks != []:
            if DelegateInfo != []:
                if Deleg2Talks != []:
                    # Track breaks, lunches and talks for all conferences
                    
                    '''SCHEDULE CREATION Pt 1 - Timing Setup & Graph Theory'''
                    SCHEDULETimeData = { # THE ACTUAL SCHEDULE
                        # Each time slot is saved as a datetime structure
                    }
                    AvailableSlots = {
                        # Only the available slots to schedule will be given to the model
                    }

                    timeLength = ConferenceData["AverageTalkLength"] # In minutes
                    maxTalks = ConferenceData["IdealNoTalkPerSession"]
                    breakTime = 15 # Possibly an option to give users

                    del talks
                    del Deleg2Talks
                    del DelegateInfo

                    for i in range(ConferenceData["NumOfDays"]):
                        day = i + 1
                        SCHEDULETimeData[day] = {}
                        AvailableSlots[day] = {}
                        lunchMade = False

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
                                    SCHEDULETimeData[day][currentTime] = [] # Space for an actual talk to be scheduled here
                                    AvailableSlots[day][currentTime] = []
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
                    
                    '''SCHEDULE CREATION Pt 2 - IP Scheduler'''
                    # Create a LP problem
                    SchedulePt1model = pulp.LpProblem("ConferenceScheduling", pulp.LpMaximize)

                    days = AvailableSlots.keys()
                    # Decision Variables
                    x = pulp.LpVariable.dicts("TalkSlotsDayParallel", ((day, timeslot, talkId, parallel) 
                                for day in days
                                for timeslot in AvailableSlots[day] 
                                for talkId, _, _, _ in ConferenceData["TalkInfo"]
                                for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1)), 
                                cat='Binary')

                    # Objective function
                    SchedulePt1model += pulp.lpSum(x[(day, timeslot, delegateLikes[0], parallel)] * delegateLikes[2]
                                for delegateLikes in ConferenceData["DelegLikesTalks"]
                                for day in days
                                for timeslot in AvailableSlots[day]
                                for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1)
                                if delegateLikes[0] in [t[0] for t in ConferenceData["TalkInfo"]])

                    # Constraints
                    # Each talk can only be scheduled once
                    for thing in ConferenceData["TalkInfo"]:
                        talkId = thing[0]
                        SchedulePt1model += pulp.lpSum(x[(day, timeslot, talkId, parallel)]
                                    for day in days
                                    for timeslot in AvailableSlots[day]
                                    for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1)) == 1
                        
                    # Each talk must be scheduled at least once
                    for thing in ConferenceData["TalkInfo"]:
                        talkId = thing[0]
                        SchedulePt1model += pulp.lpSum(x[(day, timeslot, talkId, parallel)]
                                    for day in days
                                    for timeslot in AvailableSlots[day]
                                    for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1)) >= 1
                        
                    # Only one talk per timeslot and parallelslot
                    for timeslot in AvailableSlots[day]:
                        for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1):
                            talksInSlot = []
                            for thing in ConferenceData["TalkInfo"]:
                                talkId = thing[0]
                                if x[(day, timeslot, talkId, parallel)] == 1:
                                    talksInSlot.append(talkId)
                            SchedulePt1model += pulp.lpSum(x[(day, timeslot, talkId, parallel)]
                                                        for day in days
                                                        for talkId in talksInSlot) <= 1

                    # TODO
                    '''# Speaker constraint: A speaker can only give one talk at a time
                    for day in days:
                        for timeslot in SCHEDULETimeData[day]:
                            for parallel in range(1, ConferenceData["MaxNumParallelSessions"] + 1):
                                for thing in ConferenceData["TalkInfo"]:
                                    talkId = thing[0]
                                    speakerId = thing[1]
                                    if timeslot not in ['BREAK', 'LUNCH & REFRESHMENTS']:
                                        SchedulePt1model += pulp.lpSum(x[(day, timeslot, otherthing[0], parallel)]
                                                    for otherthing in ConferenceData["TalkInfo"] # Referring to talkId
                                                    if otherthing[0] != talkId and speakerId == otherthing[2][0]) <= 1'''
                    try:
                        # Solve the problem
                        SchedulePt1model.solve()
                        SchedulerOUT("Solution:")
                    except Exception as e:
                        SchedulerOUT(f"An error occured: {e} <<<<<<<<<<<<")
                    
                    # Print the solution
                    print(conferId.confName)
                    for var in SchedulePt1model.variables():
                        if var.varValue == 1:
                            print(var.name, "=", var.varValue)
                            SchedulerOUT(f"{var.name} = {var.varValue}")

                    SchedulerOUT("--------------------------------")

                    # TODO:
                    # Creating a conference using IP, and Graphs
                    
                    # Write schedule to a text file and save a trace to it

                    UpdateLog(f"New schedule created for {conferId.confName}:\n{SchedulePt1model.variables()}")
                    return True
                else:
                    UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegate preference data to use.")
            else:
                UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegates registered to it.")
        else:
            UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no talks created for it.")
        return False

def saveScheduleAsFile(fileName, schedule, conferenceId):
    file = open(f"schedules/{conferenceId}|{fileName}.txt","w")
    file.write(schedule)
    file.close()

def SchedulerOUT(thing):
    """
    Tracking scheduler output seprately from the rest of the app.
    """
    myFile = open("schedulerOutput.txt", "a", encoding='utf-8')
    contents = f"{thing}\n"
    myFile.write(contents)
    myFile.close()
    return True

   

if __name__ == '__main__':
    # Run app
    parallelSys.add_job(scheduleStuff, trigger='interval', minutes=0.5)
    parallelSys.start()
    app.run(debug=True)
    