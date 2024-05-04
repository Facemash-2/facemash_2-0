from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import random
from math import pow

app = Flask(__name__)
K_FACTOR = 32

# MongoDB connection string (update with your own if needed)
app.config["MONGO_URI"] = "mongodb+srv://ppgame793:CBrHkNaLAPln7GeK@hotornot.gubbic6.mongodb.net/voting_app?retryWrites=true&w=majority&appName=hotornot"
mongo = PyMongo(app)

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


@app.route('/get_random_pair', methods=['GET'])
def get_random_pair():
    all_candidates = list(mongo.db.votes.find())
    if len(all_candidates) < 2:
        return jsonify({"error": "Not enough candidates"}), 400

    # Ensure two unique candidates are chosen
    random_pair = random.sample(all_candidates, 2)
    return jsonify([convert_to_json_compatible(random_pair[0]), convert_to_json_compatible(random_pair[1])])


@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    selected_id = data.get("selected_id")

    if not selected_id:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400

    # Find the candidate who was voted for
    voted_candidate = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})

    # Ensure that the selected candidate exists
    if not voted_candidate:
        return jsonify({"status": "error", "message": "Candidate not found"}), 404

    # Find all other candidates excluding the voted candidate
    all_candidates = list(mongo.db.votes.find({"_id": {"$ne": ObjectId(selected_id)}}))

    if not all_candidates:
        return jsonify({"status": "error", "message": "No other candidates to compare against"}), 400

    # Randomly select another candidate from the remaining list
    other_candidate = random.choice(all_candidates)

    # Calculate expected outcomes
    expected_voted = calculate_expected_outcome(voted_candidate["score"], other_candidate["score"])
    expected_other = 1 - expected_voted

    # Calculate score changes
    increment = K_FACTOR * (1 - expected_voted)  # Voted candidate
    decrement = K_FACTOR * (0 - expected_other)  # Other candidate

    # Update scores in the database
    mongo.db.votes.update_one({"_id": ObjectId(selected_id)}, {"$inc": {"score": increment}})
    mongo.db.votes.update_one({"_id": ObjectId(other_candidate["_id"])}, {"$inc": {"score": decrement}})

    return jsonify({"status": "success"})
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
