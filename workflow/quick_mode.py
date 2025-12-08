"""
Quick mode survey creation workflow
"""
import re
from flask import jsonify
from api.create_survey import create_survey


def handle_quick_mode_selection(state, messages):
    """Initialize quick mode workflow"""
    state["step"] = "ask_email"
    messages.append({"from": "VoteBot", "text": "Let's create your survey!\n\n<strong>Your email?</strong>"})
    return jsonify(messages=messages)


def handle_quick_email(text, state, messages):
    """Handle email input for quick mode"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@telekom\.(com|de)$'
    if not re.fullmatch(email_pattern, text.strip()):
        messages.append({"from": "VoteBot", "text": "Please enter a valid email address. Only @telekom.com or @telekom.de domains are allowed."})
        return jsonify(messages=messages)
    
    state["temp"]["email"] = text.strip()
    state["step"] = "ask_title"
    messages.append({"from": "VoteBot", "text": "Great! Now, what's the survey title?"})
    return jsonify(messages=messages)


def handle_quick_title(text, state, messages):
    """Handle survey title input"""
    state["temp"]["title"] = text
    state["step"] = "ask_question"
    messages.append({"from": "VoteBot", "text": "What's your question?"})
    return jsonify(messages=messages)


def handle_quick_question(text, state, messages):
    """Handle question input"""
    state["temp"]["question"] = text
    state["step"] = "ask_type"
    messages.append({"from": "VoteBot", "text": (
        "What type of question?\n\n"
        "1. Single Choice\n"
        "2. Multiple Choice\n"
        "3. Rating (0-100 scale)\n"
        "4. Free Text"
    )})
    return jsonify(messages=messages)


def handle_quick_type(text, state, messages):
    """Handle question type selection"""
    type_map = {
        "1": "ChoiceSingle",
        "2": "ChoiceMulti",
        "3": "RangeSlider",
        "4": "TextQuestion"
    }
    
    if text.strip() not in type_map:
        messages.append({"from": "VoteBot", "text": "Please select a valid option (1-4)"})
        return jsonify(messages=messages)
    
    state["temp"]["qtype"] = type_map[text.strip()]
    
    # Branch based on question type
    if state["temp"]["qtype"] in ["ChoiceSingle", "ChoiceMulti"]:
        state["step"] = "ask_options"
        messages.append({"from": "VoteBot", "text": "Enter options separated by commas (e.g. red,blue,green)."})
    elif state["temp"]["qtype"] == "RangeSlider":
        state["step"] = "ask_rating_min"
        messages.append({"from": "VoteBot", "text": "Minimum rating value? (e.g., 0)"})
    elif state["temp"]["qtype"] == "TextQuestion":
        # TextQuestion has no config, go straight to preview
        state["step"] = "confirm_overview"
        title = state["temp"]["title"]
        question = state["temp"]["question"]
        email = state["temp"]["email"]
        
        overview = (
            "Here is your survey overview:\n\n"
            f"<strong>Creator Email:</strong> {email}\n"
            f"<strong>Title:</strong> {title}\n"
            f"<strong>Question:</strong> {question}\n"
            f"<strong>Type:</strong> Free Text\n\n"
            "Type <strong>done</strong> to finalize.\n"
            "Type <strong>edit title</strong>, <strong>edit question</strong>, or <strong>edit type</strong> to modify.\n"
            "Type <strong>cancel</strong> to stop."
        )
        messages.append({"from": "VoteBot", "text": overview})
    
    return jsonify(messages=messages)


def handle_quick_rating_min(text, state, messages):
    """Handle rating minimum value"""
    try:
        min_val = int(text)
        state["temp"]["rating_min"] = min_val
        state["step"] = "ask_rating_max"
        messages.append({"from": "VoteBot", "text": "Maximum rating value? (e.g., 100)"})
    except ValueError:
        messages.append({"from": "VoteBot", "text": "Please enter a valid number."})
    return jsonify(messages=messages)


def handle_quick_rating_max(text, state, messages):
    """Handle rating maximum value"""
    try:
        max_val = int(text)
        min_val = state["temp"]["rating_min"]
        
        if max_val <= min_val:
            messages.append({"from": "VoteBot", "text": f"Maximum must be greater than minimum ({min_val})."})
            return jsonify(messages=messages)
        
        state["temp"]["rating_max"] = max_val
        state["step"] = "confirm_overview"
        
        # Generate preview
        title = state["temp"]["title"]
        question = state["temp"]["question"]
        email = state["temp"]["email"]
        
        overview = (
            "Here is your survey overview:\n\n"
            f"<strong>Creator Email:</strong> {email}\n"
            f"<strong>Title:</strong> {title}\n"
            f"<strong>Question:</strong> {question}\n"
            f"<strong>Type:</strong> Rating Scale\n"
            f"<strong>Range:</strong> {min_val} to {max_val}\n\n"
            "Type <strong>done</strong> to finalize.\n"
            "Type <strong>edit title</strong>, <strong>edit question</strong>, or <strong>edit type</strong> to modify.\n"
            "Type <strong>cancel</strong> to stop."
        )
        messages.append({"from": "VoteBot", "text": overview})
    except ValueError:
        messages.append({"from": "VoteBot", "text": "Please enter a valid number."})
    return jsonify(messages=messages)


def handle_quick_options(text, state, messages):
    """Handle options input and generate overview"""
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
        "Type <strong>reset</strong> to start over or <strong>cancel</strong> to stop."
    )

    messages.append({"from": "VoteBot", "text": overview})
    return jsonify(messages=messages)


def handle_quick_confirmation(text, state, messages, room, ROOMS):
    """Handle survey confirmation and creation"""
    cmd = text.lower()

    if cmd == "done":
        t = state["temp"]
        
        # Prepare options/config based on question type
        if t["qtype"] in ["ChoiceSingle", "ChoiceMulti"]:
            options_or_config = t["options"]
        elif t["qtype"] == "RangeSlider":
            options_or_config = {"min": t["rating_min"], "max": t["rating_max"]}
        else:  # TextQuestion
            options_or_config = {}
        
        response = create_survey(t["title"], t["question"], t["qtype"], options_or_config, t["email"])
        enter_code = response.get("enter_code")

        ROOMS[room]["last_survey_code"] = enter_code
        ROOMS[room]["pending_create"] = None
        state["step"] = "main"  # Reset to main menu

        messages.append({"from": "VoteBot", "text": (
            f"<strong>Survey created!</strong>\n\n"
            f"<strong>Survey Code:</strong> {enter_code}\n\n"
            "Type <strong>create</strong> to make another survey, "
            "<strong>vote {enter_code}</strong> to participate, or "
            "<strong>result {enter_code}</strong> to see results."
        )})
        return jsonify(messages=messages)

    elif cmd.startswith("edit "):
        part = cmd.replace("edit ", "")
        if part == "title":
            state["step"] = "ask_title"
            messages.append({"from": "VoteBot", "text": "Enter new title:"})
        elif part == "question":
            state["step"] = "ask_question"
            messages.append({"from": "VoteBot", "text": "Enter new question:"})
        elif part == "type":
            state["step"] = "ask_type"
            messages.append({"from": "VoteBot", "text": "Single choice or multiple choice?\nReply 1 for Single / 2 for Multiple."})
        elif part == "options":
            state["step"] = "ask_options"
            messages.append({"from": "VoteBot", "text": "Enter new options separated by commas:"})
        else:
            messages.append({"from": "VoteBot", "text": "Invalid edit command. Use: edit title, edit question, edit type, or edit options."})
        return jsonify(messages=messages)

    elif cmd == "cancel":
        ROOMS[room]["pending_create"] = None
        state["step"] = "main"
        messages.append({"from": "VoteBot", "text": "Survey creation cancelled. Type <strong>create</strong> to start a new survey."})
        return jsonify(messages=messages)
    
    elif cmd == "reset":
        # Clear all survey data and restart
        state["temp"] = {}
        state["step"] = "ask_mode"
        messages.append({"from": "VoteBot", "text": "Survey creation reset. Choose mode: <strong>quick</strong> or <strong>advanced</strong>"})
        return jsonify(messages=messages)

    else:
        messages.append({"from": "VoteBot", "text": "Type <strong>done</strong>, <strong>edit [field]</strong>, <strong>reset</strong>, or <strong>cancel</strong>."})
        return jsonify(messages=messages)
