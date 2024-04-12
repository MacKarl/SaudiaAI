import os
from dotenv import load_dotenv
import time
import logging

from flask import Flask, request, jsonify
import redis
import json
import openai


# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


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
    return jsonify({thread_id: deserialize_data(data)})

@app.route('/thread/', methods=['POST'])
def create_or_update_thread(thread_id):
    """Endpoint to create or update a thread."""
    # Validate data here (omitted for brevity)
    thread_object = client.beta.threads.create()
    thread_id = thread_object.id
    # Store data in Redis
    redis_client.set(thread_id, serialize_data(thread_object))
    return jsonify({"thread_id": f"{thread_id}"}), 200


@app.route('/response/', methods=['POST'])
def get_response():
    user_text = request.json.get('prompt')
    thread_id = request.json.get('thread_id')

    if thread_id is not None:
        thread_object = client.beta.threads.create()
        thread_id = thread_object.id
    else:
        return jsonify({'error': 'Bad request'}), 400

    try:
        # Add a message to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )

        # Run the Thread
        run_response = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=os.environ.get("ASSISTANT_ID"),
        )
        run_id = run_response.id

        # Wait for the run to complete
        while run_response.status != "completed":
            run_response = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            time.sleep(0.2)

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
        return jsonify({"message": sorry_msg}), 500



if __name__ == '__main__':
    app.run(debug=True)
