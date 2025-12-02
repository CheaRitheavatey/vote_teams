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
