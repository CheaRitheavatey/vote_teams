import os
import requests
from dotenv import load_dotenv

from api.fetch_question import fetch_question
from api.submit_answer import fetch_vote_structure

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}


def get_survey_results(enter_code, block_id=0, question_id=0):
    response = requests.get(
        f"{BASE_URL}/analysis/{enter_code}/blocks/{block_id}/questions/{question_id}",
        headers=headers
    )
    print("Results status:", response.status_code)

    if response.status_code != 200:
        return f"cannot fetch result: {response.status_code} {response.text}"

    data = response.json()
    events = data.get("events", [])
    if not events:
        return "Not enough responses yet."

    # Question meta
    q = fetch_question(enter_code, block_id, question_id)
    question_text = q["question"]["DE"]
    q_type = q.get("question_type")

    # Extract raw answers once
    raw_answers = []
    for event in events:
        content = event.get("content", {})
        ans = (
            content.get("answer", {})
            .get("0", {})
            .get("0", [{}])[0]
            .get("answer")
        )
        if ans is not None:
            raw_answers.append(ans)

    # Choice questions (single/multi) -> count per option index
    if q_type and q_type.startswith("Choice"):
        options_cfg = q.get("config", {}).get("options", {})
        option_labels = [v["DE"] for _, v in options_cfg.items()]

        counts = {}
        for ans in raw_answers:
            counts[ans] = counts.get(ans, 0) + 1

        result_lines = [
            f"\nResults for Survey {enter_code}",
            f"Block: {block_id}",
            f"Question: {question_text}",
            "-----------------------------------",
        ]

        total_votes = 0
        for idx, opt_text in enumerate(option_labels):
            votes = counts.get(str(idx), 0)
            total_votes += votes
            result_lines.append(f"{opt_text}: {votes} votes")

        result_lines.append("-----------------------------------")
        result_lines.append(f"Total responses: {total_votes}")
        return "\n".join(result_lines)

    # RangeSlider -> numeric stats
    if q_type == "RangeSlider":
        values = []
        for ans in raw_answers:
            try:
                values.append(float(ans))
            except ValueError:
                pass

        if not values:
            return (
                f"\nResults for Survey {enter_code}\n"
                f"Block: {block_id}\n"
                f"Question: {question_text}\n"
                "No numeric answers yet."
            )

        avg = sum(values) / len(values)
        result_lines = [
            f"\nResults for Survey {enter_code}",
            f"Block: {block_id}",
            f"Question: {question_text}",
            "-----------------------------------",
            f"Responses: {len(values)}",
            f"Average: {avg:.2f}",
        ]
        return "\n".join(result_lines)

    # TextQuestion or others -> just count of answers
    result_lines = [
        f"\nResults for Survey {enter_code}",
        f"Block: {block_id}",
        f"Question: {question_text}",
        "-----------------------------------",
        f"Text responses: {len(raw_answers)}",
    ]
    return "\n".join(result_lines)


def get_full_survey_result(enter_code):
    blocks = fetch_vote_structure(enter_code)
    if not blocks:
        return f"Cannot load structure for survey {enter_code}"

    lines = [f"Results for survey {enter_code}"]

    for block_id in sorted(blocks.keys(), key=lambda x: int(x)):
        block = blocks[block_id]
        block_title = (
            block.get("title", {}).get("DE")
            or block.get("title", {}).get("EN")
            or f"Block {block_id}"
        )
        lines.append(f"\n=== Block {block_id}: {block_title} ===\n")

        questions = block.get("questions", {})
        for q_id in sorted(questions.keys(), key=lambda x: int(x)):
            result_text = get_survey_results(enter_code, block_id, q_id)
            if isinstance(result_text, tuple):
                result_text = " ".join(str(p) for p in result_text)
            lines.append(result_text)

    return "\n".join(lines)
