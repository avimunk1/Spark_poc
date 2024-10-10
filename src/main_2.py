# Description: This script is used to generate an email output based on the user input and system instructions. The user input is combined with the system instructions and sent to the OpenAI API for processing. The response is then parsed to extract the email output details. The email output is saved to an RTF file along with additional content. The script also calls the mailVerified function from the validator.py file to verify the email message against the questions and answers provided.
# the html in s3 here http://sparkpoc1.s3.amazonaws.com/statics/index.html

import os
import logging
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
from validator import mailVerifed

# Constants for file paths
SYSTEM_INSTRUCTIONS_FILE = 'systemInstructions.txt'

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

def email_output_to_html(email_text):
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

def prepare_messages(file_name):
    """Load the system instructions and user input from files."""
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f'File not found: {file_name}')
        raise
    except Exception as e:
        logging.error(f'Error reading file {file_name}: {e}')
        raise


    try:
        with open(file_name, 'w', encoding='utf-8') as rtf_file:
            rtf_file.write(rtf_content)
        logging.info(f'RTF file saved: {file_name}')
    except Exception as e:
        logging.error(f'Error saving RTF file {file_name}: {e}')
        raise

def main(ex_qanda=None):
    """Generate and validate the email output and save it to an RTF file."""
    openai_api_key = get_openai_api_key()
    client = OpenAI(api_key=openai_api_key)

    try:
        system_content = prepare_messages(SYSTEM_INSTRUCTIONS_FILE)
        #user_content = prepare_messages(USER_INPUT_FILE)
        #about_the_business = user_content
        #questions_and_answers = prepare_messages(QA_FILE)
        questions_and_answers = ""
        if ex_qanda:
            questions_and_answers = ex_qanda
            logging.info(f'got Q&A from post')
        user_content = questions_and_answers

        completion = client.beta.chat.completions.parse(
            model='gpt-4o-2024-08-06',
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_content},
            ],
            response_format=EmailOutput,
        )

        email_text = completion.choices[0].message.parsed


        logging.info(f'Is Reliable: {email_text.isReliable}')
        logging.info(f'Is Too Sad: {email_text.isTooSad}')
        logging.info(f'Business Name: {email_text.businessName}')

        email_verified = mailVerifed(questions_and_answers, email_text.messageText)
        logging.info(f'2nd verification: {email_verified.isVerified}')
        if not email_verified.isVerified:
            logging.warning(f'Issue: {email_verified.issueDesc}')
            txt_issue_desc = str(email_verified.issueDesc)

        #if islocal: save_to_rtf(email_text, questions_and_answers, about_the_business, email_verified.isVerified, email_verified.issueDesc)
        #print(email_text,type(email_text))
        html_output = email_output_to_html(email_text)
        return html_output
    except Exception as e:
        logging.error(f'Failed to get response to create email output: {e}')

if __name__ == '__main__':
    main()