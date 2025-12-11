# api/vote_runtime.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def fetch_vote_structure(enter_code):
    resp = requests.get(f"{BASE_URL}/vote/{enter_code}", headers=headers)
    print("GET /vote status:", resp.status_code)
    if resp.status_code != 200:
        print("Body:", resp.text)
        return None

    data = resp.json().get("data", {})
    # system uses "question_blocks"
    blocks = data.get("question_blocks", {})
    
    # DEBUG: Print structure to see what fields exist
    print("\n=== DEBUG: Blocks structure ===")
    for b_id, block in blocks.items():
        print(f"Block {b_id}:")
        for q_id, question in block.get("questions", {}).items():
            print(f"  Question {q_id}: {list(question.keys())}")
    print("==============================\n")
    
    return blocks

def get_next_question(blocks, current_block, current_question):
    block_ids = sorted(blocks.keys(), key=lambda x: int(x))
    if current_block not in block_ids:
        return None, None

    q_ids = sorted(blocks[current_block]["questions"].keys(), key=lambda x: int(x))

    if current_question in q_ids:
        idx = q_ids.index(current_question)
        if idx + 1 < len(q_ids):
            return current_block, q_ids[idx + 1]

    b_idx = block_ids.index(current_block)
    if b_idx + 1 < len(block_ids):
        next_block = block_ids[b_idx + 1]
        next_q_ids = sorted(blocks[next_block]["questions"].keys(), key=lambda x: int(x))
        if next_q_ids:
            return next_block, next_q_ids[0]

    return None, None


def build_full_answer_payload(blocks, answers_dict, question_types=None):
    """
    Build payload for submitting answers.
    
    Args:
        blocks: Vote structure from fetch_vote_structure
        answers_dict: {(block_id, q_id): [answer_list]}
        question_types: Optional dict {(block_id, q_id): "QuestionType"} for formatting
    """
    payload_blocks = {}
    for (block_id, q_id), ans_list in answers_dict.items():
        b_id = str(block_id)
        qid = str(q_id)
        if b_id not in payload_blocks:
            payload_blocks[b_id] = {"questions": {}}
        
        payload_blocks[b_id]["questions"][qid] = {
            "answers": [
                {
                    "0": {
                        "0": ans_list
                    }
                }
            ],
            "lang": "DE",
            "skip": False
        }
    return {"blocks": payload_blocks}


def submit_all_answers(enter_code, payload):
    print("\n=== DEBUG: Submitting payload ===")
    import json
    print(json.dumps(payload, indent=2))
    print("=================================\n")
    
    resp = requests.post(
        f"{BASE_URL}/answers/{enter_code}",
        headers=headers,
        json=payload
    )
    print(f"Response status: {resp.status_code}")
    print(f"Response body: {resp.text}")
    return resp



# add another helper to help with label to display the question type
def question_type_label(q):
    qtype = q.get("type", "").upper()
    
    if qtype in ("TEXT", "STRING", "INPUT"):
        return "Text Question"

    if qtype in ("SINGLECHOICE", "SELECTONE", "RADIO"):
        return "Single Choice"

    if qtype in ("MULTICHOICE", "SELECTMULTI", "CHECKBOX"):
        return "Multiple Choice"

    if qtype in ("RANGE", "SLIDER"):
        return "Range / Slider"

    return f"{qtype}"