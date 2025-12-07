"""
Survey creation API integration
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
API_KEY = os.getenv("API_KEY")
ADMIN_PASS = os.getenv("ADMIN_PASS")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}


def create_advanced_survey(state_temp):
    """Create an advanced survey with blocks and questions"""
    
    # Build question blocks
    question_blocks = {}
    block_idx = 0
    
    # Add question blocks
    for block in state_temp.get("question_blocks", []):
        questions_dict = {}
        for q_idx, q in enumerate(block["questions"]):
            question_obj = {
                "question": {"DE": q["question"]},
                "question_type": q["type"],
                "settings": {"mandatory": False, "grid": False},
                "config": {},
                "analysis_mode": "FREE"
            }
            
            # Add type-specific config
            if q["type"] in ["ChoiceSingle", "ChoiceMulti"]:
                options_dict = {}
                for opt_idx, opt in enumerate(q["options"]):
                    options_dict[str(opt_idx)] = {"DE": opt}
                question_obj["config"]["option_type"] = "TEXT"
                question_obj["config"]["options"] = options_dict
            elif q["type"] == "Rating":
                question_obj["config"]["min"] = q.get("rating_min", 0)
                question_obj["config"]["max"] = q.get("rating_max", 100)
            
            questions_dict[str(q_idx)] = question_obj
        
        # Build structure for this block - link questions in sequence
        num_questions = len(block["questions"])
        components = {}
        for i in range(num_questions):
            if i == num_questions - 1:
                # Last question points to -1 (end)
                components[str(i)] = {"default": -1}
            else:
                # Other questions point to next question
                components[str(i)] = {"default": i + 1}
        
        structure = {
            "start": 0,
            "components": components
        }
        
        block_data = {
            "title": {"DE": block["title"]},
            "questions": questions_dict,
            "analysis_mode": "FREE",
            "structure": structure
        }
        
        # Only add description if it's not empty
        if block.get("description", "").strip():
            block_data["description"] = {"DE": block["description"]}
        
        question_blocks[str(block_idx)] = block_data
        block_idx += 1
    
    # Add standalone questions as a separate block
    if state_temp.get("standalone_questions"):
        questions_dict = {}
        for q_idx, q in enumerate(state_temp["standalone_questions"]):
            question_obj = {
                "question": {"DE": q["question"]},
                "question_type": q["type"],
                "settings": {"mandatory": False, "grid": False},
                "config": {},
                "analysis_mode": "FREE"
            }
            
            # Add type-specific config
            if q["type"] in ["ChoiceSingle", "ChoiceMulti"]:
                options_dict = {}
                for opt_idx, opt in enumerate(q["options"]):
                    options_dict[str(opt_idx)] = {"DE": opt}
                question_obj["config"]["option_type"] = "TEXT"
                question_obj["config"]["options"] = options_dict
            elif q["type"] == "Rating":
                question_obj["config"]["min"] = q.get("rating_min", 0)
                question_obj["config"]["max"] = q.get("rating_max", 100)
            
            questions_dict[str(q_idx)] = question_obj
        
        # Build structure for standalone questions - link in sequence
        num_questions = len(state_temp["standalone_questions"])
        components = {}
        for i in range(num_questions):
            if i == num_questions - 1:
                # Last question points to -1 (end)
                components[str(i)] = {"default": -1}
            else:
                # Other questions point to next question
                components[str(i)] = {"default": i + 1}
        
        structure = {
            "start": 0,
            "components": components
        }
        
        question_blocks[str(block_idx)] = {
            "title": {"DE": "Additional Questions"},
            "description": {"DE": "Standalone questions"},
            "questions": questions_dict,
            "analysis_mode": "FREE",
            "structure": structure
        }
    
    # Build global structure - link blocks in sequence
    num_blocks = len(question_blocks)
    global_components = {}
    for i in range(num_blocks):
        if i == num_blocks - 1:
            # Last block points to -1 (end)
            global_components[str(i)] = {"default": -1}
        else:
            # Other blocks point to next block
            global_components[str(i)] = {"default": i + 1}
    
    global_structure = {
        "start": 0,
        "components": global_components
    }
    
    # Build complete survey payload
    survey_data = {
        "data": {
            "module": "Survey",
            "config": {
                "title": {"DE": state_temp["title"]},
                "creator": state_temp["email"],
                "public": True,
                "settings": {
                    "editable_answer": True,
                    "full_participation": True,
                    "participation_mode": "UNGUIDED",
                    "participation_val_mode": "COOKIE"
                },
                "analysis_mode": "FREE",
                "structure": global_structure,
                "admin_pw": ADMIN_PASS
            },
            "question_blocks": question_blocks
        }
    }
    
    # Add description if exists and not empty
    if state_temp.get("description", "").strip():
        survey_data["data"]["config"]["description"] = {"DE": state_temp["description"]}
    
    # Make API call
    response = requests.post(f"{BASE_URL}/vote", headers=headers, json=survey_data)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        return {"error": f"Status {response.status_code}: {response.text}"}
