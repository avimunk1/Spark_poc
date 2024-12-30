from pydantic import BaseModel
from openai import OpenAI
import logging
import os

# Initialize OpenAI client without proxies
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')  # This will get the API key from environment variables
)

questionsAndAnswers = "question: how are you doing recently? answer: I am doing well"
message = "I am writing to update that i'm doing well"

class MailResults(BaseModel):
    issueDesc: str
    isVerified: bool

def mailVerifed(Questions_and_Answers, emailmessage):

    try:
        systemContent = "You need to verify that the emailmessage generally reflects the user's answers in the questions and answers. If it does, set isVerified=True. If it does not, set isVerified=False and provide issueDesc with a description of why the message is incorrect"
        Questions_and_Answers = Questions_and_Answers + emailmessage

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": systemContent},
                {"role": "user", "content": Questions_and_Answers},
            ],
            response_format=MailResults,
        )
        emailText = completion.choices[0].message.parsed
        #print(emailText)
        return MailResults(issueDesc=emailText.issueDesc, isVerified=emailText.isVerified)

    except Exception as e:
        print(e)
        print("failed to get response for validation",e)
        pass

