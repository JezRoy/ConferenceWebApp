import pulp
from random import randint, uniform

# Define the problem
model = pulp.LpProblem("Conference_Scheduling", pulp.LpMaximize)

# Parameters
n = 50  # Number of delegates
m = 22   # Number of talks
D = 2  # Number of days
S = 7  # Number of time slots per day
R = 2   # Number of rooms

alpha = 0.6 # Weight for preferences
gamma = 0.3 # Weight for diversity
beta = 0.1 # Weight for minimizing talk repitiions

# Generate random data
preferences = { (i, t): randint(1, 10) for i in range(n) for t in range(m) }
capacities = { r: randint(10, 25) for r in range(R) }
maxTimes = { t: randint(1, D * S * R // m) for t in range(m) }

# Decision variables
x = pulp.LpVariable.dicts("Attendance", (range(n), range(m), range(D), range(S), range(R)), cat='Binary')

'''for t in range(m):
    for d in range(D):
        for s in range(S):
            for r in range(R):
                print("-->", x[t][d][s][r])
                if not isinstance(x[t][d][s][r], pulp.LpVariable):
                    print(f"Data error with variable x[{t}][{d}][{s}][{r}]")'''

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

# Output the results
for t in range(m):
    print(f"Talk {t+1}:")
    for d in range(D):
        for s in range(S):
            for r in range(R):
                attendees = [i+1 for i in range(n) if x[i][t][d][s][r].value() == 1]
                if attendees:
                    print(f"  Day {d+1}, Slot {s+1}, Room {r+1}: Attendees {attendees}")
    print("\n")
