import os

""" An installer file that ensures all required modules for the program are installed.
    It also installs all missing modules so that the program can run."""
    
""" This program should be installed on the server, making use of the instructions on
    README.md file."""

requiredModules = [
    "traceback",
    "os",
    "numpy",
    "flask",
    "Flask",
    "flask_login",
    "flask_sqlalchemy",
    "werkzeug.security",
    'datetime',
    'functools',
    'apscheduler',
    'networkx',
]

# Given pip is installed on the machine.
    
# Start installing any modules that are missing.
for mod in requiredModules:
    try:
        exec(f'import {mod}')
    except ImportError:
        print(f"'{mod}' module not found. Installing {mod}.")
        os.system(f"pip3.8 install {mod}")
    
try: # Test pulp is installed
    exec("import pulp")
except: # Install pulp
    print("'pulp' module not found. Installing pulp")
    try:
        os.system("pip3.8 install pulp")
    except:
        os.system("sudo pip3.8 install pulp")
        os.system("sudo pulptest")
        