from pydantic import BaseModel
from openai import OpenAI
import logging
import os
import json

# Add logger initialization
logger = logging.getLogger(__name__)

# Initialize OpenAI client without proxies
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

questionsAndAnswers = "question: how are you doing recently? answer: I am doing well"
message = "I am writing to update that i'm doing well"

class MailResults(BaseModel):
    issueDesc: str
    isVerified: bool

def mailVerifed(Questions_and_Answers, emailmessage):
    try:
        systemContent = "You need to verify that the emailmessage generally reflects the user's answers in the questions and answers. If it does, set isVerified=True. If it does not, set isVerified=False and provide issueDesc with a description of why the message is incorrect. Respond in JSON format."
        
        completion = client.chat.completions.create(
            model="gpt-4",  # Correct model name
            messages=[
                {"role": "system", "content": systemContent},
                {"role": "user", "content": Questions_and_Answers},
            ],
            response_format={ "type": "json_object" }
        )
        
        response_text = completion.choices[0].message.content
        response_json = json.loads(response_text)
        
        return MailResults(
            issueDesc=response_json.get('issueDesc', ''),
            isVerified=response_json.get('isVerified', False)
        )

    except Exception as e:
        logger.error(f"Failed to validate email: {str(e)}")
        # Return a default MailResults instead of None
        return MailResults(
            issueDesc="Validation failed due to technical error",
            isVerified=False
        )

