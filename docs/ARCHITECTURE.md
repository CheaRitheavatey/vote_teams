# Vote Teams - Module Architecture

```
vote_teams/
│
├── app.py                          # Main Flask application (260 lines)
│   ├── Routes & Message Handler
│   ├── Vote Flow
│   ├── Results Flow
│   ├── Create Survey Flow
│   └── Workflow Orchestration
│
├── workflow/                       # Workflow modules
│   ├── __init__.py                # Module initialization
│   │
│   ├── advanced_helpers.py        # Helper functions (118 lines)
│   │   ├── send_question_preview()
│   │   └── send_advanced_overview()
│   │
│   ├── advanced_mode.py           # Global settings (118 lines)
│   │   ├── handle_advanced_mode_selection()
│   │   ├── handle_advanced_email()
│   │   ├── handle_advanced_title()
│   │   ├── handle_advanced_description()
│   │   └── handle_advanced_language()
│   │
│   ├── advanced_steps.py          # Question/Block handlers (306 lines)
│   │   ├── handle_block_selection()
│   │   ├── handle_block_title()
│   │   ├── handle_block_description()
│   │   ├── handle_question_type()
│   │   ├── handle_question_text()
│   │   ├── handle_question_options()
│   │   ├── handle_rating_min()
│   │   ├── handle_rating_max()
│   │   ├── handle_question_confirm()
│   │   ├── handle_more_questions_in_block()
│   │   ├── handle_more_standalone()
│   │   ├── handle_more_blocks()
│   │   ├── handle_standalone_after_blocks()
│   │   └── handle_advanced_overview()
│   │
│   ├── quick_mode.py              # Quick mode workflow (120 lines)
│   │   ├── handle_quick_mode_selection()
│   │   ├── handle_quick_email()
│   │   ├── handle_quick_title()
│   │   ├── handle_quick_question()
│   │   ├── handle_quick_type()
│   │   ├── handle_quick_options()
│   │   └── handle_quick_confirmation()
│   │
│   └── survey_api.py              # API integration (142 lines)
│       └── create_advanced_survey()
│
├── api/                           # API modules
│   ├── validation.py              # SurveyValidator class
│   ├── fetch_question.py
│   ├── submit_answer.py
│   └── get_result.py
│
├── static/
│   ├── chat.css                   # Fixed height, scrollbar
│   └── chat.js                    # Enter key support
│
├── templates/
│   └── index.html                 # Chat interface
│
└── app_backup.py                  # Original 951-line version (backup)
```

## Data Flow

### Quick Mode Flow
```
User: "create"
  ↓
app.py (route to mode selection)
  ↓
User: "1" (Quick)
  ↓
quick_mode.handle_quick_mode_selection()
  ↓
quick_mode.handle_quick_email()
  ↓
quick_mode.handle_quick_title()
  ↓
quick_mode.handle_quick_question()
  ↓
quick_mode.handle_quick_type()
  ↓
quick_mode.handle_quick_options() (if needed)
  ↓
quick_mode.handle_quick_confirmation()
  ↓
survey_api.create_advanced_survey()
  ↓
Vote2 API
```

### Advanced Mode Flow
```
User: "create"
  ↓
app.py (route to mode selection)
  ↓
User: "2" (Advanced)
  ↓
advanced_mode.handle_advanced_mode_selection()
  ↓
advanced_mode.handle_advanced_email()
  ↓
advanced_mode.handle_advanced_title()
  ↓
advanced_mode.handle_advanced_description()
  ↓
advanced_mode.handle_advanced_language()
  ↓ (validates global settings)
advanced_steps.handle_block_selection()
  ↓
[Block Creation Loop]
  advanced_steps.handle_block_title()
  advanced_steps.handle_block_description()
    ↓
  [Question Creation Loop]
    advanced_steps.handle_question_type()
    advanced_steps.handle_question_text()
    advanced_steps.handle_question_options() (or rating_min/max)
    advanced_steps.handle_question_confirm()
      ↓ (uses advanced_helpers.send_question_preview)
    advanced_steps.handle_more_questions_in_block()
  ↓
  advanced_steps.handle_more_blocks()
  ↓
[Standalone Questions]
  advanced_steps.handle_standalone_after_blocks()
  [Question Creation Loop]
  advanced_steps.handle_more_standalone()
  ↓
advanced_steps.handle_advanced_overview()
  ↓ (uses advanced_helpers.send_advanced_overview)
survey_api.create_advanced_survey()
  ↓
Vote2 API
```

## Module Dependencies

```
app.py
  ├── workflow.advanced_helpers
  ├── workflow.advanced_mode
  ├── workflow.advanced_steps
  ├── workflow.quick_mode
  ├── workflow.survey_api
  ├── api.validation (SurveyValidator)
  ├── api.fetch_question
  ├── api.submit_answer
  └── api.get_result

workflow.advanced_steps
  ├── workflow.advanced_helpers (send_question_preview, send_advanced_overview)
  ├── workflow.survey_api (create_advanced_survey)
  └── api.validation (SurveyValidator)

workflow.advanced_mode
  └── api.validation (SurveyValidator)

workflow.advanced_helpers
  └── api.validation (SurveyValidator)

workflow.quick_mode
  └── workflow.survey_api (create_advanced_survey)

workflow.survey_api
  └── requests (for API calls)
```

## Key Features Preserved

✅ Fixed height chat with scrollbar  
✅ Enter key sends messages  
✅ Quick mode (simple one-question survey)  
✅ Advanced mode (blocks + multiple questions)  
✅ 4 question types: Single Choice, Multi Choice, Rating (0-100), Free Text  
✅ Question validation using Vote2 API validator  
✅ Question preview with edit functionality  
✅ Global settings validation with dummy block  
✅ Proper API formatting (language dicts, nested options)  
✅ Vote and results flows  
✅ Email validation (basic @ and . check)  

## Testing Checklist

- [ ] Quick mode survey creation
- [ ] Advanced mode with blocks
- [ ] Advanced mode with standalone questions
- [ ] Mixed blocks + standalone questions
- [ ] All 4 question types work correctly
- [ ] Question editing in preview
- [ ] API validation shows errors properly
- [ ] Survey creation succeeds
- [ ] Vote flow works
- [ ] Results retrieval works
