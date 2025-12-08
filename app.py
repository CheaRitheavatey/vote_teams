"""
Vote Teams - Survey Creation Chatbot
Main Flask application with modular workflow handlers
"""
from flask import Flask, render_template, request, jsonify
from api.fetch_question import fetch_question, fetch_surveys, fetch_survey_list
from api.submit_answer import submit_answer, fetch_vote_structure, get_next_question
from api.get_result import get_survey_results
from api.validation import SurveyValidator

# Import workflow modules
from workflow.advanced_helpers import send_question_preview, send_advanced_overview
from workflow.advanced_mode import (
    handle_advanced_mode_selection, handle_advanced_email,
    handle_advanced_title, handle_advanced_description,
    handle_advanced_language
)
from workflow.advanced_steps import (
    handle_block_selection, handle_block_title, handle_block_description,
    handle_question_type, handle_question_text, handle_question_options,
    handle_rating_min, handle_rating_max, handle_question_confirm,
    handle_more_questions_in_block, handle_more_standalone, handle_more_blocks,
    handle_standalone_after_blocks, handle_advanced_overview
)
from workflow.quick_mode import (
    handle_quick_mode_selection, handle_quick_email, handle_quick_title,
    handle_quick_question, handle_quick_type, handle_quick_options,
    handle_quick_rating_min, handle_quick_rating_max,
    handle_quick_confirmation
)
from workflow.survey_api import create_advanced_survey

app = Flask(__name__)

# Initialize validator
validator = SurveyValidator()

# State management: maps room_id -> state dict
ROOMS = {
    "demo": {
        "pending_create": None,
        "last_survey_code": None,
        "pending_confirmation": None,
        "pending_vote_for_code": None
    }
}

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/message", methods=["POST"])
def api_message():
    """Main message handler - routes to appropriate workflow"""
    payload = request.json
    room = "demo"
    user = payload.get("user", "User")
    text = (payload.get("text") or "").strip()

    messages = []
    messages.append({"from": user, "text": text})

    if room not in ROOMS:
        ROOMS[room] = {
            "pending_create": None,
            "last_survey_code": None,
            "pending_confirmation": None,
            "pending_vote_for_code": None
        }

    state = ROOMS[room].get("pending_create")
    
    # Parse command with parameters
    text_lower = text.lower()
    parts = text_lower.split(maxsplit=1)
    command = parts[0] if parts else ""
    param = parts[1] if len(parts) > 1 else None

    # === VOTE FLOW ===
    # Handle "vote" or "vote <code>"
    if command == "vote":
        if param:
            # Direct vote with code
            enter_code = param.strip()
            
            blocks = fetch_vote_structure(enter_code)
            
            if not blocks:
                messages.append({"from": "VoteBot", "text": "Survey has no questions."})
                return jsonify(messages=messages)
            
            # calculate the total num of question to disply
            block_ids = sorted(blocks.keys(), key=lambda x: int(x))
            # get the first block in sorted order
            current_block = block_ids[0]
            
            
            question_ids = sorted(blocks[current_block]["questions"].keys(), key=lambda x: int(x))
            current_question = question_ids[0]
            
            current_index = question_ids.index(current_question)
            total_questions = len(question_ids)
            

            display_text = f"block: {int(current_block) + 1} - Question {current_index + 1} ({current_index + 1}/{total_questions})"
            # messages.append({"from": "VoteBot", "text": display_text})

            # fetch this question
            data = fetch_question(enter_code, current_block, current_question)
            
            ROOMS[room]["pending_confirmation"] = {
                "code": enter_code,
                "block": current_block,
                "question": current_question,
                "type": data.get("question_type", "")
            }

            # get next question
            
            if data:
                question_type = data.get("question_type", "")
                ROOMS[room]["pending_confirmation"] = {"code": enter_code, "block": "0", "question": "0", "type": question_type}
                
                question_text = data["question"]["DE"]
                
                # Handle different question types
                if question_type == "RangeSlider":
                    range_config = data["config"].get("range_config", {})
                    min_val = range_config.get("min", 0)
                    max_val = range_config.get("max", 100)
                    messages.append({"from": "VoteBot", "text": f"{display_text}\n\n<strong>Question:</strong> {question_text}\n\n<strong>Range:</strong> {min_val} to {max_val}\n\nEnter a number between {min_val} and {max_val}:"})
                elif question_type == "TextQuestion":
                    messages.append({"from": "VoteBot", "text": f"{display_text}\n\n<strong>Question:</strong> {question_text}\n\nEnter your text answer:"})
                else:
                    # choicesingle or choicemulti
                    options = [v["DE"] for k, v in data["config"]["options"].items()]
                    options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(options)])
                    
                    # calculate block quesiton
                    blocks = fetch_vote_structure(conf["code"])
                    question_ids = sorted(blocks[conf["block"]]["questions"].keys(), key=lambda x: int(x))

                    current_index = question_ids.index(conf["question"])
                    total_questions = len(question_ids)

                    header_text = f"<strong>Block {int(conf['block'])+1} — Question {current_index+1} ({current_index+1}/{total_questions})</strong>"
                    messages.append({"from": "VoteBot", "text": 
                        
                        f"{header_text}<br><br>"
                        f"{question_type}<br><br>"
                        f"<strong>Question:</strong> {question_text}\n\n{options_text}\n\nEnter your choice (number):"})
            else:
                messages.append({"from": "VoteBot", "text": f"Error: Survey code '{enter_code}' not found."})
        else:
            # List available surveys
            available_surveys = fetch_survey_list()
            if not available_surveys:
                messages.append({"from": "VoteBot", "text": "No surveys available right now."})
            else:
                survey_list = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(available_surveys)])
                ROOMS[room]["pending_vote_for_code"] = available_surveys
                messages.append({"from": "VoteBot", "text": f"Available surveys:\n{survey_list}\n\nEnter survey number to vote:"})
        return jsonify(messages=messages)

    if ROOMS[room].get("pending_vote_for_code"):
        try:
            idx = int(text) - 1
            surveys = ROOMS[room]["pending_vote_for_code"]
            if 0 <= idx < len(surveys):
                enter_code = surveys[idx]["enter_code"]
                ROOMS[room]["pending_vote_for_code"] = None
                
                data = fetch_question(enter_code, "0", "0")
                if data:
                    question_type = data.get("question_type", "")
                    ROOMS[room]["pending_confirmation"] = {"code": enter_code, "block": "0", "question": "0", "type": question_type}
                    
                    question_text = data["question"]["DE"]
                    
                    # Handle different question types
                    if question_type == "RangeSlider":
                        range_config = data["config"].get("range_config", {})
                        min_val = range_config.get("min", 0)
                        max_val = range_config.get("max", 100)
                        messages.append({"from": "VoteBot", "text": f"<strong>Question:</strong> {question_text}\n\n<strong>Range:</strong> {min_val} to {max_val}\n\nEnter a number between {min_val} and {max_val}:"})
                    elif question_type == "TextQuestion":
                        messages.append({"from": "VoteBot", "text": f"<strong>Question:</strong> {question_text}\n\nEnter your text answer:"})
                    else:
                        # ChoiceSingle or ChoiceMulti
                        options = [v["DE"] for k, v in data["config"]["options"].items()]
                        options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(options)])
                        messages.append({"from": "VoteBot", "text": f"<strong>Question:</strong> {question_text}\n\n{options_text}\n\nEnter your choice (number):"})
                else:
                    messages.append({"from": "VoteBot", "text": "Error fetching question."})
            else:
                messages.append({"from": "VoteBot", "text": "Invalid number."})
        except ValueError:
            messages.append({"from": "VoteBot", "text": "Please enter a valid number."})
        return jsonify(messages=messages)
    if ROOMS[room].get("pending_confirmation"):
        conf = ROOMS[room]["pending_confirmation"]
        code = conf["code"]
        block = conf["block"]
        q = conf["question"]
        q_type = conf["type"]

        # Submit answer
        try:
            if q_type == "TextQuestion":
                answer_payload = [text]
            else:
                answer_payload = [int(text)]

            result = submit_answer(code, block, q, answer_payload)
        except ValueError:
            messages.append({"from": "VoteBot", "text": "Please enter a valid answer."})
            return jsonify(messages=messages)

         # Load structure to find next question
        blocks = fetch_vote_structure(code)
        next_block, next_q = get_next_question(blocks, block, q)

        if next_block is None:
            # No more questions → finish survey
            ROOMS[room]["pending_confirmation"] = None
            messages.append({"from": "VoteBot", "text": "🎉 All questions answered! Thank you!"})
            return jsonify(messages=messages)

        # There IS another question → load it
        data = fetch_question(code, next_block, next_q)
        q_type = data["question_type"]

        ROOMS[room]["pending_confirmation"] = {
            "code": code,
            "block": next_block,
            "question": next_q,
            "type": q_type
        }

        question_text = data["question"]["DE"]

        # Display next question
        if q_type == "RangeSlider":
            c = data["config"]["range_config"]
            messages.append({
                "from": "VoteBot",
                "text":
                    f"<strong>Question:</strong> {question_text}<br>"
                    f"Range: {c['min']}–{c['max']}<br>"
                    "Enter a number:"
            })

        elif q_type == "TextQuestion":
            messages.append({
                "from": "VoteBot",
                "text": f"<strong>Question:</strong> {question_text}<br>Enter text:"
            })

        else:
            options = data["config"]["options"]
            text_opts = "<br>".join([f"{i}. {opt['DE']}" for i, opt in options.items()])
            messages.append({
                "from": "VoteBot",
                "text":
                    f"<strong>Question:</strong> {question_text}<br>{text_opts}<br>"
                    "Enter your choice number:"
            })

        return jsonify(messages=messages)


    # if ROOMS[room].get("pending_confirmation"):
    #     conf = ROOMS[room]["pending_confirmation"]
    #     question_type = conf.get("type", "")
        
    #     if question_type == "TextQuestion":
    #         # For TextQuestion, submit the raw text
    #         result = submit_answer(conf["code"], conf["block"], conf["question"], [text])
    #         ROOMS[room]["pending_confirmation"] = None
            
    #         if result:
    #             messages.append({"from": "VoteBot", "text": "✅ Your answer has been submitted!"})
    #         else:
    #             messages.append({"from": "VoteBot", "text": "❌ Failed to submit answer."})
    #     else:
    #         # For RangeSlider and choice questions, parse as number
    #         try:
    #             if question_type == "RangeSlider":
    #                 # For RangeSlider, submit the actual number value as a single-item list
    #                 value = int(text)
    #                 result = submit_answer(conf["code"], conf["block"], conf["question"], [value])
    #             else:
    #                 # For choice questions, submit the choice index
    #                 choice = int(text)
    #                 result = submit_answer(conf["code"], conf["block"], conf["question"], [choice])
                
    #             ROOMS[room]["pending_confirmation"] = None
                
    #             if result:
    #                 messages.append({"from": "VoteBot", "text": "✅ Your vote has been submitted!"})
    #             else:
    #                 messages.append({"from": "VoteBot", "text": "❌ Failed to submit vote."})
    #         except ValueError:
    #             messages.append({"from": "VoteBot", "text": "Please enter a valid number."})
    #     return jsonify(messages=messages)

    # === RESULTS FLOW ===
    # Handle "result" or "result <code>"
    if command == "result":
        if param:
            # Get results for specific code
            survey_code = param.strip()
            results_data = get_survey_results(survey_code, "0", "0")
            messages.append({"from": "VoteBot", "text": results_data})
        else:
            # Get results for last created survey
            last_code = ROOMS[room].get("last_survey_code")
            if last_code:
                results_data = get_survey_results(last_code, "0", "0")
                messages.append({"from": "VoteBot", "text": results_data})
            else:
                messages.append({"from": "VoteBot", "text": "No survey created yet. Use 'result <code>' to get results for a specific survey."})
        return jsonify(messages=messages)
    
    # === FETCH SURVEYS ===
    # Handle "fetch" to list all available surveys
    if command == "fetch":
        available_surveys = fetch_survey_list()
        if not available_surveys:
            messages.append({"from": "VoteBot", "text": "No surveys available right now."})
        else:
            survey_list = "\n".join([
                f"• <strong>{s['title']}</strong> (Code: {s['enter_code']})"
                for s in available_surveys
            ])
            messages.append({"from": "VoteBot", "text": f"<strong>Available Surveys:</strong>\n\n{survey_list}\n\nUse 'vote <code>' to participate."})
        return jsonify(messages=messages)

    # === CREATE SURVEY FLOW ===
    if command == "create":
        ROOMS[room]["pending_create"] = {"step": "ask_mode", "temp": {}}
        messages.append({"from": "VoteBot", "text": (
            "<strong>Create a New Survey</strong>\n\n"
            "Choose mode:\n"
            "1. <strong>Quick</strong> - Simple survey with one question\n"
            "2. <strong>Advanced</strong> - Full control with blocks and multiple questions\n\n"
            "Reply with 1 or 2"
        )})
        return jsonify(messages=messages)

    # === SURVEY CREATION WORKFLOW ===
    if state:
        step = state.get("step")
        
        # Mode selection
        if step == "ask_mode":
            if text.strip() == "1":
                state["temp"]["mode"] = "quick"
                return handle_quick_mode_selection(state, messages)
            elif text.strip() == "2":
                state["temp"]["mode"] = "advanced"
                return handle_advanced_mode_selection(state, messages)
            else:
                messages.append({"from": "VoteBot", "text": "Please reply with 1 for Quick or 2 for Advanced"})
                return jsonify(messages=messages)
        
        # Route to appropriate mode handler
        mode = state["temp"].get("mode")
        
        if mode == "quick":
            return handle_quick_workflow(step, text, state, messages, room)
        elif mode == "advanced":
            return handle_advanced_workflow(step, text, state, messages, room)

    # === DEFAULT ===
    # Show menu if just "votebot" or unrecognized command
    if text_lower in ["votebot", "help", "menu", ""]:
        messages.append({"from": "VoteBot", "text": (
            "<strong>VoteBot Commands:</strong>\n\n"
            "• <strong>create</strong> - Create a new survey\n"
            "• <strong>vote</strong> - List available surveys\n"
            "• <strong>vote &lt;code&gt;</strong> - Vote in specific survey\n"
            "• <strong>result</strong> - Results of your last survey\n"
            "• <strong>result &lt;code&gt;</strong> - Results of specific survey\n"
            "• <strong>fetch</strong> - List all available surveys\n"
            "• <strong>help</strong> - Show this menu"
        )})
    else:
        messages.append({"from": "VoteBot", "text": (
            "Command not recognized. Type <strong>help</strong> to see available commands."
        )})
    return jsonify(messages=messages)


def handle_quick_workflow(step, text, state, messages, room):
    """Handle quick mode workflow steps"""
    from workflow.quick_mode import (
        handle_quick_email, handle_quick_title, handle_quick_question,
        handle_quick_type, handle_quick_options, handle_quick_confirmation
    )
    
    if step == "ask_email":
        return handle_quick_email(text, state, messages)
    elif step == "ask_title":
        return handle_quick_title(text, state, messages)
    elif step == "ask_question":
        return handle_quick_question(text, state, messages)
    elif step == "ask_type":
        return handle_quick_type(text, state, messages)
    elif step == "ask_rating_min":
        return handle_quick_rating_min(text, state, messages)
    elif step == "ask_rating_max":
        return handle_quick_rating_max(text, state, messages)
    elif step == "ask_options":
        return handle_quick_options(text, state, messages)
    elif step == "confirm_overview":
        return handle_quick_confirmation(text, state, messages, room, ROOMS)
    
    return jsonify(messages=messages)


def handle_advanced_workflow(step, text, state, messages, room):
    """Handle advanced mode workflow steps"""
    
    # Global settings steps
    if step == "ask_email":
        return handle_advanced_email(text, state, messages, validator)
    elif step == "advanced_title":
        return handle_advanced_title(text, state, messages)
    elif step == "advanced_description":
        return handle_advanced_description(text, state, messages)
    elif step == "advanced_language":
        return handle_advanced_language(text, state, messages, validator)
    
    # Block and question creation steps
    elif step == "advanced_ask_block":
        return handle_block_selection(text, state, messages)
    elif step == "block_title":
        return handle_block_title(text, state, messages)
    elif step == "block_description":
        return handle_block_description(text, state, messages)
    elif step == "select_question_type":
        return handle_question_type(text, state, messages)
    elif step == "question_text":
        return handle_question_text(text, state, messages)
    elif step == "question_options":
        return handle_question_options(text, state, messages)
    elif step == "rating_min":
        return handle_rating_min(text, state, messages)
    elif step == "rating_max":
        return handle_rating_max(text, state, messages)
    elif step == "question_confirm":
        return handle_question_confirm(text, state, messages)
    elif step == "ask_more_questions_in_block":
        return handle_more_questions_in_block(text, state, messages)
    elif step == "ask_more_standalone":
        return handle_more_standalone(text, state, messages)
    elif step == "ask_more_blocks":
        return handle_more_blocks(text, state, messages)
    elif step == "ask_standalone_after_blocks":
        return handle_standalone_after_blocks(text, state, messages)
    elif step == "advanced_overview":
        return handle_advanced_overview(text, state, messages, room)
    
    return jsonify(messages=messages)


if __name__ == "__main__":
    app.run(debug=True)
