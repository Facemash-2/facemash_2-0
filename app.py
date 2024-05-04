from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import random

# Initialize Flask
app = Flask(__name__)

# Initialize Firebase Admin with the service account key
cred = credentials.Certificate("static/key.json")
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()
# Ensure initial candidates have a score of 100000
initial_candidates = ["test","jhalak patel","pankhudi bajaj","mannat kaur","stuti dubey","priyali trivedi","avanika soni","mahi modi","aastha didwania","presha lamba","himanshi sahu","yukta jangde","lavisha choudhary","niyatee vijaywargiya","snigdha thakur","shreya mishra","soumyata solanki"]
# Ensure initial candidates are in Firestore
for candidate in initial_candidates:
    doc_ref = db.collection("votes").document(candidate)
    if not doc_ref.get().exists:
        doc_ref.set({"id":len(initial_candidates)+1,"name": candidate, "count": 0, "score": 1000})  # Initial score of 1000

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_random_pair', methods=['GET'])
def get_random_pair():
    all_candidates = list(db.collection("votes").stream())
    random_pair = random.sample(all_candidates, 2)
    return jsonify([doc.to_dict() for doc in random_pair])


@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    selected_id = data.get("selected_id")
    rejected_id = data.get("rejected_id")

    if selected_id and rejected_id:
        selected_ref = db.collection("votes").document(selected_id)
        rejected_ref = db.collection("votes").document(rejected_id)

        # Update count and score for selected and rejected
        selected_ref.update({"count": firestore.Increment(1), "score": firestore.Increment(1)})
        rejected_ref.update({"score": firestore.Increment(-1)})

        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid IDs"}), 400

@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    # Get all documents from the "votes" collection
    all_candidates = list(db.collection("votes").stream())
    
    # Find the maximum score among all candidates
    max_score = max([doc.to_dict()['score'] for doc in all_candidates])

    # Create the leaderboard with percentage calculations
    leaderboard = []
    for candidate in all_candidates:
        candidate_data = candidate.to_dict()
        
        # Calculate the percentage based on the max score
        if max_score > 0:
            candidate_data['percentage'] = (candidate_data['score'] / max_score) * 100
        else:
            candidate_data['percentage'] = 0  # Handle case where max score is non-positive

        leaderboard.append(candidate_data)

    return jsonify(leaderboard)
if __name__ == '__main__':
    app.run(debug=True)