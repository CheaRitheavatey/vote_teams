# /api/message = POST
from flask import Flask, render_template, request, jsonify
from api.fetch_question import fetch_question, fetch_surveys
from api.submit_answer import submit_answer
from api.create_survey import create_survey
from api.get_result import get_survey_results

import uuid


app = Flask(__name__)

# maps room_id -> state dict
ROOMS = {
    "demo": {
        "pending_create": None,   # used when the bot is in create-survey flow
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
    payload = request.json
    room = "demo"
    user = payload.get("user", "User")
    text = (payload.get("text") or "").strip()

    # append user message for frontend
    messages = []
    messages.append({"from": user, "text": text})

    # Simple command parsing:
    if text.lower().startswith("/votebot create"):
        # start interactive create flow
        ROOMS[room]["pending_create"] = {"step": "ask_title", "temp": {}}
        bot_text = "Sure — what's the survey title?"
        messages.append({"from": "VoteBot", "text": bot_text})
        return jsonify(messages=messages)

    # Continue interactive create flow
    state = ROOMS[room].get("pending_create")
    if state:
        step = state["step"]

        # Ask title
        if step == "ask_title":
            state["temp"]["title"] = text
            state["step"] = "ask_question"
            messages.append({"from": "VoteBot", "text": "Great. What's the question?"})
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
            qtype = "Single Choice" if state["temp"]["qtype"] == "ChoiceSingle" else "Multiple Choice"
            options_text = "\n".join([f"- {o}" for o in opts])

            overview = (
                "Here is your survey overview:\n\n"
                f"**Title:** {title}\n"
                f"**Question:** {question}\n"
                f"**Type:** {qtype}\n"
                f"**Options:**\n{options_text}\n\n"
                "Type **done** to finalize.\n"
                "Type **edit title**, **edit question**, **edit type**, or **edit options** to modify.\n"
                "Type **cancel** to stop."
            )

            messages.append({"from": "VoteBot", "text": overview})
            return jsonify(messages=messages)
        
        # confirmation phase
        if step == "confirm_overview":
            cmd = text.lower()

            if cmd == "done":
                t = state["temp"]
                response = create_survey(t["title"], t["question"], t["qtype"], t["options"])
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
    qtype = "Single Choice" if state["temp"]["qtype"] == "ChoiceSingle" else "Multiple Choice"
    options_text = "\n".join([f"- {o}" for o in state["temp"]["options"]])

    overview = (
        "Here is your survey overview:\n\n"
        f"**Title:** {title}\n"
        f"**Question:** {question}\n"
        f"**Type:** {qtype}\n"
        f"**Options:**\n{options_text}\n\n"
        "Type **done** to finalize.\n"
        "Type **edit title**, **edit question**, **edit type**, or **edit options** to modify.\n"
        "Type **cancel** to stop."
    )
    return overview

if __name__ == "__main__":
    app.run(debug=True)

