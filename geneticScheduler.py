from flask import session, current_app
from werkzeug.security import generate_password_hash, check_password_hash # REMOVE LATER
import networkx as nx
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
populationSize = 75
mutateRate = 0.1
generations = 10 # 100

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

# An individual is a schedule
def createRanIndividual(AvailableSlots, TalkInfo, numSessions):
    # Creating a random schedule (individual)
    individual = AvailableSlots
    ids = []
    for talk in TalkInfo:
        if talk[0] not in ids:
            ids.append(talk[0])
    # Random assignment
    random.shuffle(ids)
    assigned = []
    for day, agenda in individual.items():
        for time, slots in agenda.items():
            if slots == []:
                for i in range(numSessions): 
                    individual[day][time].append('None')
    # Randomly choose whether or not to assign a random talk to a specific time slot
    for day, agenda in individual.items():
        for time, slots in agenda.items():
            for i in range(numSessions):
                scheduleSmth = random.randint(0, 10) # 0 counts as false in python
                if scheduleSmth % 3 == 0:
                    talk = random.choice(ids)
                    choiceCount = 1
                    while talk in assigned:
                        if choiceCount == len(ids):
                            talk = 'None'
                        if talk not in assigned:
                            break
                        talk = random.choice(ids)
                        choiceCount += 1
                    individual[day][time][i] = talk
                    if talk != 'None':
                        assigned.append(talk)
    return individual

def generatePopulation(populationSize, ConferenceData, AvailableSlots):
    population = []
    for _ in range(populationSize):
        individual = createRanIndividual(AvailableSlots, ConferenceData['TalkInfo'], ConferenceData['numSessions'])
        population.append(individual)
    return population

def evalFitness(population, Deleg2Talks):
    fitnessScores = []
    for individual in population:
        # A score will be evaluated based on the evaluation metric
        #print(individual)
        score = calculateScheduleScoreParallel(individual, Deleg2Talks)
        fitnessScores.append(score)
    return fitnessScores

def selectParents(population, fitnessScores, candidates4Tournie=round(populationSize / 5)):
    # Use tournament selection to choose parents to produce offspring
    selected = []
    for count in range(len(population)):
        # Randomly select a subset of schedules
        pool = random.sample(list(zip(population, fitnessScores)), k=candidates4Tournie)
        #print(pool)
        # Choose the schedule with the highest fitness score from the subset
        select = max(pool, key=lambda x: x[1])[0]
        selected.append(select)

    return selected

def crossover(parents, ConferenceData):
    children = []
    loop = -1
    if len(parents) % 2 == 0:
        loop = len(parents)
    else:
        loop =  len(parents) - 1
    for i in range(0, loop, 2):
        parent1 = parents[i]
        parent2 = parents[i+1]
        # Perform crossover to create children
        child = {}
        for i in range(2): # Having two kids
            for day in parent1.keys():
                child[day] = {}
                for slot in parent1[day].keys():
                    # Randomly choose crossover point
                    crossover = random.randint(0, ConferenceData['numSessions'])
                    # Combine talks from parents
                    child[day][slot] = parent1[day][slot][:crossover] + parent2[day][slot][crossover:]
            children.append(child)
    return children

def mutate(individual, mutateRate):
    mutatedInd = individual.copy() # Copy the original schedule
    
    def swap(slot1, slot2):
        talk1 = random.choice(slot1)
        talk2 = random.choice(slot2)
        ind1 = slot1.index(talk1)
        ind2 = slot2.index(talk2)

        slot1[ind1] = talk2
        slot2[ind2] = talk1

        return slot1, slot2
    
    def move(talks, timing, timeslots, day):
        # Randomly select a talk to move within the currently observed slot
        talkToMove = random.choice(talks)
        # Remove selected talk from current slot
        place = talks.index(talkToMove)
        mutatedInd[day][timing][place] = 'None'

        # Randomly select a destination timeslot
        destination = random.choice(timeslots)
        found = False
        tried = [destination]
        while not found:
            # Add the talk to the destination if there is space
            if 'None' in mutatedInd[day][destination]:
                place = mutatedInd[day][destination].index('None')
                mutatedInd[day][destination][place] = talkToMove
                found = True
            else:
                # Otherwise choose another destination
                destination = random.choice(timeslots)
                tried.append(destination)
            if len(destination) == len(timeslots) and not found:
                return False
        if found == True:
            return True

    for day, agenda in mutatedInd.items():
        timeslots = list(agenda.keys())
        for ind, key in enumerate(timeslots):
            # index of timeslots, actual timing
            timing = key
            slots = agenda[key]
            if random.random() < mutateRate:
                # Perform mutation based on the chosen mutation type
                mutationType = random.choice(['swap', 'move'])
                if mutationType == 'swap':
                    # Swap two talks within the parallel-level / sequence of timings
                    if ind < len(agenda) - 1:
                        nextTiming = timeslots[ind + 1]
                        #mutatedInd[day][timing], mutatedInd[day][nextTiming] = swap(mutatedInd[day][timing], mutatedInd[day][nextTiming])
                        swap(mutatedInd[day][timing], mutatedInd[day][nextTiming])
                    if ind > 0:
                        prevTiming = timeslots[ind - 1]
                        #mutatedInd[day][timing], mutatedInd[day][prevTiming] = swap(mutatedInd[day][timing], mutatedInd[day][prevTiming])
                        swap(mutatedInd[day][timing], mutatedInd[day][prevTiming])
                else:
                    # Move a talk to a different timeslot within the same day
                    moved = move(slots, timing, timeslots, day)
                    if not moved:
                        # Swap two talks within the parallel-level / sequence of timings
                        if ind < len(agenda) - 1:
                            nextTiming = agenda[ind + 1]
                            mutatedInd[day][timing], mutatedInd[day][nextTiming] = swap(mutatedInd[day][timing], mutatedInd[day][nextTiming])
                        if ind > 0:
                            prevTiming = agenda[ind + 1]
                            mutatedInd[day][timing], mutatedInd[day][prevTiming] = swap(mutatedInd[day][timing], mutatedInd[day][prevTiming])
    return mutatedInd

def GeneticAlgorithm(app, conferId, jobName):
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


        """ACTUAL LOOP"""
        # Initialize population
        population = generatePopulation(populationSize)

        # Iterate through generations
        for generation in range(generations):
            # Evaluate fitness of each schedule in the population
            fitnessScores = evalFitness(population, Deleg2Talks)

            # Select paren/ts for crossover
            parents = selectParents(population, fitnessScores)

            # Perform crossover to create new generation
            children = crossover(parents)

            # Mutate children
            mutants = []
            for child in children:
                mutatedChild = mutate(child, mutateRate)
                mutants.append(mutatedChild)

            # Replace old population with new generation
            population = mutants

        # Select best schedule as optimized solution
        bestSchedule = None
        bestFitness = float('-inf')

        for schedule in population:
            fitness = calculateScheduleScoreParallel(schedule, Deleg2Talks)

            if fitness > bestFitness:
                bestSchedule = schedule
                bestFitness = fitness

        UpdateLog(f"BEST SCHEDULE -> {bestFitness}:\n{bestSchedule}" )
        active.remove(conferId)
        parallelSys.remove_job(jobName)

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

if __name__ == '__main__':
    freeze_support()

    # Run app
    parallelSys.add_job(scheduleStuff, trigger='interval', minutes=0.5)
    parallelSys.start()
    app.run(debug=True)