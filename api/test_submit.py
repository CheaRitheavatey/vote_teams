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
    # Your system uses "question_blocks"
    blocks = data.get("question_blocks", {})
    return blocks

def get_next_question(blocks, current_block, current_question):
    block_ids = sorted(blocks.keys(), key=lambda x: int(x))

    # ensure current block exists
    if current_block not in block_ids:
        return None, None

    q_ids = sorted(blocks[current_block]["questions"].keys(), key=lambda x: int(x))

    # Is there a next question in same block?
    if current_question in q_ids:
        idx = q_ids.index(current_question)
        if idx + 1 < len(q_ids):
            return current_block, q_ids[idx + 1]

    # Move to next block
    b_idx = block_ids.index(current_block)
    if b_idx + 1 < len(block_ids):
        next_block = block_ids[b_idx + 1]
        next_q_ids = sorted(blocks[next_block]["questions"].keys(), key=lambda x: int(x))
        if next_q_ids:
            return next_block, next_q_ids[0]

    return None, None

def ask_for_answer(question: dict):
    q_text = question.get("question", {}).get("DE") or question.get("question", {}).get("EN") or ""
    q_type = question.get("question_type") or question.get("questionType")
    config = question.get("config", {})

    print("\n-------------------------")
    print(f"{q_type}: {q_text}")

    # Choice questions
    if q_type in ["ChoiceSingle", "ChoiceMulti"]:
        options_cfg = config.get("options", {})
        options = [v.get("DE") or v.get("EN") or f"Opt {k}" for k, v in options_cfg.items()]
        for i, opt in enumerate(options):
            print(f"{i}. {opt}")

        while True:
            raw = input("Enter option index (multi: 0,2,...): ").strip()
            try:
                if q_type == "ChoiceMulti":
                    idxs = [int(x) for x in raw.split(",") if x.strip() != ""]
                    if not idxs:
                        print("Enter at least one index.")
                        continue
                    return [{"answer": str(i), "condanswer": "string"} for i in idxs]
                else:
                    idx = int(raw)
                    if idx < 0 or idx >= len(options):
                        print("Index out of range.")
                        continue
                    return [{"answer": {"value": str(i)}, "condanswer": {}} for i in idxs]
            except ValueError:
                print("Please enter valid integer indices.")

    # Range questions
    elif q_type in ["RangeRating", "RangeSlider"]:
        while True:
            raw = input("Enter numeric value: ").strip()
            try:
                num = float(raw)
                return [{"answer": {"value": str(num)}, "condanswer": {}}]
            except ValueError:
                print("Enter a valid number.")

    # Text questions
    elif q_type == "TextQuestion":
        txt = input("Enter your text answer: ")
        return [{"answer": txt, "condanswer": "string"}]

    # Fallback
    else:
        print("Unsupported question type, skipping.")
        return None

def build_full_answer_payload(blocks, answers_dict):
    payload_blocks = {}

    for (block_id, q_id), ans_list in answers_dict.items():
        b_id = str(block_id)
        qid = str(q_id)

        if b_id not in payload_blocks:
            payload_blocks[b_id] = {"questions": {}}
            
        payload_blocks[b_id]["questions"][qid] = {
            "answers": ans_list,
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
    print("\nSubmit status:", resp.status_code)
    print("Body:", resp.text)
    return resp

def interactive_full_vote():

    enter_code = input("Enter survey code: ").strip()

    blocks = fetch_vote_structure(enter_code)
    if not blocks:
        print("No blocks found.")
        return

    # Start with the first block & first question
    block_ids = sorted(blocks.keys(), key=lambda x: int(x))
    current_block = block_ids[0]
    q_ids = sorted(blocks[current_block]["questions"].keys(), key=lambda x: int(x))
    current_question = q_ids[0]

    # Dictionary to store all answers before sending:
    # key: (block_id, question_id), value: list[ {answer, condanswer} ]
    user_answers = {}

    while current_block is not None and current_question is not None:
        question = blocks[current_block]["questions"][current_question]
        ans_list = ask_for_answer(question)
        if ans_list is not None:
            user_answers[(current_block, current_question)] = ans_list

        # find next question
        current_block, current_question = get_next_question(blocks, current_block, current_question)

    print("\nAll questions answered. Building payload...")
    payload = build_full_answer_payload(blocks, user_answers)
    print("Final payload:", payload)

    submit_all_answers(enter_code, payload)

if __name__ == "__main__":
    interactive_full_vote()
