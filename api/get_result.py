import requests
import os
from dotenv import load_dotenv
from api.fetch_question import fetch_question

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# get result
def get_survey_results(enter_code, block_id=0, question_id=0):
    response = requests.get(f"{BASE_URL}/analysis/{enter_code}/blocks/{block_id}/questions/{question_id}", headers=headers)
    print("Results status:", response.status_code)
    
    if response.status_code != 200:
        return "cannot fetch result:" , response.text
        
    
    data = response.json()
    events = data.get("events", [])
    
    if not events:
        return "Not enough responses yet."

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
    
    result_text = []
    result_text.append(f"\nResults for Survey {enter_code}\n")
    result_text.append(f"Question: {question_text}\n")
    print("-----------------------------------\n")

    total_votes = 0
    for idx, opt_text in enumerate(option):
        votes = count.get(str(idx), 0) # if not found return 0
        total_votes += votes
        # print("votes: " , votes)
        # print("total: " , total_votes)
        
        # want to display option : n vote
        result_text.append(f"{opt_text}: {votes} votes\n")

    result_text.append("-----------------------------------\n")
    result_text.append(f"Total responses: {total_votes}\n")
    
    return "\n".join(result_text)


    # print(response.text)


