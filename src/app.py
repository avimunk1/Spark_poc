from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
from main_2 import m
import requests
import os
from dotenv import load_dotenv
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from openai import OpenAI
from werkzeug.middleware.proxy_fix import ProxyFix
import jwt
from ipaddress import ip_address, ip_network
from pydantic import ValidationError
from pydantic import BaseModel
from typing import Optional
from validator import MailResults

# Get the project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / '.env'

# Load environment variables
load_dotenv(ENV_PATH)


# Define all environment variables at the top
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MONDAY_API_KEY = os.getenv('MONDAY_API_KEY')
PORT = int(os.getenv('PORT', 5000))
ENV = os.getenv('ENV', 'production')
MONDAY_AID = os.getenv('MONDAY_AID')

# Validate required environment variables
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not MONDAY_API_KEY:
    raise ValueError("MONDAY_API_KEY not found in environment variables")
if not MONDAY_AID:
    raise ValueError("MONDAY_AID not found in environment variables")

app = Flask(__name__)
CORS(app)  # Configure with specific origins in production
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Define paths at the top of the file
APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = APP_ROOT / 'logs'
LOG_FILE_PATH = LOG_DIR / 'app.log'

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger

# Initialize logger
logger = setup_logging()

# Get API key at startup
MONDAY_API_KEY = os.getenv('MONDAY_API_KEY')

if not MONDAY_API_KEY:
    raise ValueError("MONDAY_API_KEY not found in environment variables")


# Define application root
APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_INSTRUCTIONS_PATH = APP_ROOT / 'systemInstructions.txt'
STATIC_FILES_PATH = APP_ROOT / 'statics'
LOG_FILE_PATH = APP_ROOT / 'logs' / 'app.log'

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

# Define your EmailOutput model
class EmailOutput(BaseModel):
    subject: str
    body: str
    business_name: str
    is_reliable: bool = True
    is_too_sad: bool = False

def run_service(data):
    logger.info(f"Running the main service")
    data = data.get('text', '')
    if not isinstance(data, str):
        raise ValueError("Expected a string in 'data['text']'")
    mailTxt: str = m(data)
    if not isinstance(mailTxt, str):
        raise ValueError("Expected 'm' function to return a string")
    logger.info(f"returned emailTxt as html")
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
    
    # Add back the query definition
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
        response = requests.post(API_URL, json={"query": query, "variables": variables}, headers=headers)
        if response.status_code != 200:
            logger.error(f"Monday.com API error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        if 'data' in data and 'items' in data['data'] and data['data']['items']:
            item = data['data']['items'][0]
            board_id = str(item['board']['id'])
            logger.info(f"Board ID from API: {board_id}")
            
            # Create columns mapping
            columns = {col['id']: col['title'] for col in item['board']['columns']}
            
            # Process column values into qa_pairs
            qa_pairs = []
            for column_value in item['column_values']:
                if column_value['id'] in columns:
                    qa_pairs.append({
                        'question': columns[column_value['id']],
                        'answer': column_value['text'],
                        'type': column_value['type']
                    })
            
            # Create the processed data structure
            processed_data = process_monday_response({
                'item_name': item['name'],
                'qa_pairs': qa_pairs,
                'board_id': board_id
            })
            
            # Add board_id to processed data
            processed_data['board_id'] = board_id
            
            logger.info(f"Processing data for item: {item['name']}")
            
            return processed_data
            
    except Exception as e:
        logger.error(f"Error fetching Monday.com details: {str(e)}")
        return None

def prepare_and_run_service(monday_data: dict) -> str:
    try:
        if not monday_data or 'business' not in monday_data or 'qa_pairs' not in monday_data:
            raise ValueError("Invalid Monday.com data format")

        formatted_text = ""
        
        # Debug logging
        logger.info("Processing Monday data:")
        logger.info(f"Business info: {monday_data.get('business', {})}")
        logger.info(f"Number of QA pairs: {len(monday_data.get('qa_pairs', []))}")
        
        # Add Q&A pairs, excluding system fields and duplicates
        seen_questions = set()
        for qa in monday_data.get('qa_pairs', []):
            # Skip unwanted fields
            if (qa['type'] not in ['creation_log', 'status', 'mirror', 'board_relation', 'file', 'link', 'item_id'] and 
                qa['answer'] and 
                isinstance(qa['answer'], str) and
                not qa['answer'].startswith('http')):
                
                # Skip duplicate questions
                if qa['question'] not in seen_questions:
                    seen_questions.add(qa['question'])
                    formatted_text += f"Question: {qa['question']}\n"
                    formatted_text += f"Answer: {qa['answer']}\n\n"
            
        # Add business description at the end
        business_info = monday_data.get('business', {})
        business_desc = business_info.get('description', '').strip()
        if business_desc:
            formatted_text += f"Business Description: {business_desc}\n"
        
        #logger.info("Final formatted text:")
        #logger.info(formatted_text)
        
        # Call m() from main_2.py to handle the OpenAI interaction
        response = m(formatted_text, html_response=False, system_instructions_path=SYSTEM_INSTRUCTIONS_PATH)
        
        if not response:
            logger.error("No response received from main service")
            return "Error: Could not generate email content"
            
        # Response is already a string, just return it
        return response
        
    except Exception as e:
        logger.error(f"Error in prepare_and_run_service: {str(e)}")
        logger.exception("Full stack trace:")
        return f"Error generating email content: {str(e)}"

def update_monday_item_email(item_id: int, email_content: str, api_key: str, board_id: str) -> bool:
    """Update the email content in Monday.com item"""
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
        "boardId": board_id,
        "emailBody": email_content
    }
    
    try:
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to update Monday.com item: {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        if data.get('data', {}).get('change_simple_column_value', {}).get('id'):
            logger.info(f"Successfully updated email content for item {item_id}")
            return True
            
        if 'errors' in data:
            logger.error(f"Monday.com API returned errors: {data['errors']}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating Monday.com item: {str(e)}")
        return False

# Monday.com IP ranges
MONDAY_IP_RANGES = [
    '185.237.4.0/24'  # Covers all IPs we're seeing: 185.237.4.1 through 185.237.4.6
]

def verify_monday_request():
    """Verify that the request comes from Monday.com"""
    try:
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Check if IP is in Monday.com ranges
        is_valid_ip = any(
            ip_address(client_ip) in ip_network(range)
            for range in MONDAY_IP_RANGES
        )
        
        if not is_valid_ip:
            logger.warning(f"Request from unauthorized IP: {client_ip}")
            return False
            
        # Get account_id from the webhook payload
        webhook_data = request.json
        account_id = webhook_data.get('account_id')
        
        #logger.info(f"Webhook data: {webhook_data}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in verify_monday_request: {str(e)}")
        return False

@app.route('/questionandanswers', methods=['POST'])
def trigger_service():
    logger.info(f"Current ENV value: {ENV}")
    if ENV != 'development':
        logger.warning(f"Attempt to access test endpoint in {ENV} environment")
        return jsonify({
            'error': 'This endpoint is only available in development environment'
        }), 403
    
    # Only execute in development
    data = request.json
    logger.info(f"starting process")
    result = run_service(data)
    logger.info(f" result returned to main")
    return Response(result, status=200, mimetype='text/html')

@app.route('/monday-webhook', methods=['POST', 'PUT', 'OPTIONS'])
def monday_webhook():
    if request.method == 'OPTIONS':
        return '', 200
        
    # Skip verification for challenge requests
    if request.is_json and 'challenge' in request.json:
        return jsonify({'challenge': request.json['challenge']})
        
    # Verify the request
    if not verify_monday_request():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # If verification passes, continue with the rest of your webhook code
    try:
        logger.info(f"Request method: {request.method}")
        
        if request.method not in ['POST', 'PUT']:
            logger.error(f"Invalid method: {request.method}")
            return jsonify({'error': 'Method not allowed'}), 405
        
        logger.info("WEBHOOK RECEIVED")
        
        # Get the raw data first
        raw_data = request.get_data(as_text=True)
        
        # Try to parse JSON
        data = request.json
        
        # Handle challenge request
        if 'challenge' in data:
            challenge = data['challenge']
            logger.info(f"Challenge received: {challenge}")
            response = {'challenge': challenge}
            logger.info(f"Sending challenge response: {response}")
            return jsonify(response)
        
        # Handle normal webhook
        if 'event' in data and 'pulseId' in data['event']:
            item_id = data['event']['pulseId']
            monday_data = get_monday_board_and_item_details(item_id, MONDAY_API_KEY)
            
            if monday_data:
                email_content = prepare_and_run_service(monday_data)
                logger.info("Email generated successfully")
                
                if update_monday_item_email(item_id, email_content, MONDAY_API_KEY, monday_data['board_id']):
                    logger.info(f"Updated Monday.com item {item_id}")
                else:
                    logger.error(f"Failed to update Monday.com item {item_id}")
            
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}")
        logger.exception("Full stack trace:")  # This will log the full stack trace
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AWS for future monitoring"""
    try:
        # Check if we can read system instructions
        if not os.path.exists(SYSTEM_INSTRUCTIONS_PATH):
            return jsonify({
                'status': 'error',
                'message': 'System instructions file not found'
            }), 500

        # Check OpenAI API connection
        client = OpenAI()
        client.models.list()

        return jsonify({
            'status': 'healthy',
            'environment': ENV,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    if ENV == 'development':    
        port = 5001
    else:
        port = 5000
    
    app.run(host='0.0.0.0', port=port)
    print(f"Running in {ENV} mode on port {port}")

