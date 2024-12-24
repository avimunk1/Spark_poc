from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
from main_2 import main as m
import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables at the start
load_dotenv()
app = Flask(__name__)
CORS(app)

# Get API key at startup
MONDAY_API_KEY = os.getenv('MONDAY_API_KEY')
MONDAY_API_KEY='eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQ0OTczNzg5NSwiYWFpIjoxMSwidWlkIjo2MDk4NjI5MCwiaWFkIjoiMjAyNC0xMi0xOFQxODoyNzowNy4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTAzNzQ5NDQsInJnbiI6InVzZTEifQ.qSiBgzitac9pnPIo-tdE4cxB0wQuJPMXKdf3uCqbVIM'

if not MONDAY_API_KEY:
    raise ValueError("MONDAY_API_KEY not found in environment variables")
logging.info(f"Monday.com API key loaded (first 10 chars): {MONDAY_API_KEY[:10]}...")

localEnv = False

def run_service(data):
    logging.info(f"Running the main service")
    data = data.get('text', '')
    if not isinstance(data, str):
        raise ValueError("Expected a string in 'data['text']'")
    mailTxt: str = m(data)
    if not isinstance(mailTxt, str):
        raise ValueError("Expected 'm' function to return a string")
    logging.info(f"returned emailTxt as html")
    return mailTxt

def process_monday_response(data: dict) -> dict:
    """
    Process the Monday.com response to extract business info and Q&A
    """
    if not data or 'qa_pairs' not in data:
        return None
        
    business_info = {
        'name': '',
        'description': '',
        'owner_name': ''
    }
    
    qa_list = []
    
    for qa in data['qa_pairs']:
        # Extract business owner name
        if qa['question'] == 'שם בעל/ת העסק':
            business_info['owner_name'] = qa['answer']
            
        # Extract business description
        elif 'ספרו לנו בבקשה בכמה משפטים מה שלום העסק שלכם' in qa['question']:
            if qa['answer'] and 'businessName:' in qa['answer']:
                business_info['name'] = qa['answer'].replace('businessName:', '').strip()
            else:
                business_info['description'] = qa['answer'] if qa['answer'] else ''
        
        # Skip creation log, status, and empty answers
        if qa['type'] not in ['creation_log', 'status', 'mirror', 'board_relation'] and qa['answer']:
            qa_list.append({
                'question': qa['question'],
                'answer': qa['answer'],
                'type': qa['type']
            })
    
    return {
        'business': business_info,
        'qa_pairs': qa_list
    }

def get_monday_board_and_item_details(item_id: int, api_key: str) -> dict:
    """
    Fetch both board configuration and item details from Monday.com
    """
    API_URL = "https://api.monday.com/v2"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "API-Version": "2024-01"
    }
    
    # Updated query to also fetch board ID
    query = """
    query ($itemId: [ID!]) {
        items(ids: $itemId) {
            id
            name
            board {
                id
                columns {
                    id
                    title
                    type
                }
            }
            column_values {
                id
                text
                value
                type
            }
        }
    }
    """

    variables = {
        "itemId": [str(item_id)]
    }

    try:
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )
        
        # Add debug logging for board ID
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'items' in data['data'] and data['data']['items']:
                board_id = data['data']['items'][0]['board']['id']
                logging.info(f"Board ID from API: {board_id}")
                columns = data['data']['items'][0]['board']['columns']
                logging.info("Available columns in the board:")
                for col in columns:
                    logging.info(f"Column ID: {col['id']}, Title: {col['title']}, Type: {col['type']}")
        
        response.raise_for_status()
        
        data = response.json()
        if 'data' in data and 'items' in data['data'] and data['data']['items']:
            item = data['data']['items'][0]
            board_id = item['board']['id']  # Get the board ID
            columns = {col['id']: col['title'] for col in item['board']['columns']}
            
            qa_pairs = []
            for column_value in item['column_values']:
                if column_value['id'] in columns:
                    qa_pairs.append({
                        'question': columns[column_value['id']],
                        'answer': column_value['text'],
                        'type': column_value['type']
                    })
            
            raw_data = {
                'item_name': item['name'],
                'qa_pairs': qa_pairs,
                'board_id': board_id  # Add board ID to the response
            }
            
            # Process the data to extract business info and relevant Q&A
            processed_data = process_monday_response(raw_data)
            processed_data['board_id'] = board_id  # Add board ID to processed data
            return processed_data
            
        return data
    except Exception as e:
        logging.error(f"Error fetching Monday.com details: {str(e)}")
        return None

def prepare_and_run_service(monday_data: dict) -> str:
    """
    Prepares data from Monday.com API response and runs the service
    """
    if not monday_data or 'business' not in monday_data or 'qa_pairs' not in monday_data:
        raise ValueError("Invalid Monday.com data format")

    # Format the text with Q&A pairs and business description
    formatted_text = ""
    
    # Debug logging
    logging.info("Processing Monday data:")
    logging.info(f"Business info: {monday_data['business']}")
    logging.info(f"Number of QA pairs: {len(monday_data['qa_pairs'])}")
    
    # Add Q&A pairs
    for qa in monday_data['qa_pairs']:
        formatted_text += f"Question: {qa['question']}\n"
        formatted_text += f"Answer: {qa['answer']}\n\n"
        # Debug logging for each QA pair
        logging.info(f"Processing QA: {qa['question']} -> {qa['answer']}")
    
    # Add business description at the end
    business_info = monday_data['business']
    business_desc = business_info.get('description', '').strip()
    if business_desc:
        formatted_text += f"Business Description: {business_desc}\n"
    
    # Debug logging
    logging.info("Final formatted text:")
    logging.info(formatted_text)
    
    # Prepare data for run_service
    data = {'text': formatted_text}
    
    # Call run_service with html_response=False to get data object
    response = m(data.get('text', ''), html_response=False)
    
    # Now you can directly access the message text
    message_text = response['messageText']
    logging.info(f"Message text: {message_text}")
    
    return message_text

def update_monday_item_email(item_id: int, email_content: str, api_key: str, board_id: str) -> bool:
    """
    Update the email content field in Monday.com item
    """
    API_URL = "https://api.monday.com/v2"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "API-Version": "2024-01"
    }
    
    query = """
    mutation ($itemId: ID!, $boardId: ID!, $emailBody: String!) {
        change_simple_column_value(
            item_id: $itemId,
            board_id: $boardId,
            column_id: "long_text_mkkg84hp",
            value: $emailBody
        ) {
            id
        }
    }
    """

    variables = {
        "itemId": str(item_id),
        "boardId": board_id,  # Use the board ID from the API response
        "emailBody": email_content
    }

    try:
        logging.info(f"Sending update to Monday.com for item {item_id} in board {board_id}")
        logging.info(f"Query: {query}")
        logging.info(f"Variables: {variables}")
        
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )
        
        logging.info(f"Monday.com API Response Status: {response.status_code}")
        logging.info(f"Monday.com API Response: {response.text}")
        
        if response.status_code != 200:
            logging.error(f"Failed to update Monday.com item: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if data.get('data', {}).get('change_simple_column_value', {}).get('id'):
            logging.info(f"Successfully updated email content for item {item_id}")
            return True
            
        if 'errors' in data:
            logging.error(f"Monday.com API returned errors: {data['errors']}")
        
        return False
        
    except Exception as e:
        logging.error(f"Error updating Monday.com item: {str(e)}")
        return False

@app.route('/questionandanswers', methods=['POST'])
def trigger_service():
    data = request.json
    logging.info(f"starting process")
    result = run_service(data)
    logging.info(f" result returned to main")
    return Response(result, status=200, mimetype='text/html')

@app.route('/monday-webhook', methods=['POST'])
def monday_webhook():
    try:
        data = request.json
        if 'challenge' in data:
            return jsonify({'challenge': data['challenge']})
            
        if 'event' in data and 'pulseId' in data['event']:
            item_id = data['event']['pulseId']
            monday_data = get_monday_board_and_item_details(item_id, MONDAY_API_KEY)
            
            if monday_data:
                # Generate email content
                email_content = prepare_and_run_service(monday_data)
                logging.info("Generated email content successfully")
                logging.info(f"Email content: {email_content[:200]}...") # Log first 200 chars
                
                # Update Monday.com with the generated email using the board ID from the API
                if update_monday_item_email(item_id, email_content, MONDAY_API_KEY, monday_data['board_id']):
                    logging.info(f"Successfully updated Monday.com item {item_id} with email content")
                else:
                    logging.error(f"Failed to update Monday.com item {item_id} with email content")
            
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logging.error(f"Error processing Monday webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if localEnv:    
        app.run(host='0.0.0.0', port=5001)
    else:
        app.run(host='0.0.0.0', port=5000)
        print("localEnv is False, running on default port")

