"""
Helper functions for advanced survey creation mode
"""

def send_question_preview(state, validator):
    """Generate a preview of the current question with validation"""
    q = state["temp"]["current_question"]
    q_type = q["type"]
    question_text = q.get("question", "")
    
    preview = f"<strong>Question Preview:</strong>\n\n{question_text}\n<strong>Type:</strong> {q_type}\n"
    
    if "options" in q:
        preview += "<strong>Options:</strong>\n" + "\n".join([f"- {opt}" for opt in q["options"]])
    elif q_type == "RangeSlider" and "rating_min" in q:
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
    
    elif q_type == "RangeSlider":
        if "rating_min" in q and "rating_max" in q:
            min_val = q["rating_min"]
            max_val = q["rating_max"]
            question_data_for_validation["config"]["range_config"] = {
                "min": min_val,
                "max": max_val,
                "start": str(min_val),
                "end": str(max_val),
                "stepsize": 1
            }
    
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
        elif q_type == "RangeSlider":
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
        "\n\n<strong>Commands:</strong>\n"
        "• <strong>done</strong> - Create the survey\n"
        "• <strong>add block</strong> - Add another question block\n"
        "• <strong>add question</strong> - Add standalone question\n"
        "• <strong>cancel</strong> - Discard this survey"
    )
    
    return overview
