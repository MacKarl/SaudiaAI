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
    thread = requests.get(f"https://api.openai.com/v1/thread/{thread_id}")
    return thread

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
    thread = client.beta.threads.create()
    thread_id = thread.id
    save_thread(thread_id)
    return jsonify({"thread_id": thread_id}), 200

@app.route('/response/', methods=['POST'])
def get_response():
    user_text = request.json.get('prompt')
    thread_id = request.json.get('thread_id', None)

    if not thread_id:
        return jsonify({'error': 'Thread ID required'}), 400

    thread = query_thread(thread_id)
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404

    try:
        # Logic to handle the thread response
        # Add a message to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        
        # Run the Thread
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread['id'],
            instructions="Please address the user as Jane Doe. The user has a premium account."
            )
        # Wait for the run to complete
        while run.status != "completed":
            time.sleep(0.2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread['id'],
                assistant_id=os.environ.get("ASSISTANT_ID"),
                run_id=run.id
            )

        # Get messages
        response = client.beta.threads.messages.list(thread_id=thread_id)

        # Iterate through the messages in the response
        for message in response.data:
            # Check if the message is from the assistant
            if message.role == 'assistant':
                # Extract the text content from the message
                # Assuming there's only one content per message, hence [0]
                text_content = message.content[0].text.value
                # Update the last assistant message
                response_text = text_content

        return jsonify({"message": response_text})

    except Exception as e:
        sorry_msg = """
        Oops! It seems we've encountered a bit of a hiccup in our digital universe. 
        While I reboot my circuits and recalibrate my algorithms, 
        please take a moment to enjoy the unpredictable beauty of technology. 
        We'll be back on track faster than you can say 'artificial intelligence'!"
        Refresh the page and try again!🤖🔧
        \n\n
        P.S. We are in beta version, so feel free to contact our developers directly via e-mail tech@iiope.org
        """
        logging.error(f"Error processing request: {e}")
        return jsonify({"message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=False)  # It's a good practice to turn debug off in production
