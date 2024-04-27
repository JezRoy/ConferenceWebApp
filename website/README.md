# ConferenceWebApp

Automatic Generation of Conference Programmes.

The objective of this project is to develop a software system that assists in creating an optimized schedule for a scientific conference. The conference schedule typically includes parallel sessions with related topics and plenary sessions with invited speakers. The challenge is to minimize conflicts in the schedule, ensuring that participants can attend talks of interest without overlapping sessions. The project will involve designing, implementing, and evaluating a web application that allows conference organizers to input schedule and paper information while enabling participants to express their preferences for talks they wish to attend. The software will then generate a conference schedule that minimizes conflicts and possibly optimizes other relevant criteria. The paper "Conference Scheduling - A Personalized Approach" (PATAT 2016) serves as inspiration for this project's development.

## How to Install

This project makes use of a number of Python modules, as listed in the `install.py` file.

1) Ensure Python 3.8.8 & `pip` is installed and configured to run `pip3.8 install <module>`. To install Python, please visit: https://www.python.org/. To install `pip`, please visit: https://pip.pypa.io/en/stable/installation/
2) Once both of the above are installed on the server machine (or relevant computer for development), please run `install.py` to install all necessary dependencies.
3) The project is now ready to be used, ensure all program files, hosted in the repository, reside in an active server in order for the web app to operate.
4) Run one of the files `StandardSchedulerV2.py` or `geneticScheduler.py` - according to preference - each of which start the server on the web app, and click on localhost link that appears to access the application.

## How to Use

Hosts:

* Create a conference,
* Fill in details,
* Add talks / papers to offer,
* Assign topics to talks,
* Assign speakers to talks
* Publish and manage Conference,

Delegates:

* Create an account,
* Find conference,
* Select talks (based on topics)
* Select preference level (if feesible to implement)
* Check Schedule

Setup virtual environment:

`. .venv/bin/activate`
