import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")
ADMIN_PASS = os.getenv("ADMIN_PASS")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}
def create_survey_interactive():
    print("\n--- Create a New Survey ---")

    # 1. EMAIL INPUT (REQUIRED)
    while True:
        email = input("Enter your email (required): ").strip()
        if "@" in email and "." in email:
            break
        print("Please enter a valid email address.")

    # 2. TITLE INPUT
    title = input("Enter survey title: ").strip()
    if not title:
        title = "Untitled Survey"

    # 2. QUESTION INPUT
    question_text = input("Enter your question: ").strip()
    if not question_text:
        question_text = "Untitled Question"

    # 3. CHOICE TYPE (single / multiple)
    print("\nSelect question type:")
    print("1. Single choice (only one answer allowed)")
    print("2. Multiple choice (allow more than one answer)")

    while True:
        q_type = input("Enter 1 or 2: ").strip()
        if q_type == "1":
            question_type = "ChoiceSingle"
            break
        elif q_type == "2":
            question_type = "ChoiceMulti"
            break
        else:
            print("Invalid option. Please enter 1 or 2.")

    # 4. ANSWER OPTIONS
    print("\nEnter answer options one by one.")
    print("Type 'done' when finished.\n")

    options = {}
    index = 0

    while True:
        opt = input(f"Option {index+1}: ").strip()
        if opt.lower() == "done":
            break
        if len(opt) == 0:
            print("Option cannot be empty.")
            continue

        options[str(index)] = {"DE": opt}
        index += 1

    if len(options) == 0:
        print("You must enter at least one option!")
        return

    # 5. Build survey JSON
    survey_data = {
        "data": {
            "module": "Survey",
            "config": {
                "title": {"DE": title},
                "creator": email,
                "public": True,
                "settings": {
                    "editable_answer": True,
                    "full_participation": True,
                    "participation_mode": "UNGUIDED",
                    "participation_val_mode": "COOKIE"
                },
                "analysis_mode": "FREE",
                "structure": {"start": 0, "components": {"0": {"default": -1}}},
                "admin_pw": ADMIN_PASS
            },
            "question_blocks": {
                "0": {
                    "title": {"DE": "Block 1"},
                    "description": {"DE": "User-created block"},
                    "questions": {
                        "0": {
                            "question": {"DE": question_text},
                            "question_type": question_type,
                            "settings": {"mandatory": True, "grid": False},
                            "config": {
                                "option_type": "TEXT",
                                "options": options
                            },
                            "analysis_mode": "FREE"
                        }
                    },
                    "analysis_mode": "FREE",
                    "structure": {"start": 0, "components": {"0": {"default": -1}}}
                }
            }
        }
    }

    # 6. Send to API
    print("\nCreating survey...")

    response = requests.post(f"{BASE_URL}/vote", headers=headers, json=survey_data)

    print("Create survey status:", response.status_code)
    print(response.text)


def create_survey(title, question_text, question_type, options, creator_email):
    survey_data = {
        "data": {
            "module": "Survey",
            "config": {
                "title": {"DE": title},
                "creator": creator_email,
                "public": True,
                "settings": {
                    "editable_answer": True,
                    "full_participation": True,
                    "participation_mode": "UNGUIDED",
                    "participation_val_mode": "COOKIE"
                },
                "analysis_mode": "FREE",
                "structure": {"start": 0, "components": {"0": {"default": -1}}},
                "admin_pw": ADMIN_PASS
            },
            "question_blocks": {
                "0": {
                    "title": {"DE": "Block 1"},
                    "description": {"DE": "User-created block"},
                    "questions": {
                        "0": {
                            "question": {"DE": question_text},
                            "question_type": question_type,
                            "settings": {"mandatory": True, "grid": False},
                            "config": {
                                "option_type": "TEXT",
                                "options": {str(i): {"DE": opt} for i, opt in enumerate(options)}
                            },
                            "analysis_mode": "FREE"
                        }
                    },
                    "analysis_mode": "FREE",
                    "structure": {"start": 0, "components": {"0": {"default": -1}}}
                }
            }
        }
    }

    response = requests.post(f"{BASE_URL}/vote", headers=headers, json=survey_data)

    print("Create survey status:", response.status_code)
    print("Response text:", response.text)

    try:
        data = response.json()
    except Exception as e:
        print("Failed to parse JSON:", e)
        return {}

    return data
