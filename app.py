import os
from dotenv import load_dotenv
import logging
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests

from openai import AsyncOpenAI
from db_utils import create_table, save_thread

# Load environment variables
load_dotenv()

# Ensure the table is created before the app starts
create_table()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_ORGANIZATION_ID"),
)

class ThreadRequest(BaseModel):
    prompt: str
    thread_id: str = None

def serialize_data(data):
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

@app.get("/thread/{thread_id}")
async def get_thread(thread_id: str):
    """Endpoint to retrieve a thread by ID."""
    logging.info(f"GET request to retrieve thread ID: {thread_id}")
    data = query_thread(thread_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"thread_id": thread_id, "data": data}

@app.get("/thread/{thread_id}/messages/")
async def get_messages(thread_id: str):
    logging.info(f"Querying thread messages for ID: {thread_id}")
    try:
        thread_messages = await client.beta.threads.messages.list(thread_id=thread_id)
        logging.info("Thread messages retrieved successfully")
        if not thread_messages.data:
            raise ValueError("No messages found for the thread")
        
        # Assume the logic for processing messages remains the same
        assistant_messages = [msg for msg in thread_messages.data if msg.role == 'assistant']
        last_assistant_message = assistant_messages[0] if assistant_messages else None
        last_assistant_message_text = last_assistant_message.content[0].text.value if last_assistant_message.content else "No content"
        
        return {"full_thread": [msg.to_dict() for msg in thread_messages.data], "the_last_assistant_message": last_assistant_message_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve thread messages")

@app.post("/thread/")
async def create_or_update_thread():
    logging.info("Creating or updating a thread")
    try:
        thread = await client.beta.threads.create()
        thread_id = thread.id
        save_thread(thread_id)
        logging.info(f"Thread created or updated with ID: {thread_id}")
        return {"thread_id": thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create or update thread")

@app.post("/add_message/")
async def get_response(request: Request):
    req = await request.json()
    user_text = req.get('prompt')
    thread_id = req.get('thread_id', None)

    if not thread_id:
        raise HTTPException(status_code=400, detail="Thread ID required")

    logging.info(f"Handling response for thread ID: {thread_id}")
    thread = query_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        message = await client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_text)
        logging.info("Message added to thread successfully")

        run = await client.beta.threads.runs.create_and_poll(assistant_id=os.environ.get("OPENAI_ASSISTANT_ID"), thread_id=thread_id,
                                                             instructions="Please address the user as Arabian from Saudi Arabia or UAE. The user has a premium account.")
        logging.info("Thread run created and polling started")

        while run.status != "completed":
            run = await client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread_id)
            logging.info(run.status)

        response = "Messages have added and run successfully"
        return {"status": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
