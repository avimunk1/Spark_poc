import os
import requests
from requests.auth import HTTPBasicAuth
import hashlib


# Read API key and data center from environment variables
API_KEY = os.environ.get('MAILCHIMP_API_KEY')
DATA_CENTER = os.environ.get('MAILCHIMP_DATA_CENTER')

# Check if environment variables are set
if not API_KEY or not DATA_CENTER:
    raise ValueError("MAILCHIMP_API_KEY and MAILCHIMP_DATA_CENTER must be set as environment variables")
#todo: add this env vearibles to Ec2 PM2

LIST_ID = '370513c0ab'

def getFullContactInfo():
    email = 'tehilix@gmail.com'
        # Hash the email to generate subscriber_hash
    subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

    # API request to retrieve full contact details
    url = f'https://{DATA_CENTER}.api.mailchimp.com/3.0/lists/{LIST_ID}/members/{subscriber_hash}'
    response = requests.get(url, auth=HTTPBasicAuth('anystring', API_KEY))

    if response.status_code == 200:
        contact_data = response.json()
        print(contact_data)  # This will contain all available fields
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_all_tags():
    """Fetch and return all tags from Mailchimp."""
    url = f'https://{DATA_CENTER}.api.mailchimp.com/3.0/lists/{LIST_ID}/tag-search'
    count = 100  # Maximum allowed per page
    offset = 0
    all_tags = []

    # Loop to fetch all tags with pagination
    while True:
        params = {'count': count, 'offset': offset}
        response = requests.get(url, params=params, auth=HTTPBasicAuth('anystring', API_KEY))

        if response.status_code != 200:
            print(f"Failed to retrieve tags: {response.status_code} - {response.text}")
            break

        tags_data = response.json()
        tags = tags_data.get('tags', [])

        if not tags:
            break  # Exit if no more tags are available

        all_tags.extend(tags)  # Collect tags from this page
        offset += count  # Move to the next page

    return all_tags

def get_contacts_by_tag(tag_name):
    """Fetch and print all contacts for a given tag name."""
    url = f'https://{DATA_CENTER}.api.mailchimp.com/3.0/lists/{LIST_ID}/members'
    params = {'tag': tag_name, 'count': 100}  # Use the tag name as a filter

    response = requests.get(url, params=params, auth=HTTPBasicAuth('anystring', API_KEY))

    if response.status_code != 200:
        print(f"Failed to retrieve contacts: {response.status_code} - {response.text}")
        return

    contacts_data = response.json()
    members = contacts_data.get('members', [])

    print(f"Contacts for tag '{tag_name}':")
    for member in members:
        email = member.get('email_address', 'N/A')
        full_name = f"{member.get('merge_fields', {}).get('FNAME', '')} {member.get('merge_fields', {}).get('LNAME', '')}".strip()
        member_tags = [tag['name'] for tag in member.get('tags', [])]

        print(f"- Name: {full_name}, Email: {email}, Tags: {member_tags}")

#getFullContactInfo()

# Main logic to retrieve and filter tags
all_tags = get_all_tags()
print(all_tags)
#print("Tags containing the word 'Be Beauty' (case-insensitive):")
'''
for tag in all_tags:
    if 'Here to Make You Smile' in tag['name'].lower():
        #print(f"- {tag['name']} (ID: {tag['id']})")
        # Use the tag name, not the ID
        get_contacts_by_tag(tag['name'])

'''