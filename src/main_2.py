# Description: This script is used to generate an email output based on the user input and system instructions. The user input is combined with the system instructions and sent to the OpenAI API for processing. The response is then parsed to extract the email output details. The email output is saved to an RTF file along with additional content. The script also calls the mailVerified function from the validator.py file to verify the email message against the questions and answers provided.
# the html in s3 here http://sparkpoc1.s3.amazonaws.com/statics/index.html

import os
import logging
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
from validator import mailVerifed, MailResults
from pathlib import Path
import json

# Constants for file paths
SYSTEM_INSTRUCTIONS_FILE = 'systemInstructions.txt'

# Configure logging
logger = logging.getLogger(__name__)

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

def email_output_to_html(email_text, email_verified: MailResults):
    """Convert the email output to HTML format."""
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
            }}
            .email-header {{
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .email-section {{
                margin-bottom: 20px;
            }}
            .email-subject, .email-business {{
                font-size: 18px;
            }}
            .email-body {{
                margin-top: 10px;
            }}
            .verification {{
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #ccc;
                background-color: #f8f8f8;
            }}
            .verification-status {{
                font-weight: bold;
                color: {{'green' if email_verified.isVerified else 'red'}};
            }}
        </style>
    </head>
    <body>
        <div class="email-header">Email Output</div>
        <div class="email-section">
            <div class="email-subject">Subject: {email_text.emailSubject}</div>
        </div>
        <div class="email-section">
            <div class="email-body">Message: {email_text.messageText}</div>
        </div>
        <div class="email-section">
            <div>Is Reliable?: {email_text.isReliable}</div>
            <div>Is Too Sad?: {email_text.isTooSad}</div>
        </div>
        <div class="email-section">
            <div class="email-business">Business Name: {email_text.businessName}</div>
        </div>
        <div class="verification">
            <div class="verification-status">Verification Status: {'Verified' if email_verified.isVerified else 'Not Verified'}</div>
            <div>Issue Description: {email_verified.issueDesc if not email_verified.isVerified else 'No issues found'}</div>
        </div>
    </body>
    </html>
    """
    return html_content

class EmailOutput(BaseModel):
    """Pydantic model to define the structure of the email output."""
    emailSubject: str
    messageText: str
    isReliable: bool
    isTooSad: bool
    businessName: str

def get_openai_api_key():
    """Retrieve the OpenAI API key from environment variables or prompt the user."""
    openai_api_key = os.getenv('OPENAI_API_KEY')

    #print(openai_api_key)
    if not openai_api_key:
        logging.error('OpenAI API key not found in environment variables.')
        openai_api_key = input('Please enter your OpenAI API key: ')
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
        else:
            raise ValueError('OpenAI API key is required to proceed.')
    return openai_api_key

def prepare_messages(file_path):
    """Load the system instructions from file."""
    try:
        logger.info(f"Attempting to read file from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            logger.info(f"Successfully read {len(content)} characters from file")
            return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

def m(ex_qanda=None, html_response=True, system_instructions_path=None):
    """
    Generate and validate the email output.
    """
    try:
        if system_instructions_path is None:
            script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            system_instructions_path = str(script_dir / 'systemInstructions.txt')
            
        logger.info(f"Using system instructions path: {system_instructions_path}")
        system_content = prepare_messages(system_instructions_path)
        logger.info("Successfully loaded system instructions")
        
        questions_and_answers = ""
        if ex_qanda:
            questions_and_answers = ex_qanda
            logger.info(f"Using provided Q&A: {questions_and_answers[:200]}...")
            
        user_content = questions_and_answers

        # Initialize OpenAI client
        client = OpenAI()  # This will use OPENAI_API_KEY from environment

        # Updated to use correct OpenAI SDK format without response_format
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": system_content + "\nPlease respond in JSON format with the following structure: {\"emailSubject\": string, \"messageText\": string, \"isReliable\": boolean, \"isTooSad\": boolean, \"businessName\": string}"
                },
                {"role": "user", "content": user_content},
            ]
        )

        # Parse the response
        response_text = completion.choices[0].message.content
        logger.info(f"Raw response from OpenAI: {response_text[:200]}...")  # Log first 200 chars
        
        try:
            email_text = json.loads(response_text)  # Parse JSON response
            logger.info("Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response was: {response_text}")
            raise
        
        # Convert to EmailOutput model
        email_output = EmailOutput(**email_text)

        logging.info(f'Is Reliable: {email_output.isReliable}')
        logging.info(f'Is Too Sad: {email_output.isTooSad}')
        logging.info(f'Business Name: {email_output.businessName}')

        email_verified: MailResults = mailVerifed(questions_and_answers, email_output.messageText)
        logging.info(f'2nd verification: {email_verified.isVerified}')
        if not email_verified.isVerified:
            logging.warning(f'Issue: {email_verified.issueDesc}')

        if html_response:
            return email_output_to_html(email_output, email_verified)
        else:
            return {
                "emailSubject": email_output.emailSubject,
                "messageText": email_output.messageText,
                "isReliable": email_output.isReliable,
                "isTooSad": email_output.isTooSad,
                "businessName": email_output.businessName,
                "verification": {
                    "isVerified": email_verified.isVerified,
                    "issueDesc": email_verified.issueDesc if not email_verified.isVerified else None
                }
            }
    except Exception as e:
        logging.error(f'Failed to get response to create email output: {e}')
        raise

if __name__ == '__main__':
    m()