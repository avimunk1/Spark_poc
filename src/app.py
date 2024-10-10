from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
from main_2 import main as m

app = Flask(__name__)
CORS(app)  # Add this line to enable CORS

localEnv = True 

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

@app.route('/questionandanswers', methods=['POST'])
def trigger_service():
    data = request.json
    logging.info(f"starting process")
    result = run_service(data)
    logging.info(f" result returned to main")
    return Response(result, status=200, mimetype='text/html')

if __name__ == '__main__':
    if localEnv:    
        app.run(host='0.0.0.0', port=5001)
    else:
        app.run(host='0.0.0.0', port=5000)
        print("localEnv is False, running on default port")

