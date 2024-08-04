print("Starting Flask application...")

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from waitress import serve
from flask_migrate import Migrate
import logging

#logging to track when things are happening in the program and make debugging easier
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# TODO: Change this to a secure secret key
app.secret_key = 'your_secret_key'

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/main_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.user_id
            # TODO: verify if username in session is needed
            session['username'] = user.username
            return redirect(url_for('base'))
        else:
            # TODO: redirect to proper template
            return 'Invalid username or password'
    return render_template('login.html')

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