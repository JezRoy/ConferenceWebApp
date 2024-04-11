from pulp import LpProblem, LpMaximize, LpVariable

# Create a linear programming problem
model = LpProblem(name="Maximize_Profit", sense=LpMaximize)

# Decision variables
x = LpVariable(name="Car_A", lowBound=0)  # Number of cars of type A
y = LpVariable(name="Car_B", lowBound=0)  # Number of cars of type B

# Objective function
model += 20000 * x + 45000 * y, "Total_Profit"

# Constraints
model += 4 * x + 5 * y <= 30, "Designer_Constraint"
model += 3 * x + 6 * y <= 30, "Engineer_Constraint"
model += 2 * x + 7 * y <= 30, "Machine_Constraint"

# Solve the problem
model.solve()

# Print the results
#print("Status:", LpProblem)
print("Optimal Solution:")
print("Car A:", round(x.value()))
print("Car B:", round(y.value()))
print("Total Profit:", model.objective.value())
