from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

# This is the same file your bot uses
TEMPLATES_FILE = "schedule_templates.json"

app = Flask(__name__)
# CORS is required to allow your GitHub Pages site to request data from this server
CORS(app) 

def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    return {}

@app.route('/get_schedule', methods=['GET'])
def get_schedule():
    # The user's ID will be sent as a URL parameter
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    templates = load_templates()
    user_schedule = templates.get(user_id, {}) # Get the schedule or an empty dict
    
    return jsonify(user_schedule)

if __name__ == '__main__':
    # When you deploy this, the host and port will be managed by the hosting service
    app.run(host='0.0.0.0', port=8080)