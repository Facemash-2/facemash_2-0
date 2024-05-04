from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import random
from math import pow
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
K_FACTOR = 32

# MongoDB connection string (update with your own if needed)
app.config["MONGO_URI"] = "mongodb+srv://ppgame793:CBrHkNaLAPln7GeK@hotornot.gubbic6.mongodb.net/voting_app?retryWrites=true&w=majority&appName=hotornot"
mongo = PyMongo(app)

def calculate_expected_outcome_selected(rating_a, rating_b):
    # Calculate the expected outcome for candidate A
    return 1 / (1 + pow(10, (rating_b - rating_a) / 400))
    
def calculate_expected_outcome_rejected(rating_a, rating_b):
    # Calculate the expected outcome for candidate A
    return 1 / (1 + pow(10, (rating_a - rating_b) / 400))
    
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

@app.route('/get_random_pair', methods=['GET'])
def get_random_pair():
    all_candidates = list(mongo.db.votes.find())
    random_pair = random.sample(all_candidates, 2)  # Select two random candidates
    return jsonify(convert_to_json_compatible(random_pair))


@app.route('/vote', methods=['POST'])
def vote():
    try:
        data = request.get_json()  # Get JSON data from the POST request
        selected_id = data.get("selected_id")
        rejected_id = data.get("rejected_id")

        # Validate that both IDs are provided
        if not selected_id or not rejected_id:
            return jsonify({"status": "error", "message": "Selected ID or Rejected ID is missing"}), 400

        # Find the selected candidate in the database
        selected_candidate = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})
        if not selected_candidate:
            return jsonify({"status": "error", "message": "Selected candidate not found"}), 404

        # Find the rejected candidate in the database
        rejected_candidate = mongo.db.votes.find_one({"_id": ObjectId(rejected_id)})
        if not rejected_candidate:
            return jsonify({"status": "error", "message": "Rejected candidate not found"}), 404

        # Calculate expected outcomes for Elo
        expected_selected = calculate_expected_outcome(selected_candidate["score"], rejected_candidate["score"])
        expected_rejected = 1 - expected_selected

        # Score changes based on the Elo system
        score_increment = K_FACTOR * (1 - expected_selected)  # Increment for the selected candidate
        score_decrement = K_FACTOR * expected_rejected  # Decrement for the rejected candidate

        # Update scores in the database
        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {"$inc": {"score": score_increment}}  # Increase the score for selected candidate
        )

        mongo.db.votes.update_one(
            {"_id": ObjectId(rejected_id)},
            {"$inc": {"score": score_decrement}}  # Decrease the score for rejected candidate
        )

        return jsonify({"status": "success"})

    except Exception as e:
        app.logger.error(f"Error in /vote endpoint: {e}")  # Log the error for debugging
        return jsonify({"status": "error", "message": "Internal server error"}), 500  # Handle exceptions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Retrieve all candidates from the database
    all_candidates = list(mongo.db.votes.find())
    
    # Sort candidates by their Elo scores in descending order
    sorted_candidates = sorted(all_candidates, key=lambda x: x["score"], reverse=True)

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
