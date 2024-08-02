print("Starting Flask application...")

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
import logging

#logging to track when things are happening in the program and make debugging easier
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/main_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Group(db.Model):
    __tablename__ = 'Groups'
    group_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)

class Person(db.Model):
    __tablename__ = 'People'
    person_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    birthday = db.Column(db.Date)
    allergies = db.Column(db.Text)
    interests = db.Column(db.Text)

class GroupMember(db.Model):
    __tablename__ = 'GroupMembers'
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.group_id'), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('People.person_id'), primary_key=True)

@app.route('/')
@app.route('/index')
def index():
    logging.info("Rendering index page")
    return render_template('index.html')

# use /users to see the tables, just to make sure the sql works with the flask
@app.route('/users')
def show_users():
    logging.info("Displaying users table")
    users = User.query.all()
    groups = Group.query.all()
    people = Person.query.all()
    group_members = GroupMember.query.all()
    return render_template('users.html', users=users, groups=groups, people=people, group_members=group_members)

if __name__ == '__main__':
    logging.info("Creating database tables...")
    with app.app_context():
        db.create_all()
        logging.info("Starting the server...")
        app.run(debug=True, host='0.0.0.0', port=3000)