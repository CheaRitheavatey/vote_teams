# /api/message = POST
from flask import Flask, render_template, request, jsonify
from api.fetch_question import fetch_question, fetch_surveys
from api.submit_answer import submit_answer
from api.create_survey import create_survey
from api.get_result import get_survey_results
from api.validation import SurveyValidator

import uuid


app = Flask(__name__)

# Initialize validator instance for email validation
validator = SurveyValidator()

# maps room_id -> state dict
ROOMS = {
    "demo": {
        "pending_create": None,   # used when the bot is in create-survey flow
        "last_survey_code": None,
        "pending_confirmation": None,
        "pending_vote_for_code": None
    }
}

# Helper functions for advanced mode
def send_question_preview(state):
    """Generate a preview of the current question with validation"""
    q = state["temp"]["current_question"]
    q_type = q["type"]
    question_text = q.get("question", "")
    
    preview = f"<strong>Question Preview:</strong>\n\n{question_text}\n<strong>Type:</strong> {q_type}\n"
    
    if "options" in q:
        preview += "<strong>Options:</strong>\n" + "\n".join([f"- {opt}" for opt in q["options"]])
    elif q_type == "Rating" and "rating_min" in q:
        preview += f"<strong>Rating Range:</strong> {q['rating_min']} to {q['rating_max']}"
    
    # Transform question data to API format for validation
    question_data_for_validation = {
        "question": {"DE": question_text} if question_text else {"DE": "Test Question"},
        "settings": {"mandatory": False, "grid": False},
        "config": {}
    }
    
    # Format options correctly for the API
    if q_type in ["ChoiceSingle", "ChoiceMulti"]:
        if "options" in q:
            # Convert list to dict format: {"0": {"DE": "option1"}, "1": {"DE": "option2"}}
            options_dict = {}
            for idx, opt in enumerate(q["options"]):
                options_dict[str(idx)] = {"DE": opt}
            question_data_for_validation["config"]["options"] = options_dict
            question_data_for_validation["config"]["option_type"] = "TEXT"
    
    elif q_type == "Rating":
        if "rating_min" in q and "rating_max" in q:
            question_data_for_validation["config"]["min"] = q["rating_min"]
            question_data_for_validation["config"]["max"] = q["rating_max"]
    
    # Validate the question with proper format
    validation_result = validator.validate_question(question_data_for_validation, q_type)
    
    if not validation_result.success:
        preview += "\n\n<strong>⚠️ Validation Errors:</strong>\n"
        for error in validation_result.errors:
            preview += f"❌ {error}\n"
        preview += "\nPlease fix these issues before saving."
    else:
        if validation_result.warnings:
            preview += "\n\n<strong>⚠️ Warnings:</strong>\n"
            for warning in validation_result.warnings:
                preview += f"⚠️ {warning}\n"
        
        preview += "\n\n<strong>Commands:</strong>\n"
        preview += "• <strong>save</strong> - Add this question\n"
        preview += "• <strong>edit question</strong> - Change the question text\n"
        
        if q_type in ["ChoiceSingle", "ChoiceMulti"]:
            preview += "• <strong>edit options</strong> - Change the options\n"
        elif q_type == "Rating":
            preview += "• <strong>edit range</strong> - Change the rating range\n"
    
    # Store validation result for later use
    state["temp"]["validation_result"] = validation_result
    
    return preview

def send_advanced_overview(state):
    """Generate complete overview for advanced mode"""
    t = state["temp"]
    
    overview = "<strong>Survey Overview:</strong>\n\n"
    overview += f"<strong>Creator Email:</strong> {t['email']}\n"
    overview += f"<strong>Title:</strong> {t['title']}\n"
    
    if "description" in t:
        overview += f"<strong>Description:</strong> {t['description']}\n"
    
    overview += f"<strong>Language:</strong> {t.get('language', 'EN')}\n\n"
    
    # Show blocks
    if t.get("question_blocks"):
        overview += "<strong>Question Blocks:</strong>\n"
        for i, block in enumerate(t["question_blocks"], 1):
            overview += f"\n<strong>Block {i}: {block['title']}</strong>\n"
            if block.get("description"):
                overview += f"  {block['description']}\n"
            for j, q in enumerate(block["questions"], 1):
                overview += f"  {j}. {q['question']} ({q['type']})\n"
    
    # Show standalone questions
    if t.get("standalone_questions"):
        overview += "\n<strong>Standalone Questions:</strong>\n"
        for i, q in enumerate(t["standalone_questions"], 1):
            overview += f"{i}. {q['question']} ({q['type']})\n"
    
    overview += (
        "\n\nType <strong>done</strong> to finalize.\n"
        "Type <strong>add block</strong> or <strong>add question</strong> to add more.\n"
        "Type <strong>cancel</strong> to discard."
    )
    
    return overview

def create_advanced_survey(state_temp):
    """Create an advanced survey with blocks and questions"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    ADMIN_PASS = os.getenv("ADMIN_PASS")
    
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
        
        # Build structure for this block
        structure = {
            "start": 0,
            "components": {str(i): {"default": -1} for i in range(len(block["questions"]))}
        }
        
        question_blocks[str(block_idx)] = {
            "title": {"DE": block["title"]},
            "description": {"DE": block.get("description", "")},
            "questions": questions_dict,
            "analysis_mode": "FREE",
            "structure": structure
        }
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
        
        structure = {
            "start": 0,
            "components": {str(i): {"default": -1} for i in range(len(state_temp["standalone_questions"]))}
        }
        
        question_blocks[str(block_idx)] = {
            "title": {"DE": "Additional Questions"},
            "description": {"DE": "Standalone questions"},
            "questions": questions_dict,
            "analysis_mode": "FREE",
            "structure": structure
        }
    
    # Build global structure
    global_structure = {
        "start": 0,
        "components": {str(i): {"default": -1} for i in range(len(question_blocks))}
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
    
    # Add description if exists
    if "description" in state_temp:
        survey_data["data"]["config"]["description"] = {"DE": state_temp["description"]}
    
    # Make API call
    import requests
    BASE_URL = "https://vote2.telekom.net/api/v1"
    API_KEY = os.getenv("API_KEY")
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{BASE_URL}/vote", headers=headers, json=survey_data)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        return {"error": f"Status {response.status_code}: {response.text}"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/message", methods=["POST"])
def api_message():
    payload = request.json
    room = "demo"
    user = payload.get("user", "User")
    text = (payload.get("text") or "").strip()

    # append user message for frontend
    messages = []
    messages.append({"from": user, "text": text})

    # Simple command parsing:
    if text.lower().startswith("/votebot create"):
        # Start with creation mode choice
        ROOMS[room]["pending_create"] = {"step": "ask_mode", "temp": {}}
        bot_text = (
            "Let's create a survey! Choose your path:\n\n"
            "1. <strong>Quick Create</strong> - Simple survey with auto-configured settings\n"
            "2. <strong>Advanced Create</strong> - Full control over all features\n\n"
            "Reply 1 or 2"
        )
        messages.append({"from": "VoteBot", "text": bot_text})
        return jsonify(messages=messages)

    # Continue interactive create flow
    state = ROOMS[room].get("pending_create")
    if state:
        step = state["step"]

        # Ask creation mode (Quick or Advanced)
        if step == "ask_mode":
            if text.strip() == "1":
                state["temp"]["mode"] = "quick"
                state["step"] = "ask_email"
                messages.append({"from": "VoteBot", "text": "Quick Create selected! First, what's your email address? (Required)"})
            elif text.strip() == "2":
                state["temp"]["mode"] = "advanced"
                state["step"] = "ask_email"
                messages.append({"from": "VoteBot", "text": "Advanced Create selected! First, what's your email address? (Required)"})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 1 for Quick Create or 2 for Advanced Create."})
            return jsonify(messages=messages)

        # Ask email (required for both modes)
        if step == "ask_email":
            # TODO: Implement proper email validation after consulting with mentor
            # Basic format check only for now
            if "@" not in text or "." not in text:
                messages.append({"from": "VoteBot", "text": "Please enter a valid email address (must contain @ and a domain)."})
                return jsonify(messages=messages)
            
            state["temp"]["email"] = text.strip()
            
            # Branch based on mode
            if state["temp"]["mode"] == "quick":
                state["step"] = "ask_title"
                messages.append({"from": "VoteBot", "text": "Great! Now, what's the survey title?"})
            else:  # advanced mode
                state["step"] = "advanced_title"
                messages.append({"from": "VoteBot", "text": "Great! Let's configure your survey.\n\n<strong>Survey title?</strong>"})
            return jsonify(messages=messages)

        # === ADVANCED MODE WORKFLOW ===
        
        # Advanced: Title
        if step == "advanced_title":
            state["temp"]["title"] = text
            state["step"] = "advanced_description"
            messages.append({"from": "VoteBot", "text": "<strong>Description?</strong> (Optional - type 'skip' to skip)"})
            return jsonify(messages=messages)
        
        # Advanced: Description
        if step == "advanced_description":
            if text.lower() != "skip":
                state["temp"]["description"] = text
            state["step"] = "advanced_language"
            messages.append({"from": "VoteBot", "text": "<strong>Language?</strong>\n1. English\n2. German\n3. Both"})
            return jsonify(messages=messages)
        
        # Advanced: Language
        if step == "advanced_language":
            lang_map = {"1": "EN", "2": "DE", "3": "BOTH"}
            state["temp"]["language"] = lang_map.get(text.strip(), "EN")
            
            # Initialize question_blocks and standalone_questions if not exists
            if "question_blocks" not in state["temp"]:
                state["temp"]["question_blocks"] = []
            if "standalone_questions" not in state["temp"]:
                state["temp"]["standalone_questions"] = []
            
            # Validate global settings with a dummy question block
            messages.append({"from": "VoteBot", "text": "<strong>Validating global settings...</strong>"})
            
            # Build minimal survey config with dummy block for validation
            survey_config = {
                "title": {"DE": state["temp"]["title"]},
                "creator": state["temp"]["email"],
                "public": True,
                "state": "PUBLISHED",
                "settings": {
                    "editable_answer": True,
                    "full_participation": True,
                    "participation_mode": "UNGUIDED",
                    "participation_val_mode": "COOKIE"
                },
                "analysis_mode": "FREE"
            }
            
            if "description" in state["temp"]:
                survey_config["description"] = {"DE": state["temp"]["description"]}
            
            # Create a dummy block with one question for validation
            dummy_block = {
                "0": {
                    "title": {"DE": "Dummy Block"},
                    "description": {"DE": "Validation block"},
                    "questions": {
                        "0": {
                            "question": {"DE": "Validation question"},
                            "question_type": "ChoiceSingle",
                            "settings": {"mandatory": False, "grid": False},
                            "config": {
                                "option_type": "TEXT",
                                "options": {"0": {"DE": "Yes"}, "1": {"DE": "No"}}
                            },
                            "analysis_mode": "FREE"
                        }
                    },
                    "analysis_mode": "FREE",
                    "structure": {"start": 0, "components": {"0": {"default": -1}}}
                }
            }
            
            # Validate using validator
            validation_result = validator.validate_full_survey(survey_config, dummy_block)
            
            if not validation_result.success:
                error_msg = "<strong>⚠️ Global settings validation failed:</strong>\n"
                for error in validation_result.errors:
                    error_msg += f"❌ {error}\n"
                error_msg += "\nPlease check your settings. Type 'retry' to try again or 'cancel' to start over."
                messages.append({"from": "VoteBot", "text": error_msg})
                state["step"] = "advanced_duration"  # Allow retry
            else:
                messages.append({"from": "VoteBot", "text": (
                    "<strong>✅ Global settings validated!</strong>\n\n"
                    "Now let's add questions.\n\n"
                    "<strong>Create a Question Block?</strong>\n"
                    "Question blocks group related questions together (like chapters).\n\n"
                    "Reply 'yes' to create a block, or 'no' for standalone questions"
                )})
                state["step"] = "advanced_ask_block"
            
            return jsonify(messages=messages)
        
        # Advanced: Ask if user wants to create a block
        if step == "advanced_ask_block":
            if text.lower() == "yes":
                state["step"] = "block_title"
                messages.append({"from": "VoteBot", "text": "<strong>Block title?</strong>\nExample: 'Employee Satisfaction'"})
            elif text.lower() == "no":
                state["temp"]["current_block"] = None
                state["step"] = "select_question_type"
                messages.append({"from": "VoteBot", "text": (
                    "<strong>Adding standalone questions</strong>\n\n"
                    "What type of question?\n\n"
                    "1. Single Choice\n"
                    "2. Multiple Choice\n"
                    "3. Rating (0-100 scale)\n"
                    "4. Free Text"
                )})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
            return jsonify(messages=messages)
        
        # Block: Title
        if step == "block_title":
            block = {"title": text, "description": "", "questions": []}
            state["temp"]["current_block"] = block
            state["step"] = "block_description"
            messages.append({"from": "VoteBot", "text": "<strong>Block description?</strong> (Optional - type 'skip' to skip)"})
            return jsonify(messages=messages)
        
        # Block: Description
        if step == "block_description":
            if text.lower() != "skip":
                state["temp"]["current_block"]["description"] = text
            state["step"] = "select_question_type"
            
            block_title = state["temp"]["current_block"]["title"]
            messages.append({"from": "VoteBot", "text": (
                f"<strong>Current Block: {block_title}</strong>\n"
                "Ready to add questions!\n\n"
                "What type of question?\n\n"
                "1. Single Choice\n"
                "2. Multiple Choice\n"
                "3. Rating (0-100 scale)\n"
                "4. Free Text"
            )})
            return jsonify(messages=messages)
        
        # Select Question Type (for both block and standalone)
        if step == "select_question_type":
            q_type_map = {
                "1": "ChoiceSingle",
                "2": "ChoiceMulti",
                "3": "Rating",
                "4": "TextInput"
            }
            
            if text.strip() in q_type_map:
                state["temp"]["current_question"] = {"type": q_type_map[text.strip()]}
                state["step"] = "question_text"
                messages.append({"from": "VoteBot", "text": "<strong>Your question?</strong>"})
            else:
                messages.append({"from": "VoteBot", "text": "Please select a valid option (1-4)"})
            return jsonify(messages=messages)
        
        # Question: Text
        if step == "question_text":
            state["temp"]["current_question"]["question"] = text
            q_type = state["temp"]["current_question"]["type"]
            
            # Branch based on question type
            if q_type in ["ChoiceSingle", "ChoiceMulti"]:
                state["temp"]["current_question"]["options"] = []
                state["step"] = "question_options"
                messages.append({"from": "VoteBot", "text": "<strong>Add options</strong>\nEnter options one per message. Type 'done' when finished."})
            elif q_type == "Rating":
                state["step"] = "rating_min"
                messages.append({"from": "VoteBot", "text": "<strong>Minimum rating value?</strong> (e.g., 0)"})
            elif q_type == "TextInput":
                state["step"] = "question_confirm"
                messages.append({"from": "VoteBot", "text": send_question_preview(state)})
            return jsonify(messages=messages)
        
        # Question Options (for Choice questions)
        if step == "question_options":
            if text.lower() == "done":
                if len(state["temp"]["current_question"]["options"]) < 2:
                    messages.append({"from": "VoteBot", "text": "Please add at least 2 options before typing 'done'"})
                    return jsonify(messages=messages)
                
                state["step"] = "question_confirm"
                messages.append({"from": "VoteBot", "text": send_question_preview(state)})
            else:
                state["temp"]["current_question"]["options"].append(text.strip())
                count = len(state["temp"]["current_question"]["options"])
                messages.append({"from": "VoteBot", "text": f"Option {count} added. Continue adding or type 'done'"})
            return jsonify(messages=messages)
        
        # Rating: Minimum value
        if step == "rating_min":
            try:
                min_val = int(text)
                if min_val < 0 or min_val > 100:
                    messages.append({"from": "VoteBot", "text": "Please enter a number between 0 and 100"})
                    return jsonify(messages=messages)
                state["temp"]["current_question"]["rating_min"] = min_val
                state["step"] = "rating_max"
                messages.append({"from": "VoteBot", "text": "<strong>Maximum rating value?</strong> (e.g., 100)"})
            except ValueError:
                messages.append({"from": "VoteBot", "text": "Please enter a valid number"})
            return jsonify(messages=messages)
        
        # Rating: Maximum value
        if step == "rating_max":
            try:
                max_val = int(text)
                min_val = state["temp"]["current_question"]["rating_min"]
                if max_val < 0 or max_val > 100:
                    messages.append({"from": "VoteBot", "text": "Please enter a number between 0 and 100"})
                    return jsonify(messages=messages)
                if max_val <= min_val:
                    messages.append({"from": "VoteBot", "text": f"Maximum must be greater than minimum ({min_val})"})
                    return jsonify(messages=messages)
                state["temp"]["current_question"]["rating_max"] = max_val
                state["step"] = "question_confirm"
                messages.append({"from": "VoteBot", "text": send_question_preview(state)})
            except ValueError:
                messages.append({"from": "VoteBot", "text": "Please enter a valid number"})
            return jsonify(messages=messages)
        
        # Question Confirmation
        if step == "question_confirm":
            cmd = text.lower()
            
            if cmd == "save":
                # Check if validation passed
                validation_result = state["temp"].get("validation_result")
                if validation_result and not validation_result.success:
                    messages.append({"from": "VoteBot", "text": "Cannot save question with validation errors. Please fix the issues first."})
                    return jsonify(messages=messages)
                
                # Save question to current block or standalone
                if state["temp"]["current_block"]:
                    state["temp"]["current_block"]["questions"].append(state["temp"]["current_question"])
                    state["temp"]["current_question"] = None
                    state["step"] = "ask_more_questions_in_block"
                    
                    block_title = state["temp"]["current_block"]["title"]
                    q_count = len(state["temp"]["current_block"]["questions"])
                    messages.append({"from": "VoteBot", "text": (
                        f"Question saved to <strong>{block_title}</strong> ({q_count} total)\n\n"
                        "Add another question to this block? (yes/no)"
                    )})
                else:
                    state["temp"]["standalone_questions"].append(state["temp"]["current_question"])
                    state["temp"]["current_question"] = None
                    state["step"] = "ask_more_standalone"
                    
                    q_count = len(state["temp"]["standalone_questions"])
                    messages.append({"from": "VoteBot", "text": (
                        f"Question saved! ({q_count} standalone questions total)\n\n"
                        "Add another standalone question? (yes/no)"
                    )})
            
            elif cmd == "edit question" or cmd == "edit text":
                state["step"] = "question_text"
                messages.append({"from": "VoteBot", "text": "<strong>Enter the new question text:</strong>"})
            
            elif cmd == "edit options":
                q_type = state["temp"]["current_question"]["type"]
                if q_type in ["ChoiceSingle", "ChoiceMulti"]:
                    state["temp"]["current_question"]["options"] = []
                    state["step"] = "question_options"
                    messages.append({"from": "VoteBot", "text": "<strong>Add new options</strong>\nEnter options one per message. Type 'done' when finished."})
                else:
                    messages.append({"from": "VoteBot", "text": "This question type doesn't have options to edit."})
            
            elif cmd == "edit range":
                q_type = state["temp"]["current_question"]["type"]
                if q_type == "Rating":
                    state["step"] = "rating_min"
                    messages.append({"from": "VoteBot", "text": "<strong>Minimum rating value?</strong> (e.g., 0)"})
                else:
                    messages.append({"from": "VoteBot", "text": "This question type doesn't have a range to edit."})
            
            else:
                messages.append({"from": "VoteBot", "text": "Type <strong>save</strong> to add this question, or <strong>edit question</strong>, <strong>edit options</strong>, <strong>edit range</strong> to modify."})
            
            return jsonify(messages=messages)
        
        # Ask if more questions in current block
        if step == "ask_more_questions_in_block":
            if text.lower() == "yes":
                state["step"] = "select_question_type"
                block_title = state["temp"]["current_block"]["title"]
                messages.append({"from": "VoteBot", "text": (
                    f"<strong>Adding to: {block_title}</strong>\n\n"
                    "What type of question?\n\n"
                    "1. Single Choice\n"
                    "2. Multiple Choice\n"
                    "3. Rating (0-100 scale)\n"
                    "4. Free Text"
                )})
            elif text.lower() == "no":
                # Save block and ask if want to create another block
                state["temp"]["question_blocks"].append(state["temp"]["current_block"])
                state["temp"]["current_block"] = None
                state["step"] = "ask_more_blocks"
                
                block_count = len(state["temp"]["question_blocks"])
                messages.append({"from": "VoteBot", "text": (
                    f"Block saved! ({block_count} blocks total)\n\n"
                    "Create another question block? (yes/no)"
                )})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
            
            return jsonify(messages=messages)
        
        # Ask if more standalone questions
        if step == "ask_more_standalone":
            if text.lower() == "yes":
                state["step"] = "select_question_type"
                messages.append({"from": "VoteBot", "text": (
                    "What type of question?\n\n"
                    "1. Single Choice\n"
                    "2. Multiple Choice\n"
                    "3. Rating (0-100 scale)\n"
                    "4. Free Text"
                )})
            elif text.lower() == "no":
                state["step"] = "advanced_overview"
                messages.append({"from": "VoteBot", "text": send_advanced_overview(state)})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
            
            return jsonify(messages=messages)
        
        # Ask if more blocks
        if step == "ask_more_blocks":
            if text.lower() == "yes":
                state["step"] = "block_title"
                messages.append({"from": "VoteBot", "text": "<strong>Block title?</strong>"})
            elif text.lower() == "no":
                # Ask if want to add standalone questions
                state["step"] = "ask_standalone_after_blocks"
                messages.append({"from": "VoteBot", "text": "Add standalone questions (not in a block)? (yes/no)"})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
            
            return jsonify(messages=messages)
        
        # Ask standalone after blocks
        if step == "ask_standalone_after_blocks":
            if text.lower() == "yes":
                state["temp"]["current_block"] = None
                state["step"] = "select_question_type"
                messages.append({"from": "VoteBot", "text": (
                    "<strong>Adding standalone questions</strong>\n\n"
                    "What type of question?\n\n"
                    "1. Single Choice\n"
                    "2. Multiple Choice\n"
                    "3. Rating (0-100 scale)\n"
                    "4. Free Text"
                )})
            elif text.lower() == "no":
                state["step"] = "advanced_overview"
                messages.append({"from": "VoteBot", "text": send_advanced_overview(state)})
            else:
                messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
            
            return jsonify(messages=messages)
        
        # Advanced Overview confirmation
        if step == "advanced_overview":
            cmd = text.lower()
            
            if cmd == "done":
                # Create the advanced survey via API
                messages.append({"from": "VoteBot", "text": "<strong>Creating survey...</strong>"})
                
                try:
                    response = create_advanced_survey(state["temp"])
                    
                    if "error" in response:
                        messages.append({"from": "VoteBot", "text": (
                            f"<strong>❌ Error creating survey:</strong>\n{response['error']}\n\n"
                            "Type 'retry' to try again or 'cancel' to discard."
                        )})
                    else:
                        enter_code = response.get("enter_code")
                        ROOMS[room]["last_survey_code"] = enter_code
                        ROOMS[room]["pending_create"] = None
                        
                        messages.append({"from": "VoteBot", "text": (
                            f"<strong>✅ Survey created successfully!</strong>\n\n"
                            f"<strong>Survey Code:</strong> {enter_code}\n\n"
                            "Type 'create' to make another survey"
                        )})
                except Exception as e:
                    messages.append({"from": "VoteBot", "text": (
                        f"<strong>❌ Error:</strong> {str(e)}\n\n"
                        "Type 'retry' to try again or 'cancel' to discard."
                    )})
            elif cmd == "add block":
                state["step"] = "block_title"
                messages.append({"from": "VoteBot", "text": "<strong>Block title?</strong>"})
            elif cmd == "add question":
                state["temp"]["current_block"] = None
                state["step"] = "select_question_type"
                messages.append({"from": "VoteBot", "text": (
                    "What type of question?\n\n"
                    "1. Single Choice\n"
                    "2. Multiple Choice\n"
                    "3. Rating (0-100 scale)\n"
                    "4. Free Text"
                )})
            elif cmd == "cancel":
                ROOMS[room]["pending_create"] = None
                messages.append({"from": "VoteBot", "text": "Survey creation cancelled."})
            else:
                messages.append({"from": "VoteBot", "text": "Type <strong>done</strong>, <strong>add block</strong>, <strong>add question</strong>, or <strong>cancel</strong>"})
            
            return jsonify(messages=messages)

        # === QUICK MODE WORKFLOW (existing) ===

        # Ask title
        if step == "ask_title":
            state["temp"]["title"] = text
            state["step"] = "ask_question"
            messages.append({"from": "VoteBot", "text": "What's the question?"})
            return jsonify(messages=messages)

        # Ask question
        if step == "ask_question":
            state["temp"]["question"] = text
            state["step"] = "ask_type"
            messages.append({"from": "VoteBot", "text": "Single choice or multiple choice?\nReply 1 for Single / 2 for Multiple."})
            return jsonify(messages=messages)

        # Ask type
        if step == "ask_type":
            state["temp"]["qtype"] = "ChoiceSingle" if text.strip() == "1" else "ChoiceMulti"
            state["step"] = "ask_options"
            messages.append({"from": "VoteBot", "text": "Enter options separated by commas (e.g. red,blue,green)."})
            return jsonify(messages=messages)

        # Ask options → Generate Overview
        if step == "ask_options":
            opts = [o.strip() for o in text.split(",") if o.strip()]
            state["temp"]["options"] = opts
            state["step"] = "confirm_overview"

            title = state["temp"]["title"]
            question = state["temp"]["question"]
            email = state["temp"]["email"]
            qtype = "Single Choice" if state["temp"]["qtype"] == "ChoiceSingle" else "Multiple Choice"
            options_text = "\n".join([f"- {o}" for o in opts])

            overview = (
                "Here is your survey overview:\n\n"
                f"<strong>Creator Email:</strong> {email}\n"
                f"<strong>Title:</strong> {title}\n"
                f"<strong>Question:</strong> {question}\n"
                f"<strong>Type:</strong> {qtype}\n"
                f"<strong>Options:</strong>\n{options_text}\n\n"
                "Type <strong>done</strong> to finalize.\n"
                "Type <strong>edit title</strong>, <strong>edit question</strong>, <strong>edit type</strong>, or <strong>edit options</strong> to modify.\n"
                "Type <strong>cancel</strong> to stop."
            )

            messages.append({"from": "VoteBot", "text": overview})
            return jsonify(messages=messages)
        
        # confirmation phase
        if step == "confirm_overview":
            cmd = text.lower()

            if cmd == "done":
                t = state["temp"]
                response = create_survey(t["title"], t["question"], t["qtype"], t["options"], t["email"])
                enter_code = response.get("enter_code")

                ROOMS[room]["last_survey_code"] = enter_code
                ROOMS[room]["pending_create"] = None

                messages.append({"from": "VoteBot", "text": f"Survey created! Code: {enter_code}. Type /VoteBot vote {enter_code} to do the survey!"})
                return jsonify(messages=messages)

            if cmd == "edit title":
                state["step"] = "edit_title"
                messages.append({"from": "VoteBot", "text": "Enter new title:"})
                return jsonify(messages=messages)

            if cmd == "edit question":
                state["step"] = "edit_question"
                messages.append({"from": "VoteBot", "text": "Enter new question:"})
                return jsonify(messages=messages)

            if cmd == "edit type":
                state["step"] = "edit_type"
                messages.append({"from": "VoteBot", "text": "Reply 1 for Single Choice or 2 for Multiple Choice:"})
                return jsonify(messages=messages)

            if cmd == "edit options":
                state["step"] = "edit_options"
                messages.append({"from": "VoteBot", "text": "Enter new comma-separated options:"})
                return jsonify(messages=messages)

            if cmd == "cancel":
                ROOMS[room]["pending_create"] = None
                messages.append({"from": "VoteBot", "text": "Survey creation cancelled."})
                return jsonify(messages=messages)

            messages.append({"from": "VoteBot", "text": "Please type done / edit title / edit question / edit type / edit option / cancel."})
            return jsonify(messages=messages)

        # edit phase
        if step == "edit_title":
            state["temp"]["title"] = text
            state["step"] = "confirm_overview"  
            messages.append({"from": "VoteBot", "text": send_overview(state)})
            return jsonify(messages=messages)

        if step == "edit_question":
            state["temp"]["question"] = text
            state["step"] = "confirm_overview"
            messages.append({"from": "VoteBot", "text": send_overview(state)})
            return jsonify(messages=messages)
            
            
        if step == "edit_type":
            state["temp"]["qtype"] = "ChoiceSingle" if text.strip() == "1" else "ChoiceMulti"
            state["step"] = "confirm_overview"
            
            messages.append({"from": "VoteBot", "text": send_overview(state)})
            return jsonify(messages=messages)

        if step == "edit_options":
            state["temp"]["options"] = [o.strip() for o in text.split(",") if o.strip()]
            state["step"] = "confirm_overview"
           
            messages.append({"from": "VoteBot", "text": send_overview(state)})
            return jsonify(messages=messages)

    # vote flow
    if text.lower().startswith("/votebot vote"):
        parts = text.split()
        if len(parts) >= 3:
            code = parts[2]
            qdata = fetch_question(code, "0", "0")
            if not qdata:
                messages.append({"from": "VoteBot", "text": "Could not load survey or invalid code."})
                return jsonify(messages=messages)
            question_text = qdata["question"]["DE"]
            opts = [v["DE"] for k,v in qdata["config"]["options"].items()]
            # present options to user
            opt_lines = "\n".join([f"{i}. {o}" for i,o in enumerate(opts)])
            messages.append({"from": "VoteBot", "text": f"Question: {question_text}\n{opt_lines}\nReply with option number (for multi-choice, send comma-separated numbers)."})
            # store a simple pending vote marker
            ROOMS[room]["pending_vote_for_code"] = code
            return jsonify(messages=messages)

    # handle a vote reply if pending
    if ROOMS[room].get("pending_vote_for_code"):
        code = ROOMS[room]["pending_vote_for_code"]
        # assume reply is numbers e.g. "0" or "0,1"
        selection = [s.strip() for s in text.split(",") if s.strip()]
        # call submit_answer - you need a function that matches API expectation
        resp = submit_answer(code, "0", "0", selection)   # implement in vote_api
        ROOMS[room]["pending_vote_for_code"] = None
        if resp.get('identifier'):
            messages.append({
                "from": "VoteBot",
                "text": "Answer submitted!"
            })
            return jsonify(messages=messages),200
        else:
            messages.append({"from": "VoteBot", "text": f"Vote error: {resp}"})
            return jsonify(messages=messages) ,500

    # results command
    if text.lower().startswith("/votebot result"):
        parts = text.split()
        code = parts[2] if len(parts) >=3 else ROOMS[room].get("last_survey_code")
        if not code:
            messages.append({"from": "VoteBot", "text": "Please provide a survey code: /VoteBot result <code>"})
            return jsonify(messages=messages)
        results = get_survey_results(code, block_id=0, question_id=0)  # should return processed dict/string
        messages.append({"from": "VoteBot", "text": results.replace("\n", "<br>")})
        return jsonify(messages=messages)
    
    
    # fetch survey 
    if text.lower().startswith("/votebot fetch"):
        data = fetch_surveys()
        messages.append({"from": "VoteBot", "text": data.replace('\n', "<br>")})
        return jsonify(messages=messages)
    # default
    messages.append({"from": "VoteBot", "text": "Sorry, I didn't understand. Try '/VoteBot create' or '/VoteBot vote <code>' or '/VoteBot result <code>' or '/VoteBot fetch'."})
    return jsonify(messages=messages)


def send_overview(state):
    title = state["temp"]["title"]
    question = state["temp"]["question"]
    email = state["temp"]["email"]
    qtype = "Single Choice" if state["temp"]["qtype"] == "ChoiceSingle" else "Multiple Choice"
    options_text = "\n".join([f"- {o}" for o in state["temp"]["options"]])

    overview = (
        "Here is your survey overview:\n\n"
        f"<strong>Creator Email:</strong> {email}\n"
        f"<strong>Title:</strong> {title}\n"
        f"<strong>Question:</strong> {question}\n"
        f"<strong>Type:</strong> {qtype}\n"
        f"<strong>Options:</strong>\n{options_text}\n\n"
        "Type <strong>done</strong> to finalize.\n"
        "Type <strong>edit title</strong>, <strong>edit question</strong>, <strong>edit type</strong>, or <strong>edit options</strong> to modify.\n"
        "Type <strong>cancel</strong> to stop."
    )
    return overview

if __name__ == "__main__":
    app.run(debug=True)

