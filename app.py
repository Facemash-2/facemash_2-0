from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
import random

app = Flask(__name__)

# MongoDB connection string (update with your own if needed)
app.config["MONGO_URI"] = "mongodb+srv://ppgame793:CBrHkNaLAPln7GeK@hotornot.gubbic6.mongodb.net/voting_app?retryWrites=true&w=majority&appName=hotornot"
mongo = PyMongo(app)

def convert_to_json_compatible(data):
    if isinstance(data, ObjectId):
        return str(data)  # Convert ObjectId to string
    if isinstance(data, dict):
        return {k: convert_to_json_compatible(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_json_compatible(i) for i in data]
    return data

# Ensure initial candidates have a score of 100000
initial_votes = ["Alice", "Bob", "Charlie"]
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
    data = request.get_json()
    selected_id = data.get("selected_id")

    if not selected_id:
        return jsonify({"status": "error", "message": "Invalid ID"}), 400

    all_candidates = list(mongo.db.votes.find())
    candidate_voted_for = next((c for c in all_candidates if str(c["_id"]) == selected_id), None)

    if not candidate_voted_for:
        return jsonify({"status": "error", "message": "Candidate not found"}), 404

    other_candidate = random.choice([c for c in all_candidates if c["_id"] != candidate_voted_for["_id"]])

    # Increment score for the candidate who received the vote
    mongo.db.votes.update_one(
        {"_id": ObjectId(selected_id)},
        {"$inc": {"count": 1, "score": 1}}
    )

    # Decrement score for the other candidate
    mongo.db.votes.update_one(
        {"_id": ObjectId(other_candidate["_id"])},
        {"$inc": {"score": -1}}
    )

    return jsonify({"status": "success"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Fetch all candidates
    all_candidates = list(mongo.db.votes.find())
    
    # Calculate the total score for calculating likeability percentages
    total_score = sum(candidate["score"] for candidate in all_candidates)
    
    # Add likeability percentage to each candidate
    for candidate in all_candidates:
        if total_score > 0:
            candidate["likeability"] = (candidate["score"] / total_score) * 100
        else:
            candidate["likeability"] = 0
    
    # Sort candidates by score in descending order
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