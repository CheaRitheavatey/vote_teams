# Vote@Teams

A chat-based survey creation and management system integrated with Deutsche Telekom's Vote2 API.

## Overview

Vote@Teams provides an intuitive chat interface for creating, sharing, and managing surveys. 
Users can create surveys through natural conversation, share them instantly, and collect responses.

## Features

- Quick Mode: Create single-question surveys in seconds
- Advanced Mode: Build multi-question surveys with blocks
- Four question types: Single Choice, Multiple Choice, Range Slider, Free Text
- Real-time voting and results viewing

## Project Structure

```
vote_teams/
├── app.py                    # Main Flask application
├── requirements.txt          # Dependencies
├── api/                      # Vote2 API integration
│   ├── create_survey.py
│   ├── vote_runtime.py
│   ├── fetch_question.py
│   ├── get_result.py
│   └── validation.py
├── workflow/                 # Survey creation workflows
│   ├── quick_mode.py
│   ├── advanced_mode.py
│   └── survey_api.py
├── templates/                # Frontend HTML
└── static/                   # CSS and JavaScript
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```
   API_KEY=your_vote2_api_key
   ADMIN_PASS=your_admin_password
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open browser to `http://localhost:5000`

## Usage

### Creating a Survey

Quick Mode:
- Type `create` in chat
- Enter Telekom email (@telekom.com or @telekom.de)
- Provide title and question
- Choose question type and add options

Advanced Mode:
- Type `advanced` in chat
- Build multi-question surveys with blocks
- Configure settings and publish

### Voting

- Type `vote` in chat
- Select survey or enter code
- Answer questions and submit

### Results

- Type `result <code>` in chat
- View aggregated responses

## Technical Stack

- Backend: Flask (Python)
- Frontend: HTML/CSS/JavaScript
- API: Deutsche Telekom Vote2 API

## API Integration

Vote2 endpoints:
- POST /vote - Create surveys
- GET /vote/{code} - Fetch structure
- GET /vote/{code}/{block}/{question} - Fetch question
- POST /answers/{code} - Submit answers
- GET /result/{code} - Get results

## Testing

```bash
python tests/test_submit.py
python tests/test_console.py
```

## License

Deutsche Telekom Internal Project
