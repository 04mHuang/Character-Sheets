from flask import Flask, render_template, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
from flask_migrate import Migrate
from oauthlib.oauth2 import WebApplicationClient
import os
import requests
import json
import logging
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

app.secret_key = os.getenv('SECRET_KEY')

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

client = WebApplicationClient(GOOGLE_CLIENT_ID)

class User(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# When querying in MySQL server, use backticks because Groups is a reserved keyword
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
    birthday = db.Column(db.Date, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    interests = db.Column(db.Text, nullable=True)

    # Many-to-many relationship between People and Group
    groups = db.relationship('Group', secondary='GroupMembers', backref=db.backref('people', lazy='dynamic'))

# Join table
group_members = db.Table('GroupMembers',
    db.Column('person_id', db.Integer, db.ForeignKey('People.person_id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('Groups.group_id'), primary_key=True)
)

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_google_calendar_service(credentials):
    return build('calendar', 'v3', credentials=credentials)

@app.route('/')
@app.route('/base')
def base():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    groups = Group.query.filter_by(user_id=user_id).all()
    return render_template('base.html', groups=groups)

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    group_name = request.form['group_name']
    
    new_group = Group(user_id=user_id, group_name=group_name)
    db.session.add(new_group)
    db.session.commit()
    
    return redirect(url_for('base'))

@app.route('/delete_group/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    group = Group.query.get(group_id)
    if group and group.user_id == session['user_id']:
        db.session.delete(group)
        db.session.commit()
    
    return redirect(url_for('base'))

@app.route('/group/<int:group_id>')
def view_group(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    group = Group.query.get(group_id)
    if group and group.user_id == session['user_id']:
        group_members_data = (
            db.session.query(Person)
            .join(group_members, Person.person_id == group_members.c.person_id)
            .filter(group_members.c.group_id == group_id)
            .all()
        )
        return render_template('group.html', group=group, members=group_members_data)
    else:
        return redirect(url_for('base'))

@app.route('/group/<int:group_id>/add_member', methods=['POST'])
def add_member(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))    
    if request.method == 'POST':
        name = request.form['name']
        existing_person = Person.query.filter_by(name=name).first()
        group = Group.query.get(group_id)
        if existing_person:
            group.people.append(existing_person)
            return redirect(url_for('view_group', group_id=group_id))
        
        # TODO: needs to redirect to character sheet form
        new_person = Person(user_id=session['user_id'], name=name)
        db.session.add(new_person)
        db.session.commit()
        if group and group.user_id == session['user_id']:
            # Add the new person to the group
            group.people.append(new_person)
            db.session.commit()
        
    return redirect(url_for('view_group', group_id=group_id))
    
@app.route('/group/<int:group_id>/remove_member/<int:person_id>', methods=['POST'])
def remove_member(group_id, person_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    group = Group.query.get(group_id)
    person = Person.query.get(person_id)
    group.people.remove(person)
    db.session.commit()
    return redirect(url_for('view_group', group_id=group_id))

@app.route('/person/<int:person_id>')
def view_person(person_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    person = Person.query.get(person_id)
    if person and person.user_id == session['user_id']:
        return render_template('person.html', person=person)
    else:
        return redirect(url_for('base'))
    
@app.route('/person/<int:person_id>/edit', methods=['GET', 'POST'])
def edit_person(person_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    person = Person.query.get(person_id)
    if person and person.user_id == session['user_id']:
        if request.method == 'POST':
            birthday = request.form['birthday']
            if birthday:
                person.birthday = birthday
            else:
                person.birthday = None
            
            allergies = request.form['allergies']
            if allergies:
                person.allergies = allergies
            else:
                person.allergies = None
            
            interests = request.form['interests']
            if interests:
                person.interests = interests
            else:
                person.interests = None
            
            db.session.commit()
            return redirect(url_for('view_person', person_id=person_id))
        return render_template('edit_person.html', person=person)
    else:
        return redirect(url_for('base'))


# use /users to see the tables, just to make sure the sql works with the flask
@app.route('/users')
def show_users():
    logging.info("Displaying users table")
    users = User.query.all()
    groups = Group.query.all()
    people = Person.query.all()
    group_members_data = (
        db.session.query(group_members)
        .select_from(group_members)
        .join(Person, group_members.c.person_id == Person.person_id)
        .join(Group, group_members.c.group_id == Group.group_id)
        .all()
    )

    return render_template('users.html', users=users, groups=groups, people=people, group_members=group_members_data)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return 'Account with this email already exists'
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('base'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            return redirect(url_for('base'))
        else:
            return 'Invalid credentials'

    return render_template('login.html')

@app.route('/google_login', methods=['GET'])
def google_login():
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri="http://localhost:3000/login/callback"
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route("/login/callback")
def callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    session['credentials'] = credentials_to_dict(credentials)

    userinfo_endpoint = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'alt': 'json', 'access_token': credentials.token}
    userinfo_response = requests.get(userinfo_endpoint, params=params)
    userinfo = userinfo_response.json()

    if userinfo.get("email_verified"):
        users_email = userinfo["email"]
        users_name = userinfo["name"]
    else:
        return "User email not available or not verified by Google.", 400

    user = User.query.filter_by(email=users_email).first()
    if not user:
        user = User(
            username=users_name, email=users_email, password="" # You may want to store a dummy password or hash
        )
        db.session.add(user)
        db.session.commit()

    session['user_id'] = user.user_id
    session['username'] = user.username

    return redirect(url_for("base"))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('credentials', None)
    return redirect(url_for('base'))

@app.route('/calendar')
def calendar():
    if 'credentials' not in session:
        return redirect('login')
    credentials = google.oauth2.credentials.Credentials(
        **session['credentials']
    )
    service = get_google_calendar_service(credentials)
    events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    return render_template('calendar.html', events=events)

@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session.get('username', 'Guest')
        return f"Session is active. User ID: {user_id}, Username: {username}"
    else:
        return 'User is not logged in'

def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

if __name__ == '__main__':
    logging.info("Creating database tables...")
    with app.app_context():
        db.create_all()
        logging.info("Starting the server...")
        app.run(debug=True, host='0.0.0.0', port=3000)
