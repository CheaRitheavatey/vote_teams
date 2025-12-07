"""
Advanced workflow step handlers
These functions handle the detailed steps of creating questions and blocks
"""
from flask import jsonify
from workflow.advanced_helpers import send_question_preview, send_advanced_overview
from workflow.survey_api import create_advanced_survey


def handle_block_selection(text, state, messages):
    """Handle whether user wants to create a block or standalone questions"""
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
            "3. Rating (0-100 scale)"
        )})
    else:
        messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
    return jsonify(messages=messages)


def handle_block_title(text, state, messages):
    """Handle block title input"""
    block = {"title": text, "description": "", "questions": []}
    state["temp"]["current_block"] = block
    state["step"] = "block_description"
    messages.append({"from": "VoteBot", "text": "<strong>Block description?</strong> (Optional - type 'skip' to skip)"})
    return jsonify(messages=messages)


def handle_block_description(text, state, messages):
    """Handle block description input"""
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
        "3. Rating (0-100 scale)"
    )})
    return jsonify(messages=messages)


def handle_question_type(text, state, messages):
    """Handle question type selection"""
    q_type_map = {
        "1": "ChoiceSingle",
        "2": "ChoiceMulti",
        "3": "Rating"
    }
    
    if text.strip() in q_type_map:
        state["temp"]["current_question"] = {"type": q_type_map[text.strip()]}
        state["step"] = "question_text"
        messages.append({"from": "VoteBot", "text": "<strong>Your question?</strong>"})
    else:
        messages.append({"from": "VoteBot", "text": "Please select a valid option (1-3)"})
    return jsonify(messages=messages)


def handle_question_text(text, state, messages):
    """Handle question text input"""
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
    return jsonify(messages=messages)


def handle_question_options(text, state, messages):
    """Handle adding options to choice questions"""
    if text.lower() == "done":
        if len(state["temp"]["current_question"]["options"]) < 2:
            messages.append({"from": "VoteBot", "text": "Please add at least 2 options before typing 'done'"})
            return jsonify(messages=messages)
        
        state["step"] = "question_confirm"
        from api.validation import SurveyValidator
        validator = SurveyValidator()
        messages.append({"from": "VoteBot", "text": send_question_preview(state, validator)})
    else:
        state["temp"]["current_question"]["options"].append(text.strip())
        count = len(state["temp"]["current_question"]["options"])
        messages.append({"from": "VoteBot", "text": f"Option {count} added. Continue adding or type 'done'"})
    return jsonify(messages=messages)


def handle_rating_min(text, state, messages):
    """Handle rating minimum value"""
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


def handle_rating_max(text, state, messages):
    """Handle rating maximum value"""
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
        from api.validation import SurveyValidator
        validator = SurveyValidator()
        messages.append({"from": "VoteBot", "text": send_question_preview(state, validator)})
    except ValueError:
        messages.append({"from": "VoteBot", "text": "Please enter a valid number"})
    return jsonify(messages=messages)


def handle_question_confirm(text, state, messages):
    """Handle question confirmation with edit options"""
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


def handle_more_questions_in_block(text, state, messages):
    """Ask if user wants to add more questions to current block"""
    if text.lower() == "yes":
        state["step"] = "select_question_type"
        block_title = state["temp"]["current_block"]["title"]
        messages.append({"from": "VoteBot", "text": (
            f"<strong>Adding to: {block_title}</strong>\n\n"
            "What type of question?\n\n"
            "1. Single Choice\n"
            "2. Multiple Choice\n"
            "3. Rating (0-100 scale)"
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


def handle_more_standalone(text, state, messages):
    """Ask if user wants to add more standalone questions"""
    if text.lower() == "yes":
        state["step"] = "select_question_type"
        messages.append({"from": "VoteBot", "text": (
            "What type of question?\n\n"
            "1. Single Choice\n"
            "2. Multiple Choice\n"
            "3. Rating (0-100 scale)"
        )})
    elif text.lower() == "no":
        state["step"] = "advanced_overview"
        messages.append({"from": "VoteBot", "text": send_advanced_overview(state)})
    else:
        messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
    
    return jsonify(messages=messages)


def handle_more_blocks(text, state, messages):
    """Ask if user wants to create more blocks"""
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


def handle_standalone_after_blocks(text, state, messages):
    """Ask if user wants standalone questions after creating blocks"""
    if text.lower() == "yes":
        state["temp"]["current_block"] = None
        state["step"] = "select_question_type"
        messages.append({"from": "VoteBot", "text": (
            "<strong>Adding standalone questions</strong>\n\n"
            "What type of question?\n\n"
            "1. Single Choice\n"
            "2. Multiple Choice\n"
            "3. Rating (0-100 scale)"
        )})
    elif text.lower() == "no":
        state["step"] = "advanced_overview"
        messages.append({"from": "VoteBot", "text": send_advanced_overview(state)})
    else:
        messages.append({"from": "VoteBot", "text": "Please reply 'yes' or 'no'"})
    
    return jsonify(messages=messages)


def handle_advanced_overview(text, state, messages, room):
    """Handle final overview and survey creation"""
    from app import ROOMS
    
    cmd = text.lower()
    
    if cmd == "done":
        # Validate complete survey structure before creation
        messages.append({"from": "VoteBot", "text": "<strong>Validating survey structure...</strong>"})
        
        try:
            from api.validation import SurveyValidator
            validator = SurveyValidator()
            
            # Build blocks for validation
            blocks_for_validation = {}
            block_idx = 0
            
            # Add question blocks
            for block in state["temp"].get("question_blocks", []):
                questions_dict = {}
                for q_idx, q in enumerate(block["questions"]):
                    question_obj = {
                        "question": {"DE": q["question"]},
                        "question_type": q["type"],
                        "settings": {"mandatory": False, "grid": False},
                        "config": {},
                        "analysis_mode": "FREE"
                    }
                    
                    if q["type"] in ["ChoiceSingle", "ChoiceMulti"]:
                        options_dict = {str(i): {"DE": opt} for i, opt in enumerate(q["options"])}
                        question_obj["config"]["option_type"] = "TEXT"
                        question_obj["config"]["options"] = options_dict
                    elif q["type"] == "Rating":
                        question_obj["config"]["min"] = q.get("rating_min", 0)
                        question_obj["config"]["max"] = q.get("rating_max", 100)
                    
                    questions_dict[str(q_idx)] = question_obj
                
                # Build proper structure
                num_questions = len(block["questions"])
                components = {}
                for i in range(num_questions):
                    components[str(i)] = {"default": -1 if i == num_questions - 1 else i + 1}
                
                block_data = {
                    "title": {"DE": block["title"]},
                    "questions": questions_dict,
                    "analysis_mode": "FREE",
                    "structure": {"start": 0, "components": components}
                }
                
                if block.get("description", "").strip():
                    block_data["description"] = {"DE": block["description"]}
                
                blocks_for_validation[str(block_idx)] = block_data
                block_idx += 1
            
            # Add standalone questions
            if state["temp"].get("standalone_questions"):
                questions_dict = {}
                for q_idx, q in enumerate(state["temp"]["standalone_questions"]):
                    question_obj = {
                        "question": {"DE": q["question"]},
                        "question_type": q["type"],
                        "settings": {"mandatory": False, "grid": False},
                        "config": {},
                        "analysis_mode": "FREE"
                    }
                    
                    if q["type"] in ["ChoiceSingle", "ChoiceMulti"]:
                        options_dict = {str(i): {"DE": opt} for i, opt in enumerate(q["options"])}
                        question_obj["config"]["option_type"] = "TEXT"
                        question_obj["config"]["options"] = options_dict
                    elif q["type"] == "Rating":
                        question_obj["config"]["min"] = q.get("rating_min", 0)
                        question_obj["config"]["max"] = q.get("rating_max", 100)
                    
                    questions_dict[str(q_idx)] = question_obj
                
                num_questions = len(state["temp"]["standalone_questions"])
                components = {}
                for i in range(num_questions):
                    components[str(i)] = {"default": -1 if i == num_questions - 1 else i + 1}
                
                blocks_for_validation[str(block_idx)] = {
                    "title": {"DE": "Additional Questions"},
                    "description": {"DE": "Standalone questions"},
                    "questions": questions_dict,
                    "analysis_mode": "FREE",
                    "structure": {"start": 0, "components": components}
                }
            
            # Validate full survey
            survey_config = {
                "title": {"DE": state["temp"]["title"]},
                "creator": state["temp"]["email"]
            }
            if state["temp"].get("description", "").strip():
                survey_config["description"] = {"DE": state["temp"]["description"]}
            
            validation_result = validator.validate_full_survey(survey_config, blocks_for_validation)
            
            if not validation_result.success:
                messages.append({"from": "VoteBot", "text": (
                    "<strong>⚠️ Validation Failed:</strong>\\n\\n"
                    + "\\n".join([f"❌ {err}" for err in validation_result.errors]) +
                    "\\n\\nPlease fix these issues before creating the survey.\\n"
                    "Type 'cancel' to discard or fix the issues by adding/editing questions."
                )})
                return jsonify(messages=messages)
            
            # Validation passed, create the survey
            messages.append({"from": "VoteBot", "text": "<strong>✅ Validation passed! Creating survey...</strong>"})
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
            "3. Rating (0-100 scale)"
        )})
    elif cmd == "cancel":
        ROOMS[room]["pending_create"] = None
        messages.append({"from": "VoteBot", "text": "Survey creation cancelled."})
    else:
        messages.append({"from": "VoteBot", "text": "Type <strong>done</strong>, <strong>add block</strong>, <strong>add question</strong>, or <strong>cancel</strong>"})
    
    return jsonify(messages=messages)
