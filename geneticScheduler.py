from flask import session, current_app
from werkzeug.security import generate_password_hash, check_password_hash # REMOVE LATER
import networkx as nx
from networkx.algorithms.coloring import greedy_color
from datetime import datetime, timedelta
from datetime import time as tm
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
populationSize = 50
mutateRate = 0.3
generations = 7 # 100

def calculateDelegateScore(delegate_preferences, schedule): # REMOVE POPULATION LATER
    # Use a dictionary to map talk IDs to ratings for fast lookup
    preference_dict = {pref[0]: pref[1] for pref in delegate_preferences if pref[1] >= 6}
    numDesired = len(preference_dict)
    numAttended = 0

    # Return early if there are no desired talks
    if numDesired == 0:
        return 0

    # Iterate through each day in the schedule
    for day, timeslots in schedule.items():
        # Track attended talks in each timeslot to avoid double counting
        attended_per_timeslot = set()

        # Iterate through each timeslot
        for timeslot, talks in timeslots.items():
            # Process each talk in the timeslot
            for talkId in talks:
                if talkId in preference_dict and preference_dict[talkId] > 6 and talkId not in attended_per_timeslot:
                    attended_per_timeslot.add(talkId)
                    numAttended += 1

    # Calculate the percentage of preferred talks attended
    attendedPercent = numAttended / numDesired
    gc.collect()  # Free up memory
    return 1 if attendedPercent >= 0.65 else 0

def workerOLD(delegateId, delegPrefs, schedule):
    # Worker function to calculate score for a single delegate
    records = delegPrefs[delegateId]
    print(delegateId)
    return calculateDelegateScore(records, schedule)

def worker(batch, delegPrefs, schedule):
    scores = []
    for delegateId in batch:
        if delegateId in delegPrefs:  # Check if the delegateId exists in the dictionary
            records = delegPrefs[delegateId]
            score = calculateDelegateScore(records, schedule)
            scores.append(score)
    gc.collect()  # Free up memory
    return scores 

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

    delegateIds = list(delegPrefs.keys())
    # Determine the number of processes to use
    numProcesses = min(multiprocessing.cpu_count(), len(delegateIds))

    # Determine optimal chunk size based on the number of delegates and available processes
    chunk_size = max(1, len(delegateIds) // numProcesses)
    
    # Create a multiprocessing pool
    with multiprocessing.Pool(processes=numProcesses) as pool:
        # Calculate scores for each batch of delegates in parallel using map function
        batch_scores = pool.starmap(worker, [(delegateIds[i:i + chunk_size], delegPrefs, schedule) for i in range(0, len(delegateIds), chunk_size)])


        # Flatten the list of lists returned by starmap
        scores = [score for sublist in batch_scores for score in sublist]
        # Calculate scores for each delegate in parallel using map function
        
        #scores = pool.starmap(worker, [(delegate_id, delegPrefs, schedule) for delegate_id in delegPrefs.keys()])

        # Sum up the scores for all delegates
        total_score = sum(scores)

        gc.collect()  # Free up memory

    # Normalize the total score by the number of delegates and return
    return int(round((total_score / len(delegateIds) * 100)))

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
        individual = createRanIndividual(AvailableSlots, ConferenceData['TalkInfo'], ConferenceData['MaxNumParallelSessions'])
        population.append(individual)
    return population

def evalFitness(population, ConferenceData):
    fitnessScores = []
    for individual in population:
        # A score will be evaluated based on the evaluation metric
        score = calculateScheduleScoreParallel(individual, ConferenceData["DelegLikesTalks"])
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
    for i in range(0, loop, 2): # For a pair of parents as a time from the selection
        parent1 = parents[i]
        parent2 = parents[i+1]

        for i in range(2):
            child = twoPointCrossover(parent1, parent2, ConferenceData["MaxNumParallelSessions"])
            children.append(child)

    return children

def twoPointCrossover(parent1, parent2, numSessions):
     # Two-point crossover
    child = {}
    for day in parent1.keys():
        child[day] = {}
        for slot in parent1[day].keys():
            point1, point2 = sorted(random.sample(range(numSessions), 2))
            child[day][slot] = parent1[day][slot][:point1] + parent2[day][slot][point1:point2] + parent1[day][slot][point2:]
    return child

def updateMutationRate(mutateRate, prevAvgFitness, currentAvgFitness):
    # Reduce mutation rate based on improvement of fitness
    improvement = currentAvgFitness - prevAvgFitness
    if improvement > 0:
        # Reduce mutation rate by a percentage proportional to the improvement
        mutateRate *= (1 - (improvement / currentAvgFitness))
    mutateRate = max(mutateRate, 0.01)  # Ensure mutation rate doesn't drop below a minimum threshold
    return mutateRate

def mutate(individual, mutateRate):
    mutatedInd = individual.copy() # Copy the original individual
    # Mutate a given schedule by performing swap, move, and inverse mutations
    
    def swapTalks(talks):
        """Swap two talks within the same slot at random."""
        if len(talks) > 1:
            i1, i2 = random.sample(range(len(talks)), 2)
            talks[i1], talks[i2] = talks[i2], talks[i1]
        
        return talks

    def swapSlot(slots):
        """Swap two slots within the same day at random."""
        if len(slots) > 1:
            i1, i2 = random.sample(range(len(slots)), 2)
            slot1 = list(slots.keys())[i1]
            slot2 = list(slots.keys())[i2]
            slots[slot1], slots[slot2] = slots[slot2], slots[slot1]

        return slots

    def move(slots):
        """Move a talk from one time slot to another within the same day."""
        sourceSlot = random.choice(list(slots.keys()))
        destSlot = random.choice(list(slots.keys()))
        if slots[sourceSlot]:
            talk = slots[sourceSlot].pop(random.randint(0, len(slots[sourceSlot]) - 1))
            slots[destSlot].append(talk)
        
        return slots

    def inverse(slots):
        """Reverse the order of slots between two random points."""
        slotkeys = list(slots.keys())
        if len(slotkeys) > 1:
            start, end = sorted(random.sample(range(len(slotkeys)), 2))
            # Reverse only the slot order between the selected indices
            subsetKeys = slotkeys[start:end + 1]
            reversedSlots = {k: slots[k] for k in reversed(subsetKeys)}
            for i, k in enumerate(subsetKeys):
                slots[k] = reversedSlots[k]
        
        return slots

    for day, slots in mutatedInd.items():
        for slot, talks in slots.items():
            if random.random() < mutateRate:  # Probability to perform swap on entire time-slot list
                mutatedInd[day][slot] = swapTalks(talks)
        if random.random() < mutateRate:  # Probability to perform swap on entire time-slot list
            mutatedInd[day] = swapSlot(slots)
        if random.random() < mutateRate:  # Probability to perform move
            mutatedInd[day] = move(slots)
        if random.random() < mutateRate / 2:  # Reduced probability for inverse due to its disruptive nature
            mutatedInd[day] = inverse(slots)
        
    return mutatedInd

def selectiveElistism(population, fitnessScores, genNo, generations, eliteProport=0.1):
    # Elitism takes place during the beginning or final proportion of generations NOT all the time
    if genNo <= generations * 0.1 or genNo >= generations * 0.9:
        numElites = int(len(population) * eliteProport)
        eliteIndices = sorted(range(len(fitnessScores)), key=lambda x: fitnessScores[x], reverse=True)[:numElites]
        elites = [population[i] for i in eliteIndices]
        print("Elitism applied")
    else:
        elites = []
    return elites

def GeneticAlgorithm(app, conferId, jobName):
    global active
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
                            currentTime = tm(totalS // 3600, (totalS % 3600) // 60, totalS % 60)
                    
                    '''with open(f"{name}_Slots.txt", "w") as file:
                        for day in AvailableSlots:
                            file.write(f"{day},\n")
                            for record in AvailableSlots[day]:
                                file.write(f"{record}\n")'''

                    print(f"{conferId.id} {conferId.confName} data retrieved, now beginning genetic process...")

                    roomCrossRefer = {}
                    for i in range(int(ConferenceData["MaxNumParallelSessions"])):
                        roomCrossRefer[i] = ConferenceData["RoomCapacities"][i] # Do the same for rooms

                    global mutateRate
                    """ACTUAL LOOP"""
                    # Initialize population
                    population = generatePopulation(populationSize, ConferenceData, AvailableSlots)
                    prevAvgFitness = 0
                    print(f"Generated Population, initial mutation rate: {mutateRate}")

                    # Iterate through generations
                    for generation in range(generations):
                        print(f"{conferId.id} {conferId.confName} - Generation no: {generation + 1} --> {len(population)}")

                        # Evaluate fitness of each schedule in the population
                        fitnessScores = evalFitness(population, ConferenceData)
                        currentAvgFitness = sum(fitnessScores) / len(fitnessScores)
                        print("Found fitness scores and the average for the population of this generation")

                        # Update mutatation rate dynamically
                        mutateRate = updateMutationRate(mutateRate, prevAvgFitness, currentAvgFitness)
                        prevAvgFitness = currentAvgFitness
                        print(f"New mutation rate: {mutateRate}")

                        # Select parents for crossover
                        parents = selectParents(population, fitnessScores)
                        print("Parents found")

                        # Perform crossover to create new generation
                        children = crossover(parents, ConferenceData)
                        print("Children produced by two point crossover for each pair of parents")
                        # Mutate children
                        mutants = []
                        for child in children:
                            mutatedChild = mutate(child, mutateRate) #
                            mutants.append(mutatedChild)
                        print("Children mutated")

                        # Apply selective elitism
                        elites = selectiveElistism(population, fitnessScores, generation, generations)

                        # Replace old population with new generation
                        population = mutants + elites
                    
                    print("Genetic Process complete")

                    # Select best schedule as optimized solution
                    bestSchedule = None
                    bestFitness = float('-inf')

                    for schedule in population:
                        fitness = calculateScheduleScoreParallel(schedule, ConferenceData["DelegLikesTalks"])

                        if fitness > bestFitness:
                            bestSchedule = schedule
                            bestFitness = fitness

                    for day, agenda in bestSchedule.items():
                        for time, slot in agenda.items():
                            SCHEDULETimeData[day][time] = slot

                    finalSchedule = SCHEDULETimeData

                    with open(f"{conferId.confName}_genetic.txt", "wt") as file:
                        print(f"BEST SCHEDULE for {ConferenceData['ConfName']} -> {bestFitness}:" )
                        for day, agenda in bestSchedule.items():
                            print(day)
                            file.write(f"{day} - {bestFitness}")
                            for timing, slot in agenda.items():
                                print(timing, ": ", slot)
                                file.write(f"\n\t{timing}: {slot}")
                    
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
        try:
            active.remove(conferId)
        except:
            pass
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

# Running the scheduler
def scheduleStuff():
    global active
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
                            if jobName not in active:
                                UpdateLog(f"-----Running scheduler for conference {conferId.confName}: {jobName}...-----")
                                active.append(conferId.id)
                                GeneticAlgorithm(app, conferId, jobName)
                            else:
                                UpdateLog(f"Job already scheduled for {conferId.confName}: {jobName}")
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
    parallelSys.add_job(scheduleStuff, id="scheduleStuff")
    parallelSys.start()
    app.run(debug=True)