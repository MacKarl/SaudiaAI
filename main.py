from flask import Flask, request, jsonify
import redis
import json

app = Flask(__name__)

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def serialize_data(data):
    """Serialize data to store in Redis."""
    return json.dumps(data)

def deserialize_data(data):
    """Deserialize data retrieved from Redis."""
    return json.loads(data)

@app.route('/thread/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    """Endpoint to retrieve a thread by ID."""
    data = redis_client.get(thread_id)
    if data is None:
        return jsonify({"error": "Thread not found"}), 404
    return jsonify(deserialize_data(data))

@app.route('/thread/<thread_id>', methods=['POST'])
def create_or_update_thread(thread_id):
    """Endpoint to create or update a thread."""
    data = request.json
    # Validate data here (omitted for brevity)
    
    # Store data in Redis
    redis_client.set(thread_id, serialize_data(data))
    return jsonify({"message": "Thread updated successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
