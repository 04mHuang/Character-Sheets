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
from google_cal import get_credentials

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
    groupmember_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('Groups.group_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)

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
        members = db.session.query(User).join(GroupMember).filter(GroupMember.group_id == group_id).all()
        return render_template('group.html', group=group, members=members)
    else:
        return redirect(url_for('base'))

@app.route('/group/<int:group_id>/add_member', methods=['POST'])
def add_member(group_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = request.form['username']
    user = User.query.filter_by(username=username).first()
    if user:
        new_member = GroupMember(group_id=group_id, user_id=user.user_id)
        db.session.add(new_member)
        db.session.commit()
    
    return redirect(url_for('view_group', group_id=group_id))

@app.route('/group/<int:group_id>/remove_member/<int:user_id>', methods=['POST'])
def remove_member(group_id, user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    member = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
    
    return redirect(url_for('view_group', group_id=group_id))

# use /users to see the tables, just to make sure the sql works with the flask
@app.route('/users')
def show_users():
    logging.info("Displaying users table")
    users = User.query.all()
    groups = Group.query.all()
    people = Person.query.all()
    group_members = GroupMember.query.all()
    return render_template('users.html', users=users, groups=groups, people=people, group_members=group_members)

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
    
@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('base'))
    
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri = "http://localhost:3000",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    code = request.args.get("code")

    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
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
    return redirect(url_for('base'))


# TODO: remove below route used for testing
@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session.get('username', 'Guest')
        return f"Session is active. User ID: {user_id}, Username: {username}"
    else:
        return 'User is not logged in'

if __name__ == '__main__':
    logging.info("Creating database tables...")
    with app.app_context():
        db.create_all()
        logging.info("Starting the server...")
        app.run(debug=True, host='0.0.0.0', port=3000)