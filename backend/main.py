from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
from flask_migrate import Migrate
from oauthlib.oauth2 import WebApplicationClient
import os
import requests
import json
import logging
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_auth_oauthlib.flow import Flow
import datetime
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

app.secret_key = os.getenv('SECRET_KEY')
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

flow = Flow.from_client_secrets_file(
    client_secrets_file="credentials.json",
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid", 'https://www.googleapis.com/auth/calendar'],
    redirect_uri="http://localhost:3000/callback"
)

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
    nickname = db.Column(db.String(100), nullable=True)
    pronouns = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    relationship = db.Column(db.String(100), nullable=True)  # New field for relationship
    anniversary_title = db.Column(db.String(100), nullable=True)  # New field for anniversary title
    anniversary_date = db.Column(db.Date, nullable=True)  # New field for anniversary date
    likes = db.Column(db.Text, nullable=True)  # Renamed field from interests to likes
    dislikes = db.Column(db.Text, nullable=True)  # New field for dislikes
    allergies = db.Column(db.Text, nullable=True)
    reminders = db.Column(db.Text, nullable=True)
    how_we_met = db.Column(db.Text, nullable=True)
    favorite_memory = db.Column(db.Text, nullable=True)
    recent_updates = db.Column(db.Text, nullable=True)

    # Many-to-many relationship between People and Group
    groups = db.relationship('Group', secondary='GroupMembers', backref=db.backref('people', lazy='dynamic'))

# Join table
group_members = db.Table('GroupMembers',
    db.Column('person_id', db.Integer, db.ForeignKey('People.person_id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('Groups.group_id'), primary_key=True)
)

# Google Calendar API setup

def get_google_calendar_service(credentials):
    return build('calendar', 'v3', credentials=credentials)

@app.route('/')
@app.route('/base')
def base():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = session['username']
    groups = Group.query.filter_by(user_id=user_id).all()
    return render_template('base.html', groups=groups, username=username)

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
    
    name = request.form['name']
    user_id = session['user_id']
    group = Group.query.get(group_id)
    
    if not group or group.user_id != user_id:
        return redirect(url_for('base'))
    
    # Check if the person already exists
    existing_person = Person.query.filter_by(name=name, user_id=user_id).first()
    
    if existing_person:
        if existing_person not in group.people:
            group.people.append(existing_person)
            db.session.commit()
        return redirect(url_for('view_group', group_id=group_id))
    
    # Create a new person
    new_person = Person(user_id=user_id, name=name)
    db.session.add(new_person)
    db.session.commit()
    
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
    if person:
        group.people.remove(person)
        db.session.commit()  # Ensure the group-person relationship is removed
        
        # Additional cleanup if necessary
        # For example, deleting events related to this person in Google Calendar
        
        db.session.delete(person)  # Delete the person from the database
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
    
def delete_previous_anniversary(prev_date, anniversary_title, credentials):
    start_time = datetime.datetime.combine(prev_date, datetime.time.min).isoformat() + 'Z'
    end_time = datetime.datetime.combine(prev_date, datetime.time.max).isoformat() + 'Z'
    service = get_google_calendar_service(credentials)
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_time,
        timeMax=end_time,
        q=anniversary_title,
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    if events_result:
        for event in events_result:
            print(f"Deleting event: {event.get('summary')} (ID: {event.get('id')})")
            service.events().delete(calendarId='primary', eventId=event.get('id')).execute()

def create_anniversary_event(title, date, credentials):
    print("Creating anniversary event===============================================================")
    service = get_google_calendar_service(credentials)
    event = {
        "summary": title,
        "description": "Anniversary reminder from Character Sheets!",
        "start": {
            "date": date.isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "date": date.isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "recurrence": ["RRULE:FREQ=YEARLY"],
        # reminders 1 week before and on the day of the event
        "reminders": {
            "useDefault": False,
            "overrides": [
            {"method": "email", "minutes": 7 * 24 * 60},
            {"method": "email", "minutes": 0},
            ],
        },
    }
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")

@app.route('/edit_person/<int:person_id>', methods=['GET', 'POST'])
def edit_person(person_id):
    person = Person.query.get_or_404(person_id)
    # needed to remove old data from google calendar
    prev_birthday = person.birthday
    prev_anniversary_date = person.anniversary_date
    prev_anniversary_title = person.anniversary_title
    if request.method == 'POST':
        # Ensure all fields are updated correctly
        person.name = request.form['name']
        person.nickname = request.form['nickname'] if request.form['nickname'] else None
        person.pronouns = request.form['pronouns'] if request.form['pronouns'] else None
        person.relationship = request.form['relationship'] if request.form['relationship'] else None
        person.birthday = datetime.datetime.strptime(request.form['birthday'], '%Y-%m-%d').date() if request.form['birthday'] else None
        person.anniversary_title = request.form['anniversary_title'] if request.form['anniversary_title'] else None
        person.anniversary_date = datetime.datetime.strptime(request.form['anniversary_date'], '%Y-%m-%d').date() if request.form['anniversary_date'] else None
        person.likes = request.form['likes'] if request.form['likes'] else None
        person.dislikes = request.form['dislikes'] if request.form['dislikes'] else None
        person.allergies = request.form['allergies'] if request.form['allergies'] else None
        person.reminders = request.form['reminders'] if request.form['reminders'] else None
        person.how_we_met = request.form['how_we_met'] if request.form['how_we_met'] else None
        person.favorite_memory = request.form['favorite_memory'] if request.form['favorite_memory'] else None
        person.recent_updates = request.form['recent_updates'] if request.form['recent_updates'] else None
        
        db.session.commit()

        # Check if user is logged in and has Google Calendar credentials
        if 'credentials' in session:
            try:
                credentials = Credentials(**session['credentials'])
                # Create or update calendar events for birthday and anniversary
                # prevent duplicate events
                if prev_birthday != person.birthday:
                    birthday_title = f"{person.name}'s Birthday"
                    create_anniversary_event(birthday_title, person.birthday, credentials)
                    if prev_birthday is not None:
                        # prevent old events from staying in Google Calendar
                        delete_previous_anniversary(prev_birthday, birthday_title, credentials)
                if prev_anniversary_date != person.anniversary_date or prev_anniversary_title != person.anniversary_title :
                    create_anniversary_event(person.anniversary_title, person.anniversary_date, credentials)
                    if prev_anniversary_date or prev_anniversary_title:
                        # prevent old events from staying in Google Calendar
                        delete_previous_anniversary(prev_anniversary_date, prev_anniversary_title, credentials)
                # Update session credentials
                session['credentials'] = credentials_to_dict(credentials)
            except Exception as e:
                flash(f'An error occurred while creating the event: {str(e)}')
        
        return redirect(url_for('view_person', person_id=person_id))
    
    return render_template('edit_person.html', person=person)



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
            flash('Account with this email already exists', 'danger')
            return redirect(url_for('signup'))
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully', 'success')
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
            flash('Incorrect password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/google_login', methods=['GET'])
def google_login():
    authorization_url, state = flow.authorization_url()
    app.logger.info(f"URL: {authorization_url}")
    app.logger.info(f"Saved state: {state}")
    session['state'] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    state = session.get('state')
    app.logger.info(f"Saved state: {state}")
    if not state:
        return "State mismatch error.", 400
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    session["google_id"] = id_info.get("sub")
    session["email"] = id_info["email"]
    session["name"] = id_info.get("name") or id_info["email"].split('@')[0]
    
    user = User.query.filter_by(email=session["email"]).first()
    if not user:
        user = User(
            username=session["name"], email=session["email"], password="notHashed"  # You may want to store a dummy password or hash
        )
        db.session.add(user)
        db.session.commit()
    session['user_id'] = user.user_id
    session['username'] = user.username
    session['credentials'] = credentials_to_dict(credentials)
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
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    logging.info("Creating database tables...")
    with app.app_context():
        db.create_all()
        logging.info("Starting the server...")
        app.run(debug=True, host='0.0.0.0', port=3000)