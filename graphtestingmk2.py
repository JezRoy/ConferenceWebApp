import networkx as nx
from networkx.algorithms.coloring import greedy_color
from datetime import time
import matplotlib.pyplot as plt
import random

# Parse input data
ip_model_schedule = [
    {'day': 1, 'time': time(14, 15), 'talkId': 35, 'parallelSesh': 1},
    # Other schedule entries...
]
# Randomly generate IP model solution schedule
ip_model_schedule = []
talk_ids_scheduled = set()  # Keep track of scheduled talk IDs
allDone = False
for day in range(1, 4):
    for hour in range(9, 18):
        for minute in range(0, 60, 15):
            for session in range(0, 3):
                if random.random() < 0.5:  # Randomly decide if a talk is scheduled at this time slot
                    talk_id = random.randint(1, 50)  # Assuming 50 talks
                    while talk_id in talk_ids_scheduled:  # Ensure talk is not already scheduled
                        if len(talk_ids_scheduled) == 50:
                            allDone = True
                            break
                        talk_id = random.randint(1, 50)
                    if not allDone:
                        talk_ids_scheduled.add(talk_id)
                        ip_model_schedule.append({
                            'day': day,
                            'time': time(hour, minute),
                            'talkId': talk_id,  # Assuming 50 talks
                            'parallelSesh': session + 1  # Random parallel session
                        })
                    else:
                        break
                if allDone:
                    break
            if allDone:
                break
        if allDone:
            break
    if allDone:
        break

talk_information = [
    [1, "Parameterized Matroid-Constrained Maximum Coverage", [1, "François Sellier"], [1, "Parameters"], [2, "Matroid-Constrained"], [3, "Maximum Coverage"]],
    # Other talk information entries...
]
# Randomly generate talk information
talk_information = []
for talk_id in range(1, 51):
    talk_name = f"Talk {talk_id}"
    speaker_id = random.randint(1, 20)  # Assuming 20 speakers
    speaker_name = f"Speaker {speaker_id}"
    topic_ids = random.sample(range(1, 21), random.randint(1, 5))  # Assuming 20 topics
    topics = [[topic_id, f"Topic {topic_id}"] for topic_id in topic_ids]
    talk_information.append([talk_id, talk_name, [speaker_id, speaker_name], *topics])

delegate_preferences = [
    [1, 2, 9], [1, 2, 5], [1, 2, 4], [1, 3, 9], [1, 5, 10],
    # Other delegate preferences entries...
]
# Randomly generate delegate preferences
delegate_preferences = []
for talk_id in range(1, 51):
    for delegate_id in range(1, 100):  # Assuming 100 delegates
        score = random.randint(1, 10)
        delegate_preferences.append([talk_id, delegate_id, score])

available_slots = {
    1: {
        time(9, 0): [],
        # Other available slots...
    },
    2: {
        time(9, 0): [],
        # Other available slots...
    }
}
# Randomly generate available slots
available_slots = {}
for day in range(1, 4):
    available_slots[day] = {}
    for hour in range(9, 18):
        for minute in range(0, 60, 15):
            available_slots[day][time(hour, minute)] = []

# Step 2: Create preference graph
def create_preferences_graph(delegate_likes_talks, preference_threshold=5):
    G = nx.Graph()
    
    for talk_id_1, delegate_id_1, preference_1 in delegate_likes_talks:
        for talk_id_2, delegate_id_2, preference_2 in delegate_likes_talks:
            if preference_1 >= preference_threshold and preference_2 >= preference_threshold:
                if talk_id_1 != talk_id_2 and delegate_id_1 != delegate_id_2:
                    if G.has_edge(talk_id_1, talk_id_2):
                        # Update weight with preference score
                        G[talk_id_1][talk_id_2]['weight'] += 1
                    else:
                        # Add edge with weight
                        G.add_edge(talk_id_1, talk_id_2, weight=1)
    
    return G

# Step 3: Apply graph coloring
def apply_graph_colouring(G):
    # Apply greedy graph coloring algorithm
    coloring = greedy_color(G, strategy='largest_first')
    return coloring

# Step 4: Generate final schedule
def generate_schedule(ip_model_schedule, talk_information, delegate_preferences, available_slots):
    # Create preference graph
    G = create_preferences_graph(delegate_preferences)

    # Plot the graph TODO REMOVE LATER
    pos = nx.spring_layout(G)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw(G, with_labels=True, node_size=1000, node_color="lightblue", font_size=8)
    nx.draw_networkx_edges(G, pos, width=0.5, alpha=0.1)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.show()
    
    # Apply graph coloring
    colouring = apply_graph_colouring(G)
    
    # Generate final schedule
    final_schedule = []
    for entry in ip_model_schedule:
        day = entry['day']
        time_slot = entry['time']
        talk_id = entry['talkId']
        parallel_session = entry['parallelSesh']
        
        # Assign time slot based on graph coloring
        colour = colouring[talk_id]
        if colour not in available_slots[day][time_slot]:
            available_slots[day][time_slot].append(colour)
            final_schedule.append({'day': day, 'time': time_slot, 'talkId': talk_id, 'parallelSesh': parallel_session})
        else:
            # Handle conflict by finding an alternative slot
            alternative_slot = find_alternative_slot(available_slots, day)
            if alternative_slot:
                available_slots[day][alternative_slot].append(colour)
                final_schedule.append({'day': day, 'time': alternative_slot, 'talkId': talk_id, 'parallelSesh': parallel_session})
    
    return final_schedule

# Function to find alternative slot in case of conflict
def find_alternative_slot(available_slots, day):
    for slot, colors in available_slots[day].items():
        if len(colors) < max_parallel_sessions:  # Adjust as per maximum parallel sessions allowed
            return slot
    return None

# Generate final schedule
max_parallel_sessions = 3  # Example maximum parallel sessions allowed
final_schedule = generate_schedule(ip_model_schedule, talk_information, delegate_preferences, available_slots)

# Print final schedule
for entry in final_schedule:
    print(entry)
