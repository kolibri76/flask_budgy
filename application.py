import os
from flask import Flask, flash, redirect, render_template, request
#https://pypi.python.org/pypi/Flask-Bootstrap4/4.0.2
from flask_bootstrap import Bootstrap 
from flask_sqlalchemy import SQLAlchemy

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "budgy.db"))

app = Flask(__name__)
app.secret_key = 'Secret key'
Bootstrap(app)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Transactions(db.model):
    trans_id =

if __name__ == "__main__":
    app.run(debug=True)