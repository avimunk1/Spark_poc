from pydantic import BaseModel
from openai import OpenAI
import logging
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Add logger initialization
logger = logging.getLogger(__name__)

# Get the project root directory and load .env
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH)

# Get the API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client with explicit API key
client = OpenAI(
    api_key=api_key
)

questionsAndAnswers = "question: how are you doing recently? answer: I am doing well"
message = "I am writing to update that i'm doing well"

class MailResults(BaseModel):
    issueDesc: str
    isVerified: bool

def mailVerifed(Questions_and_Answers, emailmessage):
    try:
        systemContent = "You need to verify that the emailmessage generally reflects the user's answers in the questions and answers. If it does, set isVerified=True. If it does not, set isVerified=False and provide issueDesc with a description of why the message is incorrect. Respond in JSON format."
        
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",  
            messages=[
                {"role": "system", "content": systemContent},
                {"role": "user", "content": Questions_and_Answers},
            ],
            response_format=MailResults
        )
        
        # Extract the MailResults object from the completion
        mail_results = completion.choices[0].message.parsed
        
        return mail_results  # Return the parsed MailResults object instead of the whole completion

    except Exception as e:
        logger.error(f"Failed to validate email: {str(e)}")
        return MailResults(
            issueDesc="Validation failed due to technical error",
            isVerified=False
        )

