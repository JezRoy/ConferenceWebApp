import networkx as nx
from networkx.algorithms.coloring import greedy_color
import random

def create_preferences_graph(delegate_likes_talks, preference_threshold=5):
    G = nx.Graph()
    
    for talk_id_1, delegate_id_1, preference_1 in delegate_likes_talks:
        for talk_id_2, delegate_id_2, preference_2 in delegate_likes_talks:
            if preference_1 >= preference_threshold and preference_2 >= preference_threshold:
                if talk_id_1 != talk_id_2 and delegate_id_1 != delegate_id_2:
                    if G.has_edge(talk_id_1, talk_id_2):
                        # Update weight with preference score
                        G[talk_id_1][talk_id_2]['weight'] += preference_1 + preference_2
                    else:
                        # Add edge with weight
                        G.add_edge(talk_id_1, talk_id_2, weight=preference_1 + preference_2)
    
    return G

def apply_graph_coloring(G):
    # Apply greedy graph coloring algorithm
    coloring = greedy_color(G, strategy='largest_first')
    return coloring

def find_hamiltonian_path(G):
    def hamiltonian_path_util(u, path):
        nonlocal found_path
        
        if len(path) == len(G.nodes):
            found_path = True
            return path
        
        for v in G.neighbors(u):
            if v not in path and not found_path:
                path.append(v)
                if hamiltonian_path_util(v, path):
                    return path
                path.pop()
        
        return None
    
    found_path = False
    starting_node = next(iter(G.nodes))
    path = [starting_node]
    return hamiltonian_path_util(starting_node, path)

def find_hamilton_paths(graph):
    # Step 1: Find the coloring of the graph
    coloring = nx.greedy_color(graph, strategy='largest_first')
    
    # Step 2: Group nodes by color
    color_groups = {}
    for node, color in coloring.items():
        if color not in color_groups:
            color_groups[color] = [node]
        else:
            color_groups[color].append(node)
    
    # Step 3: Find Hamiltonian paths for each color group
    hamilton_paths = []
    for group in color_groups.values():
        subgraph = graph.subgraph(group)
        cycle = list(nx.find_cycle(subgraph))
        hamilton_paths.extend(cycle)
    
    return hamilton_paths

def create_topics_graph(talks_info):
    G = nx.Graph()
    
    # Add nodes for talks
    for talk_info in talks_info:
        talk_id = talk_info[0]
        G.add_node(talk_id)
    
    # Add edges based on common topics
    for i in range(len(talks_info)):
        talk_id_1, _, _, topics_1 = talks_info[i]
        for j in range(i + 1, len(talks_info)):
            talk_id_2, _, _, topics_2 = talks_info[j]
            common_topics = set(topic_1[0] for topic_1 in topics_1).intersection(set(topic_2[0] for topic_2 in topics_2))
            if common_topics:
                G.add_edge(talk_id_1, talk_id_2, weight=len(common_topics))
    
    return G

talks_info = [
    [1, 'Parameterized Matroid-Constrained Maximum Coverage', [1, 'Fran�ois Sellier'], [[1, 'Parameters'], [2, 'Matroid-Constrained'], [3, 'Maximum Coverage']]],
    [2, 'Sorting Finite Automata via Partition Refinement', [2, 'Ruben Becker'], [[4, 'Finite Automata'], [5, 'Partition Refinement']]],
    [3, 'Lyndon Arrays in Sublinear Time', [3, 'Hideo Bannai'], [[6, 'Lyndon Arrays'], [7, 'Sublinear Time']]],
    [4, 'Linear Time Construction of Cover Suffix Tree and Applications', [4, 'Jakub Radoszewski'], [[8, 'Linear Time Construction'], [9, 'Cover Suffix Tree'], [10, 'Applications']]],
    [5, 'Subcubic algorithm for (Unweighted) Unrooted Tree Edit Distance', [5, 'Krzysztof Pi�ro'], [[11, 'Subcubic algorithm'], [12, 'Unrooted Tree Edit Distance']]],
    [6, 'Lossy Kernelization for (Implicit) Hitting Set Problems', [6, 'Stephan Thomasse'], [[13, 'Lossy Kernelization'], [14, 'Hitting Set Problems']]],
    [7, 'Fault Tolerance in Euclidean Committee Selection', [7, 'Jie Xue'], [[15, 'Fault Tolerance'], [16, 'Euclidean Committee Selection']]]
]

# Example usage
numDelegs = 70
numTalks = 30
delegate_likes_talks_large = [(random.randint(1, numTalks), random.randint(1, numDelegs + 1), random.randint(1, 10)) for _ in range(numDelegs)]
talks_info_large = [(i, f"Talk {i}", f"Speaker {i}") for i in range(1, numTalks + 1)]
#preferences_graph_large = create_preferences_graph(delegate_likes_talks_large, talks_info_large)

preferences_graph_large = create_preferences_graph(delegate_likes_talks_large)
topics_graph = create_topics_graph(talks_info)

# Colouring THEN hamilton:
coloring = apply_graph_coloring(preferences_graph_large)
colored_graph = nx.Graph()
colored_graph.add_nodes_from(preferences_graph_large.nodes())
colored_graph.add_edges_from(preferences_graph_large.edges())
nx.set_node_attributes(colored_graph, coloring, 'color')
hamilton_paths = find_hamiltonian_path(preferences_graph_large)

coloring = apply_graph_coloring(preferences_graph_large)
import matplotlib.pyplot as plt

# Draw the graph
pos = nx.spring_layout(preferences_graph_large) # Interchange with preferences_graph_large
nx.draw(preferences_graph_large, pos, with_labels=True, node_size=1000, node_color="lightblue", font_size=10)
nx.draw_networkx_edge_labels(preferences_graph_large, pos)

# Visualize the conflict graph with coloring
plt.figure(figsize=(12, 8))
nx.draw(preferences_graph_large, with_labels=True, node_size=500, font_size=10, font_color='white', node_color=list(coloring.values()), cmap=plt.cm.rainbow)
plt.title('Conflict Graph with Coloring')
plt.show()

# Extract node and edge data
nodes = list(preferences_graph_large.nodes())
edges = list(preferences_graph_large.edges())

# Convert graph to dictionaries
node_attributes = dict(preferences_graph_large.nodes(data=True))
# Initialize an empty dictionary for edge attributes
edge_attributes = {}

# Iterate over edges and their data
for edge in preferences_graph_large.edges(data=True):
    if len(edge) == 2:
        # If no edge attributes, just add the edge without attributes
        edge_attributes[edge[:2]] = {}
    elif len(edge) == 3:
        # If edge attributes exist, add them to the dictionary
        edge_attributes[edge[:2]] = edge[2]
    else:
        # Handle unexpected edge format
        print("Unexpected edge format:", edge)

# Count the number of colors used
num_colors = len(set(coloring.values()))

# Print extracted data and number of colors used
print("Nodes:", nodes)
print("Edges:", edges)
print("Node Attributes:", node_attributes)
print("Edge Attributes:", edge_attributes)

print("Number of Colors Used:", num_colors)

print("Hamilton paths:", hamilton_paths)

