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
initial_votes = ["jhalak patel","pankhudi bajaj","mannat kaur","stuti dubey","priyali trivedi","avanika soni","mahi modi","aastha didwania","presha lamba","himanshi sahu","yukta jangde","lavisha choudhary","niyatee vijaywargiya","snigdha thakur","shreya mishra","soumyata solanki"]
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
    random_pair = random.sample(all_candidates, 2)  # Select two random candidates
    return jsonify(convert_to_json_compatible(random_pair))

@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()  # Get the request data
    selected_id = data.get("selected_id")  # Retrieve the selected candidate's ObjectId

    if not selected_id:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400

    try:
        # Find the candidate who received the vote
        candidate_voted_for = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})

        if not candidate_voted_for:
            return jsonify({"status": "error", "message": "Candidate not found"}), 404

        # Randomly select the other candidate from the list (excluding the selected one)
        all_candidates = list(mongo.db.votes.find())
        other_candidate = random.choice([c for c in all_candidates if str(c["_id"]) != selected_id])

        # Calculate expected outcomes for both candidates
        expected_voted_for = calculate_expected_outcome(candidate_voted_for["score"], other_candidate["score"])
        expected_other = 1 - expected_voted_for

        # Update scores using the Elo algorithm
        new_score_voted_for = candidate_voted_for["score"] + K_FACTOR * (1 - expected_voted_for)  # +1 if voted for
        new_score_other = other_candidate["score"] + K_FACTOR * (0 - expected_other)  # -1 for the other candidate

        # Update the count and score in the database
        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {
                "$inc": {"count": 1, "score": new_score_voted_for - candidate_voted_for["score"]}
            }
        )

        mongo.db.votes.update_one(
            {"_id": ObjectId(other_candidate["_id"])},
            {
                "$inc": {"score": new_score_other - other_candidate["score"]}
            }
        )

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Retrieve all candidates from the database
    all_candidates = list(mongo.db.votes.find())
    
    # Get the highest score to calculate relative likeability
    highest_score = max(candidate["score"] for candidate in all_candidates)  # Find the highest Elo score
    
    # Calculate likeability percentage and set it to 0% if count is 0
    for candidate in all_candidates:
        if candidate["count"] == 0:  # If no votes, likeability is 0%
            candidate["likeability"] = 0
        elif highest_score == 0:
            candidate["likeability"] = 0  # Avoid division by zero
        else:
            # Calculate likeability as a percentage of the highest score
            candidate["likeability"] = (candidate["score"] / highest_score) * 100
    
    # Sort candidates by their Elo scores in descending order
    sorted_candidates = sorted(all_candidates, key=lambda x: x["score"], reverse=True)

    # Return the sorted candidates with JSON compatibility
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
