import requests
import os
from dotenv import load_dotenv
from fetch_question import fetch_question, fetch_surveys
from submit_answer import submit_answer
from create_survey import create_survey

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def interactive_vote():
    enter_code = input("Enter survey code: ").strip()
    block_id = "0"
    question_id = "0"

    data = fetch_question(enter_code, block_id, question_id)
    if not data:
        return

    # show question and option
    question_text = data["question"]["DE"]
    options = [v["DE"] for k, v in data["config"]["options"].items()]
    print(f"Question: {question_text}")
    for i, opt in enumerate(options):
        print(f"{i}. {opt}")

    # user choose option index
    while True:
        try:
            choice = int(input("Enter your choice number (option ID): "))
            if 0 <= choice < len(options):
                break
            else:
                print("Invalid option number. Try again.")
        except ValueError:
            print("Please enter a valid integer.")

    submit_answer(enter_code, block_id, question_id, choice)

# get result
def get_survey_results(enter_code, block_id=0, question_id=0):
    response = requests.get(f"{BASE_URL}/analysis/{enter_code}/blocks/{block_id}/questions/{question_id}", headers=headers)
    print("Results status:", response.status_code)
    
    if response.status_code != 200:
        print("cannot fetch result:" , response.text)
        return
    
    data = response.json()
    events = data.get("events", [])
    
    if not events:
        print("Not enough responses yet.")
        return

    # count vote
    count = {}
    for event in events:
        content = event.get("content", {})
        answer = (
            content.get("answer", {})
            .get("0", {})
            .get("0", [{}])[0]
            .get("answer")
        )
        if answer is not None:
            if answer in count:
                current_vote = count[answer]
                new_vote = current_vote + 1
                count[answer] = new_vote
            else:
                count[answer] = 1
            # count[answer] = count.get(answer, 0) + 1
            # print(count)

    # fetch question to display info 
    q = fetch_question(enter_code, block_id, question_id)
    
    option = [v["DE"] for k, v in q["config"]["options"].items()]
    question_text = q["question"]["DE"]

    print(f"\nResults for Survey {enter_code}")
    print(f"Question: {question_text}")
    print("-----------------------------------")

    total_votes = 0
    for idx, opt_text in enumerate(option):
        votes = count.get(str(idx), 0) # if not found return 0
        total_votes += votes
        # print("votes: " , votes)
        # print("total: " , total_votes)
        
        # want to display option : n vote
        print(f"{opt_text}: {votes} votes")

    print("-----------------------------------")
    print(f"Total responses: {total_votes}")


    # print(response.text)


if __name__ == "__main__":
    while True:
        print("\n1. Fetch Surveys")
        print("2. Create Survey")
        print("3. Submit Answer")
        print("4. Get Results")
        print("5. Quit")
        choice = input("Choose an option: ")

        if choice == "1":
            fetch_surveys()
        elif choice == "2":
            create_survey()
        elif choice == "3":
            interactive_vote()
        elif choice == "4":
            code = input("Enter survey code: ")
            get_survey_results(code,block_id=0,question_id=0)
        elif choice == "5":
            break
        else:
            print("Invalid choice. Try again.")
