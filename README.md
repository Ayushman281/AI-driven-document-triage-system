# AI-driven Document Triage System

A multi-agent AI system that accepts input in PDF, JSON, or Email format, classifies the format and intent, and routes it to the appropriate agent for processing.

## Features

- **Input Formats**: PDF, JSON, and Email (text)
- **Multi-Agent System**:
  - Classifier Agent: Determines document format and intent
  - JSON Agent: Processes structured JSON documents
  - Email Agent: Extracts information from emails
- **Shared Memory**: Maintains context across agents
- **User-friendly UI**: Built with Streamlit

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Database**: SQLite
- **LLM API**: OpenRouter.ai
- **PDF Parser**: PyMuPDF
- **Email Parser**: Python's built-in email module
- **JSON Validation**: jsonschema

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your OpenRouter API key to `.env`

## Running the Application

1. Start the backend server:
   ```
   cd backend
   uvicorn main:app --reload
   ```

2. In a new terminal, start the Streamlit frontend:
   ```
   cd frontend
   streamlit run app.py
   ```

3. Open your browser and navigate to `http://localhost:8501`

## Project Structure

```
AI-driven document triage system/
├── backend/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── classifier_agent.py
│   │   ├── email_agent.py
│   │   └── json_agent.py
│   ├── memory/
│   │   └── memory_store.py
│   ├── parsers/
│   │   └── pdf_parser.py
│   ├── config.py
│   ├── database.py
│   └── main.py
├── frontend/
│   └── app.py
├── database/
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## How to Use

1. Upload a document (PDF or JSON) or paste email/JSON content
2. The system will classify the document format and intent
3. Process the document to extract relevant information
4. View and download the extracted data

## License

[MIT License](LICENSE)
