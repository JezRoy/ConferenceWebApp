import networkx as nx
from networkx.algorithms.coloring import greedy_color
import random


def create_preferences_graph(delegate_likes_talks, talks_info, preference_threshold=5):
    G = nx.Graph()
    
    # Add nodes for talks
    for talk_id, _, _ in talks_info:
        G.add_node(talk_id)
    
    # Add edges based on conflicts (preferences above threshold)
    for i, (talk_id_1, delegate_id_1, preference_1) in enumerate(delegate_likes_talks):
        if preference_1 >= preference_threshold:
            for j in range(i + 1, len(delegate_likes_talks)):
                talk_id_2, delegate_id_2, preference_2 = delegate_likes_talks[j]
                if preference_2 >= preference_threshold and delegate_id_1 != delegate_id_2:
                    if (talk_id_1 != talk_id_2) and not G.has_edge(talk_id_1, talk_id_2):
                        G.add_edge(talk_id_1, talk_id_2, weight=1)
                    elif (talk_id_1 != talk_id_2) and G.has_edge(talk_id_1, talk_id_2):
                        G[talk_id_1][talk_id_2]['weight'] += 1
    
    # Add additional edges for nodes with less than two edges
    for node in G.nodes():
        neighbors = list(G.neighbors(node))
        while len(neighbors) < 2:
            other_node = random.choice(list(G.nodes()))
            if other_node != node and other_node not in neighbors:
                G.add_edge(node, other_node, weight=0)
                neighbors.append(other_node)
    
    return G

def apply_graph_coloring(G):
    # Apply greedy graph coloring algorithm
    coloring = greedy_color(G, strategy='largest_first')
    return coloring

# Example usage
numDelegs = 70
numTalks = 30
delegate_likes_talks_large = [(random.randint(1, numTalks), random.randint(1, numDelegs + 1), random.randint(1, 10)) for _ in range(numDelegs)]
talks_info_large = [(i, f"Talk {i}", f"Speaker {i}") for i in range(1, numTalks + 1)]
preferences_graph_large = create_preferences_graph(delegate_likes_talks_large, talks_info_large)
coloring = apply_graph_coloring(preferences_graph_large)
import matplotlib.pyplot as plt

# Draw the graph
pos = nx.spring_layout(preferences_graph_large)
nx.draw(preferences_graph_large, pos, with_labels=True, node_size=1000, node_color="lightblue", font_size=10)
nx.draw_networkx_edge_labels(preferences_graph_large, pos)


# Visualize the conflict graph with coloring
plt.figure(figsize=(12, 8))
nx.draw(preferences_graph_large, with_labels=True, node_size=500, font_size=10, font_color='white', node_color=list(coloring.values()), cmap=plt.cm.rainbow)
plt.title('Conflict Graph with Coloring')
plt.show()

plt.title("Delegate Preferences Graph")
plt.show()



