from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import base64
import json
import sys
import os
import logging
from starlette.responses import JSONResponse

# Add the parent directory to sys.path to fix imports when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Use direct imports (no relative imports)
from backend.agents.classifier_agent import ClassifierAgent
from backend.agents.json_agent import JSONAgent
from backend.agents.email_agent import EmailAgent
from backend.agents.pdf_agent import PDFAgent  # Add this line
from backend.memory.memory_store import MemoryStore

# Fallback to direct imports if the above fails
try:
    from agents.classifier_agent import ClassifierAgent
    from agents.json_agent import JSONAgent
    from agents.email_agent import EmailAgent
    from agents.pdf_agent import PDFAgent  # Add this line
    from memory.memory_store import MemoryStore
except ImportError:
    pass

app = FastAPI(title="AI-driven Document Triage System")

# Set up CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize memory store
memory_store = MemoryStore()

# Initialize agents
classifier_agent = ClassifierAgent(memory_store)
json_agent = JSONAgent(memory_store)
email_agent = EmailAgent(memory_store)
pdf_agent = PDFAgent(memory_store)  # Add this line

class EmailInput(BaseModel):
    content: str
    subject: Optional[str] = None
    sender: Optional[str] = None

@app.post("/classify")
async def classify_document(
    file: Optional[UploadFile] = File(None),
    email_content: Optional[str] = Form(None),
    json_content: Optional[str] = Form(None)
):
    """Classify document type and intent"""
    try:
        if file:
            content = await file.read()
            filename = file.filename
            file_extension = filename.split('.')[-1].lower()
            
            # Handle binary content like PDF
            if file_extension == 'pdf':
                content_type = 'pdf'
                content_base64 = base64.b64encode(content).decode('utf-8')
                content = content_base64
                logging.info(f"Processing PDF file: {filename}")
            elif file_extension == 'json':
                content_type = 'json'
                content = json.loads(content.decode('utf-8'))
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        elif email_content:
            content = email_content
            content_type = 'email'
        elif json_content:
            content = json.loads(json_content)
            content_type = 'json'
        else:
            raise HTTPException(status_code=400, detail="No content provided")
            
        # Call classifier agent
        classification = await classifier_agent.classify(content, content_type)
        
        # For PDF uploads, make sure format is correctly set
        if content_type == 'pdf' and classification.get("format") != "pdf":
            classification["format"] = "pdf"
            logging.info("Correcting format to PDF based on uploaded file extension")
        
        return classification
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")

@app.post("/process/{document_id}")
async def process_document(document_id: str, background_tasks: BackgroundTasks):
    """Process a previously classified document"""
    try:
        # Get document classification from memory
        doc_info = memory_store.get_document(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_format = doc_info.get("format", "").lower() if doc_info.get("format") else "unknown"
        doc_intent = doc_info.get("intent", "").lower() if doc_info.get("intent") else "general"
        content = doc_info.get("content")
        
        # Enhanced logging
        logging.info(f"Processing document {document_id}")
        logging.info(f"  Format: '{doc_format}', Intent: '{doc_intent}'")
        
        # Route to appropriate agent with case-insensitive format checks
        if doc_format == "json" or doc_format == "application/json":
            result = await json_agent.process(content, doc_intent, document_id)
        elif doc_format == "email" or doc_format == "text/plain":
            result = await email_agent.process(content, doc_intent, document_id)
        elif doc_format == "pdf" or doc_format == "application/pdf":
            # Since we don't have a PDF agent yet, use a placeholder
            result = await pdf_agent.process(content, doc_intent, document_id)
        else:
            # Instead of raising an exception, try to handle this more gracefully
            logging.warning(f"Unrecognized format: '{doc_format}'. Defaulting to text processing.")
            # Use the email agent as fallback for text-based content
            result = await email_agent.process(content, doc_intent, document_id)
            
        return {
            "document_id": document_id,
            "format": doc_format,
            "intent": doc_intent,
            "processing_result": result
        }
    except Exception as e:
        logging.exception(f"Error processing document {document_id}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/history")
async def get_history(limit: int = 5):
    """Get processing history"""
    try:
        history = memory_store.get_history(limit)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "version": "1.0"}

@app.get("/check-api-key")
async def check_api_key():
    """Check OpenRouter API key"""
    from backend.config import OPENROUTER_API_KEY, DEFAULT_MODEL
    
    # Mask the API key for security in logs
    api_key = OPENROUTER_API_KEY
    masked_key = "NOT_SET" if not api_key else f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "INVALID_FORMAT"
    
    # Read directly from .env file to compare
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    direct_env_key = "NO_ENV_FILE"
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        direct_env_key = line.strip().split("=", 1)[1]
                        # Mask this too
                        if direct_env_key and len(direct_env_key) > 12:
                            direct_env_key = f"{direct_env_key[:8]}...{direct_env_key[-4:]}"
                        break
        except Exception as e:
            direct_env_key = f"ERROR: {str(e)}"
    
    return {
        "loaded_key": masked_key,
        "env_file_key": direct_env_key,
        "model": DEFAULT_MODEL,
        "env_vars": {k: (f"{v[:8]}..." if k.endswith("API_KEY") and v and len(v) > 10 else v) for k, v in os.environ.items() if "API" in k or "MODEL" in k or "KEY" in k}
    }
