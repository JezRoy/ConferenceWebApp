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
                            "DayStartTime": conferId.dayStart,
                            "DayEndTime": conferId.dayEnd,
                            "IdealNoTalkPerSession": conferId.talkPerSession,
                            "AverageTalkLength": conferId.talkLength,
                            "MaxNumParallelSessions": conferId.numSessions, # Number of parallel sessions
                            "TalkInfo": talks,
                            "DelegLikesTalks": Deleg2Talks,
                            "DelegateInfo": DelegateInfo
                }
                SchedulerOUT(ConferenceData)
                dataset.append(ConferenceData)

                '''jsonData = ConferenceData
                jsonData["DayStartTime"] = str(jsonData["DayStartTime"])
                jsonData["DayEndTime"] = str(jsonData["DayEndTime"])
                import json
                file_path = str(ConferenceData["ConfName"]) + ".json"
                with open(file_path, "w") as json_file:
                    json.dump(jsonData, json_file)'''

                # Track breaks, lunches and talks for all conferences
                
                
                '''SCHEDULE CREATION Pt 1 - Pseudo Random Schedule'''
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