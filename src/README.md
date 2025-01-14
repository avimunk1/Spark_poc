```markdown
# SparkIL Micro-Lending Platform - MVP

## Introduction

SparkIL is committed to strengthening the connection between the Jewish diaspora and Israelis through a micro-lending platform. The MVP (Minimum Viable Product) aims to lay the foundation for a scalable infrastructure that supports this mission. A significant focus of the MVP is to replace the manual processes required to update lenders on the progress of businesses they support, transitioning to a more efficient semi-automated system.
The MVP platform will focus on a semi-automated process to keep lenders informed about the businesses they have supported through regular update emails. The key features include:

- **Questionnaire Distribution**: Automates the distribution of surveys to businesses, making it easier to collect updates efficiently.
- **Email Content Generation**: Utilizes Generative AI to create concise and engaging email content based on the responses to questionnaires.
- **Manual Review Process**: Allows SparkIL staff to review the AI-generated content for accuracy, adjust as needed, and distribute the emails smoothly.
- **KPI Tracking**: Implements tools to measure and monitor the effectiveness and usage of the update process.
- **Security Compliance**: Ensures that the platform adheres to information security standards, with a focus on minimizing the storage of sensitive data.

## Proof of Concept (POC)

The current POC demonstrates a "manual" version of the process. In this version, SparkIL employees can manually input questions and answers submitted by the businesses into an HTML file, which is then used to generate the update email content for lenders. This setup is a stepping stone towards full automation.

## Project Structure

```
project/
│
├── src/
│   ├── app.py              # Main Flask application
│   ├── main_2.py           # Python script for OpenAI email generation
│   ├── validator.py        # Validation logic for inputs
│   ├── systemInstructions.txt # Instructions related to system usage
│   ├── statics/            # Static files such as HTML and CSS
│   └── __pycache__/        # Compiled Python files
│
├── requirements.txt        # Dependencies for the project
└── README.md               # Project documentation
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   ```
   
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Flask application**:
   Start the server locally by running the following command:
   ```bash
   python3 src/app.py
2. **run index.html** to set the Q&A recived from the business.  submit the form to send the data to the server and disply the update email.  note the relialbole and validator results. this form is not used for the production enviorment i.e used for testing only.
   ```

2. **Email Generation**:
   The script in `main_2.py` can be used to generate email content using OpenAI. Before running the script, make sure your OpenAI API key is set as an environment variable:
   ```bash
   
   ```

3. **Static Files**:
   Static files, including the HTML forms for data input, are located in the `src/statics/` folder. SparkIL employees use these files to manually input questions and answers submitted by business owners, which are then used to generate update emails.

## System Instructions

Refer to the `src/systemInstructions.txt` file for detailed guidelines on using the system and its key functionalities.

## Requirements

- Python 3.8+
- Flask
- OpenAI API key (for email generation)
- AWS or S3 for file storage (if necessary)
- Monday API key (for monday integration)
- Monday workspace id (for monday integration)
- Moday SDK (for monday integration)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
```

Monday intgreation
to start monday integration:
   1. run the app.py normaly
   2. run Ngrok: ngrok http 5000
   3. use the ngrok url in the monday webhook to create a new webhook: the public ip+ /monday_webhook
   4. add the workspace id and monday API key to the .env file

server usfull commands:
   1. run the service in background: PYTHONPATH=/home/ec2-user/spark_poc/src gunicorn --workers 3 --bind 0.0.0.0:5000 app:app --daemon
   2. To check if gunicorn is running: ps aux | grep gunicorn
   3. To stop the service: pkill gunicorn
   4. check logs: tail -f /home/ec2-user/spark_poc/src/logs/app.log
  
   
