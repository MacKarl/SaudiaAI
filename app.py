import os
from dotenv import load_dotenv
import time
import logging
from flask import Flask, request, jsonify
import openai
import requests

from db_utils import create_table, save_thread

# Load environment variables
load_dotenv()

# Ensure the table is created before the app starts
create_table()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_ORGANIZATION_ID"),
)

def query_thread(thread_id):
    """Retrieve a thread from the database by ID."""
    logging.info(f"Querying thread with ID: {thread_id}")
    try:
        response = requests.get(f"https://api.openai.com/v1/thread/{thread_id}")
        response.raise_for_status()
        logging.info("Thread retrieved successfully")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to retrieve thread: {e}")
        return None

@app.route('/thread/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    """Endpoint to retrieve a thread by ID."""
    logging.info(f"GET request to retrieve thread ID: {thread_id}")
    data = query_thread(thread_id)
    if data is None:
        logging.warning(f"Thread ID: {thread_id} not found")
        return jsonify({"error": "Thread not found"}), 404
    return jsonify({'thread_id': thread_id, 'data': data})

@app.route('/thread/', methods=['POST'])
def create_or_update_thread():
    """Endpoint to create or update a thread."""
    try:
        logging.info("Creating or updating a thread")
        thread = client.beta.threads.create()
        thread_id = thread.id
        save_thread(thread_id)
        logging.info(f"Thread created or updated with ID: {thread_id}")
        return jsonify({"thread_id": thread_id}), 200
    except Exception as e:
        logging.error(f"Failed to create or update thread: {e}")
        return jsonify({"error": "Failed to create or update thread"}), 500

@app.route('/response/', methods=['POST'])
def get_response():
    user_text = request.json.get('prompt')
    thread_id = request.json.get('thread_id', None)

    if not thread_id:
        logging.warning("Thread ID required but not provided")
        return jsonify({'error': 'Thread ID required'}), 400

    logging.info(f"Handling response for thread ID: {thread_id}")
    thread = query_thread(thread_id)
    if not thread:
        logging.warning(f"Thread ID: {thread_id} not found for response handling. {thread}")
        return jsonify({'error': 'Thread not found'}), 404

    try:
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        logging.info("Message added to thread successfully")

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            instructions="Please address the user as Arabian from Saudi Arabia or UAE. The user has a premium account."
        )
        logging.info("Thread run created and polling started")
        
        while run.status != "completed":
            time.sleep(0.2)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        response = client.beta.threads.messages.list(thread_id=thread_id)
        response_text = [m['content']['text'] for m in response['data'] if m['role'] == 'assistant'][-1]
        
        logging.info("Response retrieved from thread successfully")
        return jsonify({"message": response_text})

    except Exception as e:
        logging.error(f"Error processing response request: {e}")
        return jsonify({"message": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=False)  # It's a good practice to turn debug off in production
