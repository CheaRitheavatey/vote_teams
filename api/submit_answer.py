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


# submit answer
# def submit_answer(enter_code, block_id, question_id, option_index):
#     answer_data = {
#         "blocks": {
#             block_id: {
#                 "questions": {
#                     question_id: {
#                         "answers": [
#                             {
#                                 "0": {
#                                     "0": [
#                                         {"answer": str(option_index), "cond_answer": "string"}
#                                     ]
#                                 }
#                             }
#                         ],
#                         "lang": "DE",
#                         "skip": False
#                     }
#                 }
#             }
#         }
#     }

#     response = requests.post(
#         f"{BASE_URL}/answers/{enter_code}",
#         headers=headers,
#         json=answer_data
#     )
#     print("Submit answer status:", response.status_code)
#     print(response.text)


def submit_answer(enter_code, block_id, question_id, option_indexes):
    # option_indexes is a list of option indices, e.g. ['0'] or ['0','1']

    answers_list = [{"answer": str(idx), "cond_answer": "string"} for idx in option_indexes]

    answer_data = {
        "blocks": {
            str(block_id): {
                "questions": {
                    str(question_id): {
                        "answers": [
                            {
                                "0": {
                                    "0": answers_list
                                }
                            }
                        ],
                        "lang": "DE",
                        "skip": False
                    }
                }
            }
        }
    }

    response = requests.post(
        f"{BASE_URL}/answers/{enter_code}",
        headers=headers,
        json=answer_data
    )
    print("Submit answer status:", response.status_code)
    print(response.text)

    try:
        return response.json()
    except Exception as e:
        print("Error parsing submit answer response:", e)
        return {"status_code": response.status_code, "text": response.text}
    
    
    # helper method
def fetch_vote_structure(enter_code):
    resp = requests.get(f"{BASE_URL}/vote/{enter_code}", headers=headers)
    # print("vote status: " + resp.status_code)
    if resp.status_code != 200:
        print("Failed to fetch vote:", resp.status_code, resp.text)
        return None
    
    data = resp.json().get("data", {})
    return data.get("question_blocks", {})  # returns dict of blocks

# idea: get one question
# get next question
def get_next_question(blocks, current_block, current_question):
    block_ids = sorted(blocks.keys(), key=lambda x: int(x))
    
    if current_block not in block_ids:
        return None, None
    
    q_ids = sorted(blocks[current_block]["questions"].keys(), key=lambda x: int(x))
    # Is there a next question in same block?
    if current_question in q_ids:
        idx = q_ids.index(current_question)
        if idx + 1 < len(q_ids):
            return current_block, q_ids[idx + 1]

    
    b_idx = block_ids.index(current_block)
    if b_idx + 1 < len(block_ids):
        next_block = block_ids[b_idx + 1]
        next_q = sorted(blocks[next_block]["questions"].keys(), key=lambda x: int(x))
        if next_q:
            return next_block, next_q[0]

    return None, None



