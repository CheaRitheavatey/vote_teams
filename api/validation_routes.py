"""
Flask route examples for integrating the validation system.
Add these routes to your app.py or create a separate blueprint.
"""

from flask import Blueprint, request, jsonify
from api.validation import (
    validate_question_preview,
    validate_block_preview,
    validate_survey_preview,
    validate_interactive_preview
)

# Create a blueprint (or add directly to your main app)
validation_bp = Blueprint('validation', __name__, url_prefix='/api/validation')


@validation_bp.route('/question', methods=['POST'])
def validate_question():
    """
    Validate a question at preview checkpoint.
    
    Request body:
    {
        "question_data": {
            "question": {"DE": "Question text?"},
            "config": {
                "option_type": "TEXT",
                "options": {
                    "0": {"DE": "Option 1"},
                    "1": {"DE": "Option 2"}
                }
            },
            "settings": {"mandatory": true}
        },
        "question_type": "ChoiceSingle",
        "language": "DE"
    }
    
    Response:
    {
        "success": true/false,
        "message": "User-friendly message",
        "errors": ["error1", "error2"],
        "warnings": ["warning1"]
    }
    """
    try:
        data = request.json
        
        question_data = data.get('question_data')
        question_type = data.get('question_type')
        language = data.get('language', 'DE')
        
        if not question_data or not question_type:
            return jsonify({
                "success": False,
                "message": "Missing required fields: question_data and question_type",
                "errors": ["Invalid request format"]
            }), 400
        
        # Validate
        result = validate_question_preview(question_data, question_type, language)
        
        return jsonify({
            "success": result.success,
            "message": result.get_user_message(),
            "errors": result.errors,
            "warnings": result.warnings,
            "data": result.data
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Validation error: {str(e)}",
            "errors": [str(e)]
        }), 500


@validation_bp.route('/block', methods=['POST'])
def validate_block():
    """
    Validate a question block at preview checkpoint.
    
    Request body:
    {
        "block_data": {
            "title": {"DE": "Block title"},
            "description": {"DE": "Block description"}
        },
        "questions": [
            {
                "question": {"DE": "Question?"},
                "question_type": "ChoiceSingle",
                "config": {...},
                "settings": {...}
            }
        ],
        "language": "DE"
    }
    """
    try:
        data = request.json
        
        block_data = data.get('block_data')
        questions = data.get('questions', [])
        language = data.get('language', 'DE')
        
        if not block_data:
            return jsonify({
                "success": False,
                "message": "Missing required field: block_data",
                "errors": ["Invalid request format"]
            }), 400
        
        # Validate
        result = validate_block_preview(block_data, questions, language)
        
        return jsonify({
            "success": result.success,
            "message": result.get_user_message(),
            "errors": result.errors,
            "warnings": result.warnings,
            "data": result.data
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Validation error: {str(e)}",
            "errors": [str(e)]
        }), 500


@validation_bp.route('/survey', methods=['POST'])
def validate_survey():
    """
    Validate complete survey at final preview checkpoint.
    
    Request body:
    {
        "survey_config": {
            "title": {"DE": "Survey title"},
            "description": {"DE": "Description"},
            "settings": {...}
        },
        "blocks": {
            "0": {
                "title": {"DE": "Block 1"},
                "questions": {...}
            }
        },
        "language": "DE"
    }
    """
    try:
        data = request.json
        
        survey_config = data.get('survey_config')
        blocks = data.get('blocks', {})
        language = data.get('language', 'DE')
        
        if not survey_config or not blocks:
            return jsonify({
                "success": False,
                "message": "Missing required fields: survey_config and blocks",
                "errors": ["Invalid request format"]
            }), 400
        
        # Validate
        result = validate_survey_preview(survey_config, blocks, language)
        
        return jsonify({
            "success": result.success,
            "message": result.get_user_message(),
            "errors": result.errors,
            "warnings": result.warnings,
            "data": result.data
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Validation error: {str(e)}",
            "errors": [str(e)]
        }), 500


@validation_bp.route('/interactive', methods=['POST'])
def validate_interactive():
    """
    Validate interactive module (Q&A, Word Cloud).
    
    Request body:
    {
        "module_type": "QnA",
        "module_data": {
            "topic": {"DE": "Q&A topic"},
            "settings": {...}
        },
        "language": "DE"
    }
    """
    try:
        data = request.json
        
        module_type = data.get('module_type')
        module_data = data.get('module_data')
        language = data.get('language', 'DE')
        
        if not module_type or not module_data:
            return jsonify({
                "success": False,
                "message": "Missing required fields: module_type and module_data",
                "errors": ["Invalid request format"]
            }), 400
        
        # Validate
        result = validate_interactive_preview(module_type, module_data, language)
        
        return jsonify({
            "success": result.success,
            "message": result.get_user_message(),
            "errors": result.errors,
            "warnings": result.warnings,
            "data": result.data
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Validation error: {str(e)}",
            "errors": [str(e)]
        }), 500


# ==================== HELPER ROUTES ====================

@validation_bp.route('/health', methods=['GET'])
def health_check():
    """Check if validation service is available."""
    return jsonify({
        "status": "ok",
        "service": "validation",
        "endpoints": [
            "/api/validation/question",
            "/api/validation/block",
            "/api/validation/survey",
            "/api/validation/interactive"
        ]
    })


# ==================== USAGE INSTRUCTIONS ====================

"""
To integrate this into your app.py:

1. Import the blueprint:
   from api.validation_routes import validation_bp

2. Register the blueprint:
   app.register_blueprint(validation_bp)

3. Use from frontend or chatbot:
   
   // Example: Validate question from JavaScript
   fetch('/api/validation/question', {
       method: 'POST',
       headers: {'Content-Type': 'application/json'},
       body: JSON.stringify({
           question_data: {
               question: {"DE": "Your question?"},
               config: {
                   option_type: "TEXT",
                   options: {
                       "0": {"DE": "Option 1"},
                       "1": {"DE": "Option 2"}
                   }
               },
               settings: {mandatory: true}
           },
           question_type: "ChoiceSingle",
           language: "DE"
       })
   })
   .then(res => res.json())
   .then(result => {
       if (result.success) {
           console.log("[SUCCESS] Validated!");
           enableConfirmButton();
       } else {
           console.log("[ERROR] Errors:", result.errors);
           showErrors(result.errors);
       }
   });
   
   # Example: Validate from chatbot flow
   import requests
   
   response = requests.post('http://localhost:5000/api/validation/question', json={
       'question_data': question_data,
       'question_type': 'ChoiceSingle',
       'language': 'DE'
   })
   
   result = response.json()
   if result['success']:
       bot_message = "[SUCCESS] Question validated! You can proceed."
   else:
       bot_message = "[ERROR] Please fix these issues:\n" + "\n".join(result['errors'])
"""
