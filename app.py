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
initial_votes = ["aakriti singh","aayushi singh","jhalak patel","pankhudi bajaj","mannat kaur","stuti dubey","priyali trivedi","avanika soni","mahi modi","aastha didwania","presha lamba","himanshi sahu","yukta jangde","lavisha choudhary","niyatee vijaywargiya","snigdha thakur","shreya mishra","soumyata solanki"]
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
    data = request.get_json()  # Retrieve the JSON data from the POST request
    selected_id = data.get("selected_id")

    if not selected_id:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400  # Handle invalid ID

    try:
        # Find the voted-for candidate
        candidate_voted_for = mongo.db.votes.find_one({"_id": ObjectId(selected_id)})

        if not candidate_voted_for:
            return jsonify({"status": "error", "message": "Candidate not found"}), 404  # Handle non-existent ID

        # Randomly select the other candidate (excluding the voted-for candidate)
        all_candidates = list(mongo.db.votes.find())
        other_candidate = random.choice([c for c in all_candidates if str(c["_id"]) != selected_id])

        # Calculate expected outcomes for Elo
        expected_voted_for = calculate_expected_outcome(candidate_voted_for["score"], other_candidate["score"])
        expected_other = 1 - expected_voted_for

        # Update scores with Elo adjustments
        score_increment = K_FACTOR * (1 - expected_voted_for)  # Score change for voted-for candidate
        score_decrement = K_FACTOR * (-expected_other)  # Score change for other candidate

        # Update the score for the voted-for candidate
        mongo.db.votes.update_one(
            {"_id": ObjectId(selected_id)},
            {
                "$inc": {"score": score_increment}  # Increment the Elo score
            }
        )

        # Update the score for the other candidate
        mongo.db.votes.update_one(
            {"_id": ObjectId(other_candidate["_id"])},
            {
                "$inc": {"score": score_decrement}  # Decrement the Elo score
            }
        )

        return jsonify({"status": "success"})  # Successful vote

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500  # Error handling
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
