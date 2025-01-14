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

# Define the EmailOutput model
class EmailOutput(BaseModel):
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
        client = OpenAI()

        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": system_content
                },
                {"role": "user", "content": user_content},
            ],
            response_format=EmailOutput
        )
        
        # Get the JSON string
        email_output_str = completion.choices[0].message.content
        
        # Use model_validate_json instead of parse_raw
        email_output = EmailOutput.model_validate_json(email_output_str)
        
        # Now verify with the parsed model
        email_verified = mailVerifed(questions_and_answers, email_output.messageText)
        print("==========check this =============================")
        print("this is the email output", email_verified)
        #todo: add the output from vaildator to monday and remove this print
        logger.info(f"Email verification result: {email_verified.isVerified}")

        if html_response:
            return email_output_to_html(email_output, email_verified)
        else:
            return email_output.messageText
            
    except Exception as e:
        logger.error(f"Error in m(): {str(e)}")
        logger.error(f"Full error details: {e.__class__.__name__}: {str(e)}")
        raise

if __name__ == '__main__':
    m()