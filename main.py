from website import CreateApp, Scheduler
from multiprocessing import Process

### To be dragged from out of the website folder
# This web app has been created with help from
# https://www.youtube.com/watch?v=dam0GPOAvVI&t=288s&ab_channel=TechWithTim

"""During Development
Set the right python interpreter using:
- cmd+shift+p
- 'python select interpreter'
- python3.8.8 (NOT conda)
"""

### The scheduler will be run in parallel

app = CreateApp()

if __name__ == '__main__':
    parallelScheduler = Process(target=Scheduler)
    app.run(debug=True)