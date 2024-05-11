from flask import Flask, render_template, request, jsonify
from flask import session, redirect, url_for
from flask_pymongo import PyMongo
from bson import ObjectId
import random
from math import pow
from flask_cors import CORS
from datetime import timedelta, datetime
from celery import Celery
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)
K_FACTOR = 32

app.config['EMAIL_HOST'] = 'smtp.gmail.com'  # SMTP server host
app.config['EMAIL_PORT'] = 587  # SMTP server port
app.config['EMAIL_USERNAME'] = '784a35689@gmail.com'  # Your email address
app.config['EMAIL_PASSWORD'] = 'Dante699'  # Your email password
app.config['EMAIL_RECIPIENT'] = 'ooknacx7@duck.com'  # Recipient email address

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


# MongoDB connection string (update with your own if needed)
app.config["MONGO_URI"] = "mongodb+srv://ppgame793:CBrHkNaLAPln7GeK@hotornot.gubbic6.mongodb.net/voting_app?retryWrites=true&w=majority&appName=hotornot"
mongo = PyMongo(app)
app.secret_key = 'x6M`h[V;/cfT(['

# Function to generate a random password
def generate_random_password():
    # Implement password generation logic here (example)
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for _ in range(12))

# Task to update admin password every 24 hours
@celery.task
def update_admin_password():
    new_password = generate_random_password()
    app.config['ADMIN_PASSWORD'] = new_password
    notify_admins(new_password)

# Schedule the task to run every 24 hours
celery.conf.beat_schedule = {
    'update-password-every-24-hours': {
        'task': 'app.update_admin_password',
        'schedule': timedelta(hours=24),
    },
}

def notify_admins(new_password):
    # Email configuration
    sender_email = app.config['EMAIL_USERNAME']
    recipient_email = app.config['EMAIL_RECIPIENT']
    email_password = app.config['EMAIL_PASSWORD']
    
    # Email content
    subject = 'New Admin Password'
    body = f'Your new admin password is: {new_password}'

    # Create a multipart message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject

    # Add body to email
    message.attach(MIMEText(body, 'plain'))

    # Create SMTP session for sending the mail
    server = smtplib.SMTP(app.config['EMAIL_HOST'], app.config['EMAIL_PORT'])
    server.starttls()  # Enable encryption
    server.login(sender_email, email_password)

    # Send mail
    server.sendmail(sender_email, recipient_email, message.as_string())
    server.quit()

# Flask routes
# Admin login route
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.config.get('ADMIN_PASSWORD'):
            session['admin_authenticated'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Incorrect password. Please try again."
    else:
        return render_template('admin_login.html')

# Admin dashboard route
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('admin_authenticated'):
        return render_template('admin_dashboard.html')
    else:
        return redirect(url_for('admin'))

# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin'))



def calculate_expected_outcome(rating_a, rating_b):
    # Calculate the expected outcome for candidate A
    return 1 / (1 + pow(10, (rating_b - rating_a) / 400))
    
    
def convert_to_json_compatible(data):
    if isinstance(data, ObjectId):
        return str(data)  # Convert ObjectId to string
    if isinstance(data, dict):
        return {k: convert_to_json_compatible(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_json_compatible(i) for i in data]
    return data

# Ensure initial candidates have a score of 100000
initial_votes = ["vanshika garg","yutika sehgal","aarshiya kshatri","padmapriya sahu","kritika daga","apurva mahto","aakriti singh","aayushi singh","jhalak patel","pankhudi bajaj","mannat kaur","stuti dubey","priyali trivedi","avanika soni","mahi modi","aastha didwania","presha lamba","himanshi sahu","yukta jangde","lavisha choudhary","niyatee vijaywargiya","snigdha thakur","shreya mishra","soumyata solanki"]
for candidate in initial_votes:
    if not mongo.db.votes.find_one({"name": candidate}):
        mongo.db.votes.insert_one({"name": candidate, "count": 0, "score": 1000})
    else:
        # If the candidate exists but doesn't have a score, initialize it
        mongo.db.votes.update_one(
            {"name": candidate, "score": {"$exists": False}},
            {"$set": {"score": 1000}}
        )
  # Track the last pair to prevent repetition

# Global variable to track the last random pair
last_pair = []

@app.route('/get_random_pair', methods=['GET'])
def get_random_pair():
    global last_pair  # Declare to use the global variable
    all_candidates = list(mongo.db.votes.find())

    # Get a new random pair
    new_pair = random.sample(all_candidates, 2)

    # Regenerate until the new pair isn't the same as the last pair
    while set(candidate["_id"] for candidate in new_pair) == set(candidate["_id"] for candidate in last_pair):
        new_pair = random.sample(all_candidates, 2)

    # Store the new pair as the last pair
    last_pair = new_pair
    random_pair = new_pair

    return jsonify(convert_to_json_compatible(random_pair))


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/vote', methods=['POST'])
def vote():
    try:
        data = request.get_json()

        selected_id = data.get("selected_id")
        rejected_id = data.get("rejected_id")

        selected_candidate = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})
        rejected_candidate = mongo.db.votes.find_one({"_id": ObjectId(rejected_id)})

        # Calculate expected outcomes
        expected_selected = calculate_expected_outcome(
            selected_candidate["score"], 
            rejected_candidate["score"]
        )
        expected_rejected = 1 - expected_selected  # Because one wins, other loses

        # Calculate score changes based on expected outcomes
        score_increment = K_FACTOR * (1 - expected_selected)  # Winner gets increment
        score_decrement = K_FACTOR * expected_selected  # Loser gets decrement

        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {"$inc": {"count": 1}}
        )

        # Update the scores
        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {"$inc": {"score": score_increment}}
        )

        mongo.db.votes.update_one(
            {"_id": ObjectId(rejected_id)},
            {"$inc": {"score": -score_decrement}}  # Decrement for rejected candidate
        )

        return jsonify({"status": "success"})

    except Exception as e:
        app.logger.error(f"Error in /vote endpoint: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Retrieve all candidates from the database
    all_candidates = list(mongo.db.votes.find())
    
    # Sort candidates by their Elo scores in descending order
    sorted_candidates = sorted(all_candidates, key=lambda x: (x["score"], x["count"]), reverse=True)

    # Move candidates with count 0 to the bottom of the leaderboard
    sorted_candidates.sort(key=lambda x: x['count'] == 0)

    # Convert to JSON-compatible format
    return jsonify(convert_to_json_compatible(sorted_candidates))

@app.route('/get_votes', methods=['GET'])
def get_votes():
    # Retrieve all documents from the "votes" collection
    votes = list(mongo.db.votes.find())
    # Convert MongoDB data to a JSON-compatible format
    votes_json = convert_to_json_compatible(votes)
    return jsonify(votes_json)

if __name__ == '__main__':
    app.run(debug=True)
