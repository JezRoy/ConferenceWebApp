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
from werkzeug.security import generate_password_hash, check_password_hash # REMOVE LATER
from celery import Celery
from networkx.algorithms.coloring import greedy_color
from datetime import datetime, timedelta, time
import pulp
import random
import multiprocessing
from multiprocessing import freeze_support
import gc
from website import CreateApp
# This web app has been created with help from
# https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim
from website.functions import UpdateLog
from website.models import db, User, ConfDeleg, Conferences, ConfRooms, ConfHosts, Talks, TopicTalks, DelegTalks, Speakers, Topics, Topicsconf, DelTopics, Schedules
from website.__init__ import parallelSys
import os
os.makedirs("schedules", exist_ok=True)

app = CreateApp()
global active
active = []

import string
import random
from werkzeug.security import generate_password_hash

def generateRandomString(length=7):
    # Define the characters to choose from
    characters = string.ascii_letters + string.digits  # You can add more characters if needed
    
    # Generate the random string
    randomString = ''.join(random.choice(characters) for _ in range(length))
    
    return randomString

def generateRandomDateOfBirth(start_date, end_date):
    # Convert start_date and end_date strings to datetime objects
    startDate = datetime.strptime(start_date, '%Y-%m-%d')
    endDate = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Calculate the range of days between start_date and end_date
    delta = endDate - startDate
    
    # Generate a random number of days within the range
    randomNumberOfDays = random.randint(0, delta.days)
    
    # Add the random number of days to start_date to get the random date of birth
    randomDateOfBirth = startDate + timedelta(days=randomNumberOfDays)
    
    return randomDateOfBirth

# Create new delegates and assign random preference scores for each talk
def createNewDelegates(app, conference_id):
    def MessageMe(thing):
        """
        Tracking scheduler output seprately from the rest of the app.
        """
        myFile = open(f"ConfID_{conference_id}.txt", "a")
        contents = f"{thing}\n"
        myFile.write(contents)
        myFile.close()
        return True
    
    with app.app_context():
        MessageMe("Starting to run autoGen >>>>")
        # Create random user details
        username = generateRandomString(6)
        password = generate_password_hash(generateRandomString(13))
        emailAddr = generateRandomString(6).join("@gmail.com")
        firstName = username
        lastName = generateRandomString(6)
        dateObj = generateRandomDateOfBirth('1950-01-01', '2005-12-31')
        dateStr = dateObj.strftime('%Y-%m-%d')
        # Parse the string date
        dob = datetime.strptime(dateStr, '%Y-%m-%d').date()
        usertype = 'delegate'
        newUser = User(
            username=username,
            passwordHash=password,
            email=emailAddr,
            firstName=firstName,
            lastName=lastName,
            dob=dob,
            type=usertype
        )
        db.session.add(newUser)
        db.session.commit()
        MessageMe(f"--> User {newUser.id} : {[username, password, emailAddr, firstName, lastName, dob]}")
        # Register the user for the conference
        userId = newUser.id
        registration = ConfDeleg(
            confId=conference_id,
            delegId=userId
        )
        db.session.add(registration)
        db.session.commit()
        # Retrieve all talks associated with the conference
        talks = Talks.query.filter_by(confId=conference_id).all()
        collection = []
        for thing in talks:
            talkId = thing.id
            topicIDs = []
            assoTopics = TopicTalks.query.filter_by(talkId=talkId).all()
            for topic in assoTopics:
                topicIDs.append(topic.topicId)
            record = [talkId, topicIDs]
            collection.append(record)
        # And rate the talks
        for talk in collection:
            rating = random.randint(1, 10)
            recording = DelegTalks(
                delegId=userId,
                talkId=talk[0],
                confId=conference_id,
                prefLvl=rating
            )
            db.session.add(recording)
            db.session.commit()
            MessageMe(f"--|--|--> {userId} : {talk[0]}, {rating}")
            if rating >= 6:
                # Add a record to DelTopics table too
                for topicId in talk[1]:
                    entry = DelTopics(
                        delegId=userId,
                        topicId=topicId,
                        confId=conference_id
                    )
                    db.session.add(entry)
                    db.session.commit()
                    MessageMe(f"--|--|--|--|--> {userId} : {topicId}")
        return True

# Evaluation function
def calculateDelegateScore(delegate_preferences, schedule):
    # Initialize variables to count the number of preferred talks and attended talks
    numDesired = 0
    numAttended = 0

    for record in delegate_preferences:
        if record[1] >= 6:
            numDesired += 1
    
    # Iterate through each day in the schedule
    for day, timeslots in schedule.items():
        # Initialize a counter to track the number of highly rated talks attended by the delegate for each timeslot
        attendedPerTimeslot = {timeslot: 0 for timeslot in timeslots}
        
        # Iterate through each timeslot in the day
        for timeslot in timeslots:
            # Iterate through all talks scheduled in the timeslot
            for talkId in timeslots[timeslot]:
                # Check if the talk is in the delegate's preferences and if it's highly rated
                for preference in delegate_preferences:
                    if preference[0] == talkId and preference[1] > 6:  # Assuming a score of 6 or higher is considered highly rated
                        # Check if the number of highly rated talks attended in the timeslot is not greater than 1
                        if attendedPerTimeslot[timeslot] < 1:
                            # Increment the counter for attended highly rated talks in the timeslot
                            attendedPerTimeslot[timeslot] += 1
                            numAttended += 1
                            break  # Break out of the loop once a highly rated talk is attended
    
    # Calculate the percentage of preferred talks attended
    attendedPercent = numAttended / numDesired
    return 1 if attendedPercent >= 0.65 else 0 

def worker(delegateId, delegPrefs, schedule):
    # Worker function to calculate score for a single delegate
    records = delegPrefs[delegateId]
    return calculateDelegateScore(records, schedule)

def calculateScheduleScoreParallel(schedule, deleg_likes_talks):
    total_score = 0
    delegPrefs = {
        # DelegateId1 : [[talkId, score], [talkId, score], [talkId, score] ... ],
        # DelegateId2 : [[talkId, score], [talkId, score], [talkId, score] ... ]
    }

    for record in deleg_likes_talks:
        if record[1] not in delegPrefs:
            delegPrefs[record[1]] = []
        delegPrefs[record[1]].append([record[0], record[2]])

    # Determine the number of processes to use
    num_processes = min(multiprocessing.cpu_count(), len(delegPrefs))
    
    # Create a multiprocessing pool
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Calculate scores for each delegate in parallel using map function
        scores = pool.starmap(worker, [(delegate_id, delegPrefs, schedule) for delegate_id in delegPrefs.keys()])

        # Sum up the scores for all delegates
        total_score = sum(scores)

    # Normalize the total score by the number of delegates and return
    return int(round((total_score / len(delegPrefs) * 100)))

# Running the scheduler
def scheduleStuff():
    message = "Scheduler is still running... Designed to run once every 30 seconds for every conference..."
    today = datetime.today().date()
    with app.app_context():

        # Extract conference information
        conferences = db.session.query(Conferences).all()
        # The scheduler should only run for a conference, once the delegate registration deadline is passed, 
        # and if the start date for the conference has not been passed
        if conferences:
            # Check active jobs
            # Start a separate job for each conference
            for conferId in conferences:
                changesMade = Schedules.query.filter_by(confId=conferId.id).first()
                if not changesMade or changesMade.editInfoFlag == 0: # Either this conference doesnt have a schedule record, or changes have been made for it
                    jobName = f"conference_job_{conferId.confName}"
                    if conferId.id not in active:
                        if conferId.paperFinalisationDate < today and conferId.confStart > today: # It is the right phase to schedule for this conference
                            UpdateLog(f"-----Running scheduler for conference {conferId.confName}: {jobName}...-----")
                            active.append(conferId.id)
                            parallelSys.add_job(SCHEDULEConference, args=(app, conferId, jobName), id=jobName)
                        else:
                            UpdateLog(f"-----Unnecessary time phase for {conferId.confName}, thus no scheduling will occur this conference.-----")
                    else: 
                        UpdateLog(f"-----Scheduler is already dealing with {conferId.confName}: {jobName}!-----")
                else:
                    UpdateLog(f"Changes have not been made to conference {conferId.id}")
        else:
            UpdateLog("Scheduler cannot create any schedules, as the conference database is empty.")
        UpdateLog(f"Active jobs: {active}")
        
def SCHEDULEConference(app, conferId, jobName):
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
            popScore = 0
            data = [talk.id, talk.talkName]
            speaker = Speakers.query.filter_by(id=talk.speakerId).all()[0]
            data.append([speaker.id, speaker.deleg])

            # Extract topic information
            topics = []
            topicsAsso = TopicTalks.query.filter_by(talkId=talk.id).all()
            # Relate topic to talks
            for topicId in topicsAsso:
                tag = Topics.query.filter_by(id=topicId.topicId).first()
                topics.append([topicId.topicId, tag.topic])
            data.append(topics)
            for deleg in DelegateInfo:
                delegId = deleg[0]
                queryMade = DelegTalks.query.filter(DelegTalks.delegId == delegId).filter(DelegTalks.confId == conferId.id).filter(DelegTalks.talkId == talk.id).all()
                for record in queryMade:
                    if record.prefLvl >= 6:
                        popScore += 1
                    elif record.prefLvl >= 8:
                        popScore += 2
            data.append(popScore) # Determine popularity score
            if popScore >= int(round((len(DelegateInfo) * 0.50))): 
                # Talk is considered popular
                data.append(1)
            else:
                data.append(0)
            data.append(talk.repitions)
            talks.append(data)

            # Relate delegates to talks
            for item in DelegateInfo:
                # Find a possible record of each delegate rating each talk
                queryMade = DelegTalks.query.filter(DelegTalks.delegId == item[0]).filter(DelegTalks.confId == conferId.id).filter(DelegTalks.talkId == talk.id).all()
                for queried in queryMade:
                    if [queried.talkId, queried.delegId, queried.prefLvl] not in Deleg2Talks:
                        # Track the preference a talk, by a certain delegate, and the score they gave it
                        Deleg2Talks.append([queried.talkId, queried.delegId, queried.prefLvl])

        # Add room capacity information
        rooms = []
        roomsFound = ConfRooms.query.filter_by(confId=conferId.id).all()
        for i in range(conferId.numSessions):
            roomInQ = roomsFound[i].capacity
            rooms.append(roomInQ)

        # Relate topics to delegates
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
                    "MaxNumParallelSessions": conferId.numSessions, # Number of parallel sessions / rooms
                    "TalkInfo": talks,
                    "DelegLikesTalks": Deleg2Talks,
                    "DelegateInfo": DelegateInfo,
                    "RoomCapacities": rooms
        }

        if talks != []:
            if DelegateInfo != []:
                if Deleg2Talks != []:
                    # Track breaks, lunches and talks for all conferences
                    
                    '''SCHEDULE CREATION Pt 1 - Timing Slot Setup'''
                    SCHEDULETimeData = { # THE ACTUAL SCHEDULE
                        # Each time slot is saved as a datetime structure
                    }
                    AvailableSlots = {
                        # Only the available slots to schedule will be given to the model
                    }

                    timeLength = ConferenceData["AverageTalkLength"] # In minutes
                    maxTalks = ConferenceData["IdealNoTalkPerSession"]
                    breakTime = 15 # Possibly an option to give users

                    name = ConferenceData["ConfName"]
                
                    '''with open(f"{name}_Deleg2Talks.txt", "w") as file:
                        for record in Deleg2Talks:
                            file.write(f"{record},\n")'''

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
                        sessionCount = 0
        
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
                    
                    '''with open(f"{name}_Slots.txt", "w") as file:
                        for day in AvailableSlots:
                            file.write(f"{day},\n")
                            for record in AvailableSlots[day]:
                                file.write(f"{record}\n")'''

                    '''SCHEDULE CREATION Pt 2 - IP Scheduler'''
                    talkCrossRefer = {} # Handy cross referencing tools for once the solution is solved
                    slotCrossRefer = {}
                    roomCrossRefer = {}
                    deleCrossRefer = {}

                    # Parameters
                    n = len(ConferenceData["DelegateInfo"])  # Number of delegates
                    m = len(ConferenceData["TalkInfo"])   # Number of talks
                    D = int(ConferenceData["NumOfDays"])  # Number of days
                    S = len(list(AvailableSlots[1].keys()))   # Number of time slots per day
                    R = int(ConferenceData["MaxNumParallelSessions"])   # Number of rooms

                    for i in range(m):
                        talkCrossRefer[i] = ConferenceData["TalkInfo"][i][0] # Associate talkId with actual talk number as used in the model

                    for i in range(n):
                        deleCrossRefer[i] = ConferenceData["DelegateInfo"][i][0] # Do the same for delegates

                    # Initialize slotCrossRefer properly
                    for i in range(S):  # Ensure this covers all days
                        slotCrossRefer[i] = list(AvailableSlots[1].keys())[i]

                    for i in range(R):
                        roomCrossRefer[i] = ConferenceData["RoomCapacities"][i] # Do the same for rooms

                    alpha = 0.35 # Weight for preferences
                    gamma = 0.45 # Weight for diversity
                    beta = 0.2 # Weight for minimizing talk repitiions

                    preferences = { (i, t): -1 for i in range(n) for t in range(m) }
                    for key, _ in preferences.items():
                        modelDelegNo = key[0]
                        modelTalkNo = key[1]
                        talkId = talkCrossRefer[modelTalkNo]
                        delegId = deleCrossRefer[modelDelegNo]
                        prefScore = 4
                        for record in ConferenceData["DelegLikesTalks"]:
                            if record[0] == talkId and record[1] == delegId:
                                prefScore = record[2]
                                break
                        preferences[key] = prefScore
                        
                    capacities = { r: -1 for r in range(R) }
                    for key, _ in capacities.items():
                        capacities[key] = roomCrossRefer[key]

                    maxTimes = { t: 1 for t in range(m) }
                    for key, _ in maxTimes.items():
                        modelTalkNo = key
                        talkId = talkCrossRefer[modelTalkNo]
                        repeaters = 1
                        for record in ConferenceData["TalkInfo"]:
                            if record[0] == talkId:
                                repeaters = record[6]
                        maxTimes[key] = repeaters
                    
                    # Decision variables
                    x = pulp.LpVariable.dicts("Attendance", (range(n), range(m), range(D), range(S), range(R)), cat='Binary')

                    """for key, value in slotCrossRefer.items():
                        print(f"model Talk number: {key}, actual time-slot: {value} ")"""

                    # Define the problem
                    model = pulp.LpProblem("Conference_Scheduling", pulp.LpMaximize)

                    # Helper variable for the minimum condition
                    attendCount = pulp.LpVariable.dicts("AttendanceCount", (range(n), range(m)), 0, 1, cat='Continuous')

                    # Objective function with weights
                    model += (
                        alpha * pulp.lpSum(preferences[i, t] * x[i][t][d][s][r] for i in range(n) for t in range(m) for d in range(D) for s in range(S) for r in range(R)) +
                        gamma * pulp.lpSum(attendCount[i][t] for i in range(n) for t in range(m)) -
                        beta * pulp.lpSum(pulp.lpSum(x[i][t][d][s][r] for i in range(n)) for t in range(m) for d in range(D) for s in range(S) for r in range(R))
                    )

                    # Constraints
                    # Capacity constraints
                    for r in range(R):
                        for d in range(D):
                            for s in range(S):
                                model += sum(x[i][t][d][s][r] for i in range(n) for t in range(m)) <= capacities[r]

                    # Unique attendance constraints
                    for i in range(n):
                        for t in range(m):
                            model += sum(x[i][t][d][s][r] for d in range(D) for s in range(S) for r in range(R)) <= 1

                    # Schedule constraints
                    for i in range(n):
                        for d in range(D):
                            for s in range(S):
                                model += sum(x[i][t][d][s][r] for t in range(m) for r in range(R)) <= 1

                    # Talk frequency constraints
                    for t in range(m):
                        model += sum(x[i][t][d][s][r] for i in range(n) for d in range(D) for s in range(S) for r in range(R)) <= maxTimes[t]

                    # Room usage constraints
                    for d in range(D):
                        for s in range(S):
                            for r in range(R):
                                model += sum(x[i][t][d][s][r] for i in range(n) for t in range(m)) <= 1

                    # Solve the model
                    model.solve()

                    # Generate final schedule
                    finalSchedule = {}
                    # Initialize the structure for each day and fill each timeslot with a list of None (indicating empty rooms)
                    for d in range(D):
                        day_agenda = {}
                        for s in range(S):
                            # Assume the number of rooms R is the number of elements to be placed in each timeslot list
                            day_agenda[slotCrossRefer[s]] = [None] * R
                        finalSchedule[d + 1] = day_agenda

                    # Populate the finalSchedule dictionary with talk assignments
                    for t in range(m):
                        talkId = talkCrossRefer[t]
                        for d in range(D):
                            for s in range(S):
                                for r in range(R):
                                    attendees = [i+1 for i in range(n) if x[i][t][d][s][r].value() == 1]
                                    if attendees:
                                        finalSchedule[d + 1][slotCrossRefer[s]][r] = talkId
                    """for day, agenda in finalSchedule.items():
                        print(day)
                        for timeslot, rooms in agenda.items():
                            print(f"{timeslot} contains {rooms}")"""
                    

                    '''SCHEDULE CREATION Pt 3 - Evaluate & Save'''
                    # Only update the schedule database table if there are changes to the organic data
                        # Including changes in timings, number of talks, number of sessions, or number of delegates
                    # Represented by an arbituary score - hard to track the change in other metrics in isolation
                        # This score should include changes to delegate preferences ideally
                        # It should also be able to minimise the number of "None" time slots (where no talk is scheduled)
                    lookupScore = 0
                    scheduleScore = calculateScheduleScoreParallel(finalSchedule, ConferenceData["DelegLikesTalks"])
                    lookup = Schedules.query.filter_by(confId=conferId.id).first()
                    if lookup:
                        lookupScore = lookup.score
                        if lookup.editInfoFlag == 0: # Overwrite regardless
                            saveScheduleAsFile(finalSchedule, conferId.id, roomCrossRefer)
                            lookup.score = scheduleScore
                            lookup.file = f"schedules/CONF_{conferId.id}.txt"
                            lookup.paraSesh = ConferenceData["MaxNumParallelSessions"]
                            lookup.editInfoFlag = 1 # Ammend flag for this set of conference data
                            db.session.commit()
                            UpdateLog(f"New schedule created for {conferId.confName} with score {scheduleScore} using IP:\n{finalSchedule}")
                        else: # Overwrite only better schedule
                            if scheduleScore >= lookupScore:
                                saveScheduleAsFile(finalSchedule, conferId.id, roomCrossRefer)
                                lookup.score = scheduleScore
                                lookup.editInfoFlag = 1
                                lookup.file = f"schedules/CONF_{conferId.id}.txt"
                                lookup.paraSesh = ConferenceData["MaxNumParallelSessions"]
                            db.session.commit()
                            UpdateLog(f"New schedule created for {conferId.confName} with score {scheduleScore} using IP:\n{finalSchedule}")
                    else: # Brand new schedule
                        saveScheduleAsFile(finalSchedule, conferId.id, roomCrossRefer)
                        newScheduler = Schedules(
                            confId=conferId.id,
                            file=f"schedules/CONF_{conferId.id}.txt",
                            editInfoFlag=1,
                            score=scheduleScore,
                            paraSesh=ConferenceData["MaxNumParallelSessions"]
                        )
                        db.session.add(newScheduler)
                        db.session.commit()
                        UpdateLog(f"New schedule created for {conferId.confName} with score {scheduleScore} using IP:\n{finalSchedule}")
                    try:
                        active.remove(conferId)
                    except:
                        pass
                    return True
                else:
                    UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegate preference data to use.")
            else:
                UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no Delegates registered to it.")
        else:
            UpdateLog(f"Scheduler cannot create any schedules for {conferId.confName}, as the conference has no talks created for it.")
        active.remove(conferId)
        parallelSys.remove_job(jobName)
        return False

def saveScheduleAsFile(schedule, conferenceId, roomCrossRefer):
    file = open(f"schedules/CONF_{conferenceId}.txt","w+")
    for day, stuff in schedule.items():
        stringy = ""
        for value in list(roomCrossRefer.values()):
            stringy += f"{value}|"
        file.write(f"D-{day}|{stringy}\n")
        for timing, talks in stuff.items():
            file.write(f"{timing}:{talks}\n")
    file.close()

if __name__ == '__main__':
    freeze_support()

    # Run app
    parallelSys.add_job(scheduleStuff, trigger='interval', minutes=0.75)
    parallelSys.start()
    app.run(debug=True)
    