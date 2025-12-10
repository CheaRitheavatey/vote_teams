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
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", {})
    return data.get("question_blocks", {})

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


def build_full_answer_payload(blocks, answers_dict):
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
    resp = requests.post(
        f"{BASE_URL}/answers/{enter_code}",
        headers=headers,
        json=payload
    )
    return resp
