"""
Quick survey creation workflow handlers
"""
from flask import jsonify
from api.create_survey import create_survey


def handle_quick_mode_selection(state, messages):
    """Handle quick mode selection"""
    state["step"] = "ask_email"
    messages.append({"from": "VoteBot", "text": "Let's create your survey!\n\n<strong>Your email?</strong>"})
    return jsonify(messages=messages)


def handle_quick_email(text, state, messages):
    """Handle email input for quick mode"""
    if "@" not in text or "." not in text:
        messages.append({"from": "VoteBot", "text": "Please enter a valid email address (must contain @ and a domain)."})
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
    messages.append({"from": "VoteBot", "text": "Single choice or multiple choice?\nReply 1 for Single / 2 for Multiple."})
    return jsonify(messages=messages)


def handle_quick_type(text, state, messages):
    """Handle question type selection"""
    state["temp"]["qtype"] = "ChoiceSingle" if text.strip() == "1" else "ChoiceMulti"
    state["step"] = "ask_options"
    messages.append({"from": "VoteBot", "text": "Enter options separated by commas (e.g. red,blue,green)."})
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
        "Type <strong>cancel</strong> to stop."
    )

    messages.append({"from": "VoteBot", "text": overview})
    return jsonify(messages=messages)


def handle_quick_confirmation(text, state, messages, room, ROOMS):
    """Handle survey confirmation and creation"""
    cmd = text.lower()

    if cmd == "done":
        t = state["temp"]
        response = create_survey(t["title"], t["question"], t["qtype"], t["options"], t["email"])
        enter_code = response.get("enter_code")

        ROOMS[room]["last_survey_code"] = enter_code
        ROOMS[room]["pending_create"] = None

        messages.append({"from": "VoteBot", "text": (
            f"<strong>Survey created!</strong>\n\n"
            f"<strong>Survey Code:</strong> {enter_code}\n\n"
            "Type 'create' to make another survey."
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
        messages.append({"from": "VoteBot", "text": "Survey creation cancelled."})
        return jsonify(messages=messages)

    else:
        messages.append({"from": "VoteBot", "text": "Type <strong>done</strong>, <strong>edit [field]</strong>, or <strong>cancel</strong>."})
        return jsonify(messages=messages)
