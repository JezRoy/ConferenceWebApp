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
from networkx.algorithms.coloring import greedy_color
from datetime import datetime, timedelta, time
import pulp
import random
from website import CreateApp
# This web app has been created with help from
# https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim
from website.functions import UpdateLog
from website.models import db, User, ConfDeleg, Conferences, ConfDaySessions, ConfHosts, Talks, TopicTalks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from website.__init__ import parallelSys
import os
os.makedirs("schedules", exist_ok=True)

app = CreateApp()

# Running the scheduler
def scheduleStuff():
    #with app.app_context():
    message = "Scheduler is still running... Designed to run once every 30 seconds for every conference..."
    SchedulerOUT(message)
    print(message)
    with app.app_context():
        # Extract conference information
        conferences = db.session.query(Conferences).all()
        if conferences:
            # Check active jobs
            active = [job.name for job in parallelSys.get_jobs()]
            # Start a separate job for each conference
            for conferId in conferences:
                jobName = f"conference_job_{conferId}"
                if jobName not in active:
                    UpdateLog(f"-----Running scheduler for conference {conferId.confName}: {jobName}...-----")
                    parallelSys.add_job(SCHEDULEConference, args=(app, conferId,), name=jobName)
                else: 
                    UpdateLog(f"-----Scheduler is already dealing with {conferId.confName}: {jobName}!-----")
        else:
            UpdateLog("Scheduler cannot create any schedules, as the conference database is empty.")

def SCHEDULEConference(app, conferId):
    '''Each conference is computed one-at-a-time'''
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
                        # Track the preference a talk, by a certain delegate, and the score they gave it
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

        # Function to find alternative slot in case of conflict
        def findAltSlot(AvailableSlots, day):
            for slot, colors in AvailableSlots[day].items():
                if len(colors) < ConferenceData["MaxNumParallelSessions"]:  # Adjust as per maximum parallel sessions allowed
                    return slot
            return None
        
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
                                    for i in range(ConferenceData["MaxNumParallelSessions"]):
                                        SCHEDULETimeData[day][currentTime].append("None")
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
                    try:
                        # Solve the problem
                        SchedulePt1model.solve()
                    except Exception as e:
                        SchedulerOUT(f"An error occured: {e} <<<<<<<<<<<<")
                    
                    # Print the solution
                    solution = []
                    for var in SchedulePt1model.variables():
                        if var.varValue == 1:
                            solution.append(var.name)
                    
                    '''SCHEDULE CREATION Pt 3 - Graph Theory'''
                    # First some reformatting
                    for i in range(len(solution)):
                        # Some reformatting of the solution
                        label = solution[i][22:len(solution[i])-1] # Eg 1,_datetime.time(14,_15),_35,_1
                        label = label.replace("_", "") # Eg 1,datetime.time(14,15),35,1
                        sep = label.split(",") # ['1', 'datetime.time(14', '15)', '35', '1']
                        day = int(sep[0]) # 1
                        talkId = int(sep[3]) # 35
                        parallel = int(sep[4]) # 1
                        hour, minute = int(sep[1][14:]), int(sep[2][0:-1]) # 14, 15
                        timeObj = time(hour, minute)
                        element = {
                            "day":day,
                            "time":timeObj, 
                            "talkId":talkId,
                            "parallelSesh":parallel
                        }
                        solution[i] = element

                    # To be used later with, schedule tuning by taking topics and similar talks into account
                    # Initialize an empty dictionary to store topic similarity between talks
                    topicSimilarity = {}
                    simThreshold = 4 # Max number of required topics to deem talks as similar talks
                    # Iterate through each combination of talks
                    for i in range(len(ConferenceData["TalkInfo"])):
                        for j in range(i + 1, len(ConferenceData["TalkInfo"])):
                            # Get the topics for the current pair of talks
                            talk1Topics = set(topic[1] for topic in ConferenceData["TalkInfo"][i][3])
                            talk2Topics = set(topic[1] for topic in ConferenceData["TalkInfo"][j][3])

                            # Calculate the similarity between the topics using set intersection - counts number of common topics
                            similarity = len(talk1Topics.intersection(talk2Topics))

                            # Store the similarity between the talks in the topic_similarity dictionary
                            topicSimilarity[(ConferenceData["TalkInfo"][i][0], ConferenceData["TalkInfo"][j][0])] = similarity

                    # Next create the graph based on delegate preferences
                    G = nx.Graph() # Initialize an empty graph
                    prefThreshold = 6

                    # Iterate through each combination of talks and delegates
                    for talkId_1, delegId_1, pref_1 in ConferenceData["DelegLikesTalks"]:
                        for talkId_2, delegId_2, pref_2 in ConferenceData["DelegLikesTalks"]:
                            # Check if both preferences meet the threshold and are for different talks and delegates
                            if pref_1 >= prefThreshold and pref_2 >= prefThreshold:
                                if talkId_1 != talkId_2 and delegId_1 != delegId_2:
                                    # Check if there's already an edge between the two talks
                                    if G.has_edge(talkId_1, talkId_2):
                                        # Update weight with preference score
                                        G[talkId_1][talkId_2]['weight'] += 1
                                    else:
                                        # Add edge with weight
                                        G.add_edge(talkId_1, talkId_2, weight=1)

                    # Apply greedy graph coloring algorithm
                    colouring = greedy_color(G, strategy='largest_first')
                    # The greedy_colour algorithm developed with networkx comes from Classical Coloring of Graphs from A. Kosowski, and K. Manuszewski
                    # https://umv.science.upjs.sk/madaras/ATG/coloring%20algorithms.pdf

                    # Generate final schedule
                    finalSchedule = []
                    for entry in solution:
                        day = entry['day']
                        timeSlot = entry['time']
                        talkId = entry['talkId']
                        parallel_session = entry['parallelSesh']
                        
                        # Assign time slot based on graph coloring
                        colour = colouring[talkId]
                        if colour not in AvailableSlots[day][timeSlot]:
                            AvailableSlots[day][timeSlot].append(colour)
                            finalSchedule.append({'day': day, 'time': timeSlot, 'talkId': talkId, 'parallelSesh': parallel_session})
                        else:
                            # Handle conflict by finding an alternative slot
                            alternative_slot = findAltSlot(AvailableSlots, day)
                            if alternative_slot:
                                AvailableSlots[day][alternative_slot].append(colour)
                                finalSchedule.append({'day': day, 'time': alternative_slot, 'talkId': talkId, 'parallelSesh': parallel_session})
                    
                    # Now to implement the usage of talk similarities (by using common topics) to further tune and refine the schedule
                            # Consider making this option of tuning optional?
                            # For now enforce correct spelling and mentioning of topics in conference creation

                    for entry in solution:
                        talkId = entry['talkId']
                        similarTalks = [t_id for t_id, sim in topicSimilarity.items() if talkId in t_id and sim >= simThreshold]
                        if similarTalks:
                            # Check if any similar talks are already scheduled
                            for scheduledTalk in finalSchedule:
                                if scheduledTalk['talkId'] in similarTalks:
                                    # Adjust the schedule to avoid parallel scheduling
                                    similarTalk = scheduledTalk
                                    # Attempt to schedule the current talk closer to its time if there's available space
                                    currentTalk = entry
                                    currentDay = currentTalk['day']
                                    currentTime = currentTalk['time']
                                    similarTime = similarTalk['time']
                                    if similarTime > currentTime:
                                        # Attempt to schedule the current talk closer to the similar talk
                                        if len([talk for talk in finalSchedule if talk['day'] == currentDay and talk['time'] == currentTime]) < ConferenceData["MaxNumParallelSessions"]:
                                            # Schedule the current talk in the same time slot as the similar talk
                                            finalSchedule.append({'day': currentDay, 'time': currentTime, 'talkId': currentTalk['talkId'], 'parallelSesh': currentTalk['parallelSesh']})
                                        else:
                                            # Find an alternative time slot
                                            alternative_slot = findAltSlot(finalSchedule, currentDay, currentTime)
                                            if alternative_slot:
                                                finalSchedule.append({'day': currentDay, 'time': alternative_slot, 'talkId': currentTalk['talkId'], 'parallelSesh': currentTalk['parallelSesh']})
                                            else:
                                                # Handle conflict by rescheduling the similar talk
                                                similarTalkSlot = findAltSlot(finalSchedule, currentDay, similarTime)
                                                if similarTalkSlot:
                                                    similarTalk['time'] = similarTalkSlot
                                                    finalSchedule.append(similarTalk)
                                                else:
                                                    # No alternative slot available, replace conflicting talk
                                                    finalSchedule.remove(similarTalk)
                                                    finalSchedule.append(currentTalk)
                                    break

                    '''SCHEDULE CREATION Pt 4 - Evaluate & Save'''
                    # Define a function to extract the sorting key
                    def sortingKey(item):
                        return item['day'], item['time'], item['parallelSesh']
                    
                    finalSchedule.sort(key=sortingKey) # Sort the schedule data structure in order of day, then timeslot, then parallel session number

                    # Write schedule to a text file and save a trace to it
                    for entry in finalSchedule:
                        day = entry['day']
                        timing = entry['time']
                        talkId = entry['talkId']
                        parallel = entry['parallelSesh']
                        SCHEDULETimeData[day][timing][parallel - 1] = talkId # At this time this may have ["None", "None", "None" ...] depending on MaxNumOfParallelSessions

                    # Only update the schedule database table if there are changes to the organic data
                        # Including changes in timings, number of talks, number of sessions, or number of delegates
                    # Represented by an arbituary score - hard to track the change in other metrics in isolation
                    scheduleScore = ConferenceData["NumOfDays"] + len(ConferenceData["TalkInfo"]) + ConferenceData["MaxNumParallelSessions"] + len(ConferenceData["DelegateInfo"])
                    lookupScore = 0
                    saveScheduleAsFile(SCHEDULETimeData, conferId.id)
                    lookup = Schedules.query.filter_by(confId=conferId.id).first()
                    if lookup:
                        lookupScore = lookup.score
                    if scheduleScore != lookupScore:
                        # If not previous trace of a schedule for this conference is present make one
                        if lookupScore == 0:
                            newScheduler = Schedules(
                                confId=conferId.id,
                                file=f"schedules/CONF_{conferId.id}.txt",
                                dayOfConf=0,
                                score=scheduleScore,
                                paraSesh=ConferenceData["MaxNumParallelSessions"]
                            )
                            db.session.add(newScheduler)
                        else:
                            lookup.score = scheduleScore
                            lookup.file = f"schedules/CONF_{conferId.id}.txt"
                            lookup.paraSesh = ConferenceData["MaxNumParallelSessions"]
                        db.session.commit()
                        UpdateLog(f"New schedule created for {conferId.confName} using IP, and Graph Theory:\n{SCHEDULETimeData}")
                    return True
                else:
                    UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegate preference data to use.")
            else:
                UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegates registered to it.")
        else:
            UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no talks created for it.")
        return False

def saveScheduleAsFile(schedule, conferenceId):
    file = open(f"schedules/CONF_{conferenceId}.txt","w+")
    for day, stuff in schedule.items():
        file.write(f"D-{day}\n")
        for timing, talks in stuff.items():
            file.write(f"{timing}:{talks}\n")
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
    parallelSys.add_job(scheduleStuff, trigger='interval', minutes=0.3)
    parallelSys.start()
    app.run(debug=True)
    