## When running flask, ENSURE YOU ARE DIRECTORY OF APPLICATION.PY
## Run using Cmd use the following commands:
## set FLASK_APP=application.py
## set FLASK_ENV=development
## python -m flask run
## Web App runs on http://127.0.0.1:5000/

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session



