"""
Modular validation system for survey creation workflow.
https://vote2.telekom.net/api/v1/doc#/Template/validate_api_v1_template_validator_put
"""

import requests
import os
import time
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta

load_dotenv()

BASE_URL = "https://vote2.telekom.net/api/v1"
VALIDATOR_ENDPOINT = f"{BASE_URL}/template/validator"
API_KEY = os.getenv("API_KEY")
ADMIN_PASS = os.getenv("ADMIN_PASS")

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

RATE_LIMIT_DELAY = 1.5  # Default delay in seconds between API calls to avoid 429 errors


class ValidationResult:
    
    def __init__(self, success: bool, errors: List[str] = None, warnings: List[str] = None, data: Dict = None):
        self.success = success
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data
        }
    
    def get_user_message(self) -> str:
        """Generate a user-friendly message from validation result."""
        if self.success:
            msg = "[SUCCESS] Validation successful!"
            if self.warnings:
                msg += f"\n[WARNING] Warnings:\n" + "\n".join(f"  - {w}" for w in self.warnings)
            return msg
        else:
            msg = "[ERROR] Validation failed. Please fix the following issues:\n"
            msg += "\n".join(f"  - {e}" for e in self.errors)
            return msg


class DummyDataGenerator:
    """Generates dummy/placeholder data to complete partial survey structures for validation."""
    
    @staticmethod
    def get_dummy_global_config() -> Dict:
        """Returns dummy global configuration."""
        return {
            "creator": "validation.test@telekom.de",
            "public": True,
            "state": "PUBLISHED",  # Required field for validator
            "settings": {
                "editable_answer": True,
                "full_participation": True,
                "participation_mode": "UNGUIDED",
                "participation_val_mode": "COOKIE"
            },
            "analysis_mode": "FREE",
            "admin_pw": ADMIN_PASS
        }
    
    @staticmethod
    def get_dummy_title(lang: str = "DE") -> Dict[str, str]:
        """Returns dummy title in specified language."""
        return {lang: "Validation Test Survey"}
    
    @staticmethod
    def get_dummy_description(lang: str = "DE") -> Dict[str, str]:
        """Returns dummy description."""
        return {lang: "This is a validation test description"}
    
    @staticmethod
    def get_dummy_question(lang: str = "DE") -> Dict[str, str]:
        """Returns dummy question text."""
        return {lang: "Dummy validation question?"}
    
    @staticmethod
    def get_dummy_options(count: int = 3, lang: str = "DE") -> Dict[str, Dict[str, str]]:
        """Returns dummy answer options."""
        return {
            str(i): {lang: f"Option {i+1}"}
            for i in range(count)
        }
    
    @staticmethod
    def get_dummy_question_block(block_id: str = "0", lang: str = "DE") -> Dict:
        """Returns a complete dummy question block."""
        return {
            "title": {lang: f"Validation Block {block_id}"},
            "description": {lang: "Dummy block for validation"},
            "questions": {
                "0": {
                    "question": DummyDataGenerator.get_dummy_question(lang),
                    "question_type": "ChoiceSingle",
                    "settings": {"mandatory": False, "grid": False},
                    "config": {
                        "option_type": "TEXT",
                        "options": DummyDataGenerator.get_dummy_options(3, lang)
                    },
                    "analysis_mode": "FREE"
                }
            },
            "analysis_mode": "FREE",
            "structure": {"start": 0, "components": {"0": {"default": -1}}}
        }


class SurveyValidator:
    """Main validator class for survey creation workflow."""
    
    def __init__(self, language: str = "DE", rate_limit_delay: float = None):
        self.language = language
        self.dummy_gen = DummyDataGenerator()
        self.rate_limit_delay = rate_limit_delay if rate_limit_delay is not None else RATE_LIMIT_DELAY
        self._last_api_call = 0  # Track last API call time for rate limiting
    
    def _make_validated_request(self, payload: Dict, timeout: int = 10) -> requests.Response:
        """
        Make a validated API request with rate limiting.
        
        Args:
            payload: The request payload
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        # Rate limiting: ensure minimum delay between API calls
        if self.rate_limit_delay > 0:
            time_since_last_call = time.time() - self._last_api_call
            if time_since_last_call < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last_call
                time.sleep(sleep_time)
        
        # Make the API call
        response = requests.put(
            VALIDATOR_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Update last call time
        self._last_api_call = time.time()
        
        return response
    
    def validate_question(self, question_data: Dict, question_type: str) -> ValidationResult:
        """
        Validates a single question by creating a minimal survey with just this question.
        
        Args:
            question_data: Dict containing question text, options, settings, etc.
            question_type: Type of question (ChoiceSingle, ChoiceMulti, GoodBad, Slider, TextInput, etc.)
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        
        # Local validation first
        if not question_data.get("question"):
            errors.append("Question text is required")
        
        # Validate based on question type
        if question_type in ["ChoiceSingle", "ChoiceMulti", "GoodBad"]:
            options = question_data.get("config", {}).get("options", {})
            if not options:
                errors.append("At least one option is required for choice questions")
            elif len(options) < 2:
                warnings.append("Choice questions typically have at least 2 options")
        
        elif question_type == "Slider":
            # Note: Slider may not be supported by the API validator
            warnings.append("Slider question type may not be supported by the API. Use ChoiceSingle/ChoiceMulti for testing.")
            config = question_data.get("config", {})
            if "min" not in config or "max" not in config:
                errors.append("Slider questions require min and max values")
            elif config.get("min", 0) >= config.get("max", 100):
                errors.append("Slider max value must be greater than min value")
        
        # If local validation fails, return early
        if errors:
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        # Build minimal survey for API validation
        survey_payload = self._build_question_validation_payload(question_data, question_type)
        
        # Make API call to validator endpoint (PUT request) with rate limiting
        try:
            response = self._make_validated_request(survey_payload, timeout=10)
            
            # Check response
            if response.status_code == 200 or response.status_code == 201:
                result_data = response.json()
                
                # Check if validator returned any validation errors
                if result_data.get("valid", True):
                    return ValidationResult(
                        success=True,
                        warnings=warnings,
                        data={"validated_structure": question_data, "validator_response": result_data}
                    )
                else:
                    # Validator found issues
                    validation_errors = result_data.get("errors", [])
                    for err in validation_errors:
                        errors.append(f"Validation issue: {err}")
                    return ValidationResult(success=False, errors=errors, warnings=warnings)
            else:
                # API returned error
                error_msg = self._parse_api_error(response)
                errors.append(f"API validation failed: {error_msg}")
                return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        except requests.exceptions.Timeout:
            errors.append("Validation request timed out. Please try again.")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        except requests.exceptions.RequestException as e:
            errors.append(f"Network error during validation: {str(e)}")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    def validate_question_block(self, block_data: Dict, questions: List[Dict]) -> ValidationResult:
        """
        Validates a question block with multiple questions.
        
        Args:
            block_data: Dict containing block title, description, settings, etc.
            questions: List of question dicts to include in this block
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        
        # Local validation
        if not block_data.get("title"):
            errors.append("Block title is required")
        
        if not questions or len(questions) == 0:
            errors.append("Block must contain at least one question")
        
        if len(questions) > 50:
            warnings.append("Large number of questions in one block may impact user experience")
        
        if errors:
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        # Build survey payload with this block
        survey_payload = self._build_block_validation_payload(block_data, questions)
        
        # Make API call to validator endpoint (PUT request) with rate limiting
        try:
            response = self._make_validated_request(survey_payload, timeout=10)
            
            if response.status_code == 200 or response.status_code == 201:
                result_data = response.json()
                
                # Check validation result
                if result_data.get("valid", True):
                    return ValidationResult(
                        success=True,
                        warnings=warnings,
                        data={"validated_block": block_data, "validator_response": result_data}
                    )
                else:
                    validation_errors = result_data.get("errors", [])
                    for err in validation_errors:
                        errors.append(f"Block validation issue: {err}")
                    return ValidationResult(success=False, errors=errors, warnings=warnings)
            else:
                error_msg = self._parse_api_error(response)
                errors.append(f"Block validation failed: {error_msg}")
                return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        except requests.exceptions.RequestException as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    def validate_full_survey(self, survey_config: Dict, blocks: Dict[str, Dict]) -> ValidationResult:
        """
        Validates the complete survey structure before final creation.
        
        Args:
            survey_config: Global survey configuration (title, description, settings, etc.)
            blocks: Dict of block_id -> block_data with questions
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        
        # Local validation
        if not survey_config.get("title"):
            errors.append("Survey title is required")
        
        if not blocks or len(blocks) == 0:
            errors.append("Survey must contain at least one question block")
        
        # Check for empty blocks
        for block_id, block_data in blocks.items():
            if not block_data.get("questions") or len(block_data["questions"]) == 0:
                errors.append(f"Block '{block_data.get('title', block_id)}' has no questions")
        
        if errors:
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        # Build complete survey payload
        survey_payload = self._build_full_survey_payload(survey_config, blocks)
        
        # Make API call to validator endpoint (PUT request) with rate limiting
        try:
            response = self._make_validated_request(survey_payload, timeout=15)
            
            if response.status_code == 200 or response.status_code == 201:
                result_data = response.json()
                
                # Check validation result
                if result_data.get("valid", True):
                    return ValidationResult(
                        success=True,
                        warnings=warnings,
                        data={"validated_survey": survey_config, "validator_response": result_data}
                    )
                else:
                    validation_errors = result_data.get("errors", [])
                    for err in validation_errors:
                        errors.append(f"Survey validation issue: {err}")
                    return ValidationResult(success=False, errors=errors, warnings=warnings)
            else:
                error_msg = self._parse_api_error(response)
                errors.append(f"Survey validation failed: {error_msg}")
                return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        except requests.exceptions.RequestException as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    def validate_interactive_module(self, module_type: str, module_data: Dict) -> ValidationResult:
        """
        Validates interactive modules (Q&A, Word Cloud).
        
        Args:
            module_type: "QnA" or "WordCloud"
            module_data: Module configuration
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        
        if module_type == "QnA":
            if not module_data.get("topic"):
                errors.append("Q&A topic is required")
        elif module_type == "WordCloud":
            if not module_data.get("topic"):
                errors.append("Word Cloud topic is required")
        else:
            errors.append(f"Unknown interactive module type: {module_type}")
        
        if errors:
            return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        # Build interactive module payload
        survey_payload = self._build_interactive_validation_payload(module_type, module_data)
        
        # Make API call to validator endpoint (PUT request) with rate limiting
        try:
            response = self._make_validated_request(survey_payload, timeout=10)
            
            if response.status_code == 200 or response.status_code == 201:
                result_data = response.json()
                
                # Check validation result
                if result_data.get("valid", True):
                    return ValidationResult(
                        success=True,
                        warnings=warnings,
                        data={"validated_module": module_data, "validator_response": result_data}
                    )
                else:
                    validation_errors = result_data.get("errors", [])
                    for err in validation_errors:
                        errors.append(f"Interactive module issue: {err}")
                    return ValidationResult(success=False, errors=errors, warnings=warnings)
            else:
                error_msg = self._parse_api_error(response)
                errors.append(f"Interactive module validation failed: {error_msg}")
                return ValidationResult(success=False, errors=errors, warnings=warnings)
        
        except requests.exceptions.RequestException as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _build_question_validation_payload(self, question_data: Dict, question_type: str) -> Dict:
        """Builds a minimal survey payload with just one question for validation."""
        
        # Use dummy data for global config
        global_config = self.dummy_gen.get_dummy_global_config()
        global_config["title"] = question_data.get("title") or self.dummy_gen.get_dummy_title(self.language)
        
        # Build question block with the real question
        question_block = {
            "0": {
                "title": self.dummy_gen.get_dummy_title(self.language),
                "description": self.dummy_gen.get_dummy_description(self.language),
                "questions": {
                    "0": {
                        "question": question_data.get("question", self.dummy_gen.get_dummy_question(self.language)),
                        "question_type": question_type,
                        "settings": question_data.get("settings", {"mandatory": False, "grid": False}),
                        "config": question_data.get("config", {}),
                        "analysis_mode": "FREE"
                    }
                },
                "analysis_mode": "FREE",
                "structure": {"start": 0, "components": {"0": {"default": -1}}}
            }
        }
        
        return {
            "data": {
                "module": "Survey",
                "config": {
                    **global_config,
                    "structure": {"start": 0, "components": {"0": {"default": -1}}}
                },
                "question_blocks": question_block
            }
        }
    
    def _build_block_validation_payload(self, block_data: Dict, questions: List[Dict]) -> Dict:
        """Builds a survey payload with one complete block for validation."""
        
        global_config = self.dummy_gen.get_dummy_global_config()
        global_config["title"] = self.dummy_gen.get_dummy_title(self.language)
        
        # Build questions dict
        questions_dict = {}
        for idx, q in enumerate(questions):
            questions_dict[str(idx)] = q
        
        # Build the block
        question_block = {
            "0": {
                "title": block_data.get("title", self.dummy_gen.get_dummy_title(self.language)),
                "description": block_data.get("description", self.dummy_gen.get_dummy_description(self.language)),
                "questions": questions_dict,
                "analysis_mode": "FREE",
                "structure": block_data.get("structure", {"start": 0, "components": {str(i): {"default": -1} for i in range(len(questions))}})
            }
        }
        
        return {
            "data": {
                "module": "Survey",
                "config": {
                    **global_config,
                    "structure": {"start": 0, "components": {"0": {"default": -1}}}
                },
                "question_blocks": question_block
            }
        }
    
    def _build_full_survey_payload(self, survey_config: Dict, blocks: Dict[str, Dict]) -> Dict:
        """Builds complete survey payload for final validation."""
        
        global_config = self.dummy_gen.get_dummy_global_config()
        
        # Build proper structure with all blocks in the path
        block_count = len(blocks)
        structure_components = {}
        
        for i in range(block_count):
            if i == block_count - 1:
                # Last block points to -1 (end)
                structure_components[str(i)] = {"default": -1}
            else:
                # Each block points to the next
                structure_components[str(i)] = {"default": i + 1}
        
        # Merge real config with dummy defaults
        global_config.update({
            "title": survey_config.get("title", self.dummy_gen.get_dummy_title(self.language)),
            "description": survey_config.get("description", self.dummy_gen.get_dummy_description(self.language)),
            "settings": {**global_config["settings"], **survey_config.get("settings", {})},
            "structure": {"start": 0, "components": structure_components}
        })
        
        return {
            "data": {
                "module": survey_config.get("module", "Survey"),
                "config": global_config,
                "question_blocks": blocks
            }
        }
    
    def _build_interactive_validation_payload(self, module_type: str, module_data: Dict) -> Dict:
        """Builds payload for interactive module validation."""
        
        global_config = self.dummy_gen.get_dummy_global_config()
        global_config["title"] = module_data.get("title") or self.dummy_gen.get_dummy_title(self.language)
        
        # Interactive modules have different structure - adjust based on your API
        return {
            "data": {
                "module": module_type,
                "config": {
                    **global_config,
                    **module_data
                }
            }
        }
    
    def _parse_api_error(self, response: requests.Response) -> str:
        """Parses API error response and returns user-friendly message."""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                if "error" in error_data:
                    return error_data["error"]
                elif "message" in error_data:
                    return error_data["message"]
            return f"Status {response.status_code}: {response.text[:200]}"
        except:
            return f"Status {response.status_code}: Unable to parse error message"


# ==================== CONVENIENCE FUNCTIONS ====================

def validate_question_preview(question_data: Dict, question_type: str, language: str = "DE", rate_limit_delay: float = None) -> ValidationResult:
    """
    Convenience function to validate a question at preview checkpoint.
    
    Args:
        question_data: Question configuration
        question_type: Type of question (ChoiceSingle, ChoiceMulti, etc.)
        language: Language code (default: "DE")
        rate_limit_delay: Delay in seconds between API calls (default: 0.5s). 
                         Set to 0 to disable rate limiting.
    
    Usage:
        result = validate_question_preview(
            question_data={
                "question": {"DE": "How satisfied are you?"},
                "config": {
                    "option_type": "TEXT",
                    "options": {
                        "0": {"DE": "Very satisfied"},
                        "1": {"DE": "Satisfied"},
                        "2": {"DE": "Neutral"}
                    }
                },
                "settings": {"mandatory": True}
            },
            question_type="ChoiceSingle"
        )
        
        if result.success:
            print("Question validated successfully!")
        else:
            print(result.get_user_message())
    """
    validator = SurveyValidator(language=language, rate_limit_delay=rate_limit_delay)
    return validator.validate_question(question_data, question_type)


def validate_block_preview(block_data: Dict, questions: List[Dict], language: str = "DE", rate_limit_delay: float = None) -> ValidationResult:
    """
    Convenience function to validate a question block at preview checkpoint.
    
    Args:
        block_data: Block configuration
        questions: List of question dicts
        language: Language code (default: "DE")
        rate_limit_delay: Delay in seconds between API calls (default: 0.5s)
    
    Usage:
        result = validate_block_preview(
            block_data={
                "title": {"DE": "Employee Satisfaction"},
                "description": {"DE": "Questions about your work environment"}
            },
            questions=[
                {
                    "question": {"DE": "Question 1?"},
                    "question_type": "ChoiceSingle",
                    "config": {...},
                    "settings": {"mandatory": True}
                },
                # ... more questions
            ]
        )
    """
    validator = SurveyValidator(language=language, rate_limit_delay=rate_limit_delay)
    return validator.validate_question_block(block_data, questions)


def validate_survey_preview(survey_config: Dict, blocks: Dict[str, Dict], language: str = "DE", rate_limit_delay: float = None) -> ValidationResult:
    """
    Convenience function to validate complete survey at final preview checkpoint.
    
    Args:
        survey_config: Survey configuration
        blocks: Dictionary of blocks
        language: Language code (default: "DE")
        rate_limit_delay: Delay in seconds between API calls (default: 0.5s)
    
    Usage:
        result = validate_survey_preview(
            survey_config={
                "title": {"DE": "Annual Survey 2025"},
                "description": {"DE": "Your feedback matters"},
                "settings": {...}
            },
            blocks={
                "0": {
                    "title": {"DE": "Block 1"},
                    "questions": {...}
                },
                "1": {
                    "title": {"DE": "Block 2"},
                    "questions": {...}
                }
            }
        )
    """
    validator = SurveyValidator(language=language, rate_limit_delay=rate_limit_delay)
    return validator.validate_full_survey(survey_config, blocks)


def validate_interactive_preview(module_type: str, module_data: Dict, language: str = "DE", rate_limit_delay: float = None) -> ValidationResult:
    """
    Convenience function to validate interactive module at preview checkpoint.
    
    Args:
        module_type: "QnA" or "WordCloud"
        module_data: Module configuration
        language: Language code (default: "DE")
        rate_limit_delay: Delay in seconds between API calls (default: 0.5s)
    
    Usage:
        result = validate_interactive_preview(
            module_type="QnA",
            module_data={
                "topic": {"DE": "Ask me anything about the project"}
            }
        )
    """
    validator = SurveyValidator(language=language, rate_limit_delay=rate_limit_delay)
    return validator.validate_interactive_module(module_type, module_data)
