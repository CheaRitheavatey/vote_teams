import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}
# get questiion and answer
def fetch_question(enter_code, block_id, question_id):
    response = requests.get(
        f"{BASE_URL}/vote/{enter_code}/blocks/{block_id}/questions/{question_id}",
        headers=headers
    )
    if response.status_code != 200:
        print("Failed to fetch question:", response.status_code, response.text)
        return None
    return response.json()["data"]


# fetch survey list
def fetch_survey_list():
    """Returns a list of survey objects"""
    surveys_list = []
    response = requests.get(f"{BASE_URL}/vote/", headers=headers)
    if response.status_code == 200:
        surveys = response.json()
        for key, survey in surveys.items():
            title = (survey.get("title") or {}).get("DE", "No title")
            enter_code = survey.get("enter_code", "N/A")
            surveys_list.append({
                "title": title,
                "enter_code": enter_code
            })
    return surveys_list


# fetch survye
def fetch_surveys():
    data = []
    response = requests.get(f"{BASE_URL}/vote/", headers=headers)
    if response.status_code == 200:
        surveys = response.json()
        for key, survey in surveys.items():
            title = (survey.get("title") or {}).get("DE", "No title")
            description = (survey.get("description") or {}).get("DE", "No description")
            enter_code = survey.get("enter_code", "N/A")
            data.append(f"Title: {title}\n")
            data.append(f"Description: {description}\n")
            data.append(f"Enter Code: {enter_code}\n")
            data.append("---\n")
    else:
        data.append("Failed to fetch surveys: ", response.status_code, response.text + "\n")
    return "\n".join(data)
