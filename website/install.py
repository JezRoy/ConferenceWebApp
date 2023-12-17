import os
import sys
import urllib

""" An installer file that ensures all required modules for the program are installed.
    It also installs all missing modules so that the program can run."""
    
""" This program should be installed on the server, making use of the instructions on
    README.md file."""

requiredModules = [
    "traceback",
    "os",
    "numpy",
    "flask",
    "sqlite3",
    "Flask"
]

# Given pip is installed on the machine.
    
# Start installing any modules that are missing.
for mod in requiredModules:
    try:
        exec(f'import {mod}')
    except ImportError:
        print(f"{mod} module not found. Installing {mod}.")
        os.system(f"pip3.10 install {mod}")