"""
Advanced survey creation workflow handlers
"""
import re
from flask import jsonify


def handle_advanced_mode_selection(state, messages):
    """Handle mode selection step"""
    state["step"] = "ask_email"
    messages.append({"from": "VoteBot", "text": "Let's create your survey!\n\n📧 <strong>Your email?</strong>"})
    return jsonify(messages=messages)


def handle_advanced_email(text, state, messages, validator):
    """Handle email input for advanced mode"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@telekom\.(com|de)$'
    if not re.fullmatch(email_pattern, text.strip()):
        messages.append({"from": "VoteBot", "text": "⚠️ Please enter a valid email address. Only @telekom.com or @telekom.de domains are allowed."})
        return jsonify(messages=messages)
    
    state["temp"]["email"] = text.strip()
    
    # Branch to advanced mode
    state["step"] = "advanced_title"
    messages.append({"from": "VoteBot", "text": "Great! ✓\n\nLet's configure your survey.\n\n📝 <strong>Survey title?</strong>"})
    return jsonify(messages=messages)


def handle_advanced_title(text, state, messages):
    """Handle survey title input"""
    state["temp"]["title"] = text
    state["step"] = "advanced_description"
    messages.append({"from": "VoteBot", "text": "<strong>Description?</strong> (Optional - type 'skip' to skip)"})
    return jsonify(messages=messages)


def handle_advanced_description(text, state, messages):
    """Handle survey description input"""
    if text.lower() != "skip":
        state["temp"]["description"] = text
    state["step"] = "advanced_language"
    messages.append({"from": "VoteBot", "text": "🌍 <strong>Language?</strong>\n1. English\n2. German\n3. Both"})
    return jsonify(messages=messages)


def handle_advanced_language(text, state, messages, validator):
    """Handle language selection and validate global settings"""
    lang_map = {"1": "EN", "2": "DE", "3": "BOTH"}
    state["temp"]["language"] = lang_map.get(text.strip(), "EN")
    
    # Initialize question_blocks and standalone_questions
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
        state["step"] = "advanced_language"  # Allow retry
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
