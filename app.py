import os
from dotenv import load_dotenv
import time
import logging
from flask import Flask, request, jsonify
import openai
import requests
import json

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

def serelize_data(data):
    """Serialize the data to JSON."""
    return json.dumps(data)

def query_thread(thread_id):
    """Retrieve a thread from the database by ID."""
    logging.info(f"Querying thread with ID: {thread_id}")
    try:
        response = requests.get(f"https://api.openai.com/v1/thread/{thread_id}")
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

@app.route('/thread/<thread_id>/messages/', methods=['GET'])
def get_messages(thread_id):
    logging.info(f"Querying thread with ID: {thread_id}")
    try:
        thread_messages = client.beta.threads.messages.list(thread_id=thread_id)
        logging.info("Thread messages retrieved successfully")
        if not thread_messages.data:
            raise ValueError("No messages found for the thread")

        # Assuming thread_messages.data is a list and the last message is the last element
        """
        last_msg_id = thread_messages.data[-1].id  # Changed from dictionary access to attribute access
        last_msg = client.beta.threads.messages.retrieve(message_id=last_msg_id, thread_id=thread_id)

        last_message_text = last_msg.content[0].text.value if last_msg.content else "No content"
        """
        assistant_messages = [msg for msg in thread_messages.data if msg.role == 'assistant']
        last_assistant_message = assistant_messages[0] if assistant_messages else None
        last_assistant_message_text = last_assistant_message.content[0].text.value if last_assistant_message.content else "No content"
        
        # Changed access to properties of the last_msg object

        return jsonify({
            "full_thread": [msg.to_dict() for msg in thread_messages.data],  # Assuming there's a method to convert each Message object to a dictionary
            "the_last_assistant_message": last_assistant_message_text
        }), 200
    except Exception as e:
        logging.error(f"Failed to retrieve thread messages: {e}")
        return jsonify({"error": "Failed to retrieve thread messages"}), 500


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

@app.route('/add_message/', methods=['POST'])
def get_response():
    user_text = request.json.get('prompt')
    thread_id = request.json.get('thread_id', None)

    if not thread_id:
        logging.warning("Thread ID required but not provided")
        return jsonify({'error': 'Thread ID required'}), 400

    logging.info(f"Handling response for thread ID: {thread_id}")
    thread = query_thread(thread_id)
    if not thread:
        logging.warning(f"Thread ID: {thread_id} not found for response handling")
        return jsonify({'error': 'Thread not found'}), 404

    try:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        logging.info("Message added to thread successfully")

        run = client.beta.threads.runs.create_and_poll(
            assistant_id=os.environ.get("OPENAI_ASSISTANT_ID"),
            thread_id=thread_id,
            instructions="Please address the user as Arabian from Saudi Arabia or UAE. The user has a premium account."
        )
        logging.info("Thread run created and polling started")
        
        while run.status != "completed":
            time.sleep(0.2)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run['id'])

        # Get messages
        response = "Messages have added and run successfully" #get_messages(thread_id) #client.beta.threads.messages.list(thread_id=thread_id)
        """
        last_msg = client.beta.threads.messages.retrieve(message_id=response.last_id, thread_id=thread_id,)
        
        serelized_response = serelize_data(response)
        
        
        last_msg = client.beta.threads.messages.retrieve(message_id=response.last_id, thread_id=thread_id)
        
        response_text = last_msg.content[0].text.value
        
        # Iterate through the messages in the response
        for message in response.data:
            # Check if the message is from the assistant
            if message.role == 'assistant':
                # Extract the text content from the message
                # Assuming there's only one content per message, hence [0]
                text_content = message.content[0].text.value
                # Update the last assistant message
                response_text = text_content
                break
        """
        return jsonify({"status": response}), 201

    except Exception as e:
        logging.error(f"Error processing response request: {e}")
        return jsonify({"message": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=False)  # It's a good practice to turn debug off in production
