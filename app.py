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
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_ORGANIZATION_ID"),
)

def query_thread(thread_id):
    """Retrieve a thread from the database by ID."""
    try:
        response = requests.get(f"https://api.openai.com/v1/threads/{thread_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch thread: {e}")
        return None

@app.route('/thread/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    """Endpoint to retrieve a thread by ID."""
    data = query_thread(thread_id)
    if data is None:
        return jsonify({"error": "Thread not found"}), 404
    return jsonify({'thread_id': thread_id, 'data': data})

@app.route('/thread/', methods=['POST'])
def create_or_update_thread():
    """Endpoint to create or update a thread."""
    try:
        thread = client.beta.threads.create()
        thread_id = thread.id
        save_thread(thread_id, thread)
        return jsonify({"thread_id": thread_id}), 200
    except Exception as e:
        logging.error(f"Failed to create/update thread: {e}")
        return jsonify({"error": "Failed to create or update thread"}), 500

@app.route('/response/', methods=['POST'])
def get_response():
    user_text = request.json.get('prompt')
    thread_id = request.json.get('thread_id', None)

    if not thread_id:
        return jsonify({'error': 'Thread ID required'}), 400

    thread = query_thread(thread_id)
    if thread is None:
        return jsonify({'error': 'Thread not found'}), 404

    try:
        # Logic to handle the thread response
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )

        # Run the Thread
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            instructions="Please address the user as an Arabic man from Saudi Arabia. The user has a premium account."
        )
        # Wait for the run to complete
        while run['status'] != "completed":
            time.sleep(0.2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run['id']
            )

        # Get messages
        response = client.beta.threads.messages.list(thread_id=thread_id)
        response_text = next((m['content']['text'] for m in response['data'] if m['role'] == 'assistant'), None)

        return jsonify({"message": response_text if response_text else "No response from assistant"})

    except Exception as e:
        logging.error(f"Error processing response request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=False)  # It's a good practice to turn debug off in production
