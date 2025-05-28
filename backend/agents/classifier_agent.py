import json
from typing import Dict, Any, Union
import base64

# Try both import styles to support different ways of running the app
try:
    from backend.agents.base_agent import BaseAgent
    from backend.parsers.pdf_parser import extract_pdf_text
    from backend.memory.memory_store import MemoryStore
except ImportError:
    from .base_agent import BaseAgent
    from ..parsers.pdf_parser import extract_pdf_text
    from ..memory.memory_store import MemoryStore

class ClassifierAgent(BaseAgent):
    """Agent for classifying document format and intent"""
    
    def __init__(self, memory_store: MemoryStore):
        super().__init__(memory_store)
    
    async def classify(self, content: Union[str, Dict, bytes], content_type: str = None) -> Dict[str, Any]:
        """
        Classify the format and intent of the document
        
        Args:
            content: The document content
            content_type: Optional hint about content type
            
        Returns:
            Dict with format, intent and document ID
        """
        # Prepare content for classification
        if content_type == "pdf" and isinstance(content, str):
            # Content is base64-encoded PDF
            try:
                binary_content = base64.b64decode(content)
                text_content = extract_pdf_text(binary_content)
                processed_content = text_content[:1500]  # Limit text for LLM
            except Exception as e:
                raise Exception(f"Failed to process PDF: {str(e)}")
        elif content_type == "json" or isinstance(content, dict):
            # Content is JSON
            if isinstance(content, dict):
                processed_content = json.dumps(content, indent=2)[:1500]
            else:
                processed_content = content[:1500]
        elif content_type == "email" or isinstance(content, str):
            # Content is likely email or plain text
            processed_content = content[:1500]
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        # Classify using LLM
        messages = [
            {"role": "system", "content": "You are a document classification AI. Your task is to analyze the document and determine its format (PDF, JSON, Email) and its intent (Invoice, RFQ, Complaint, Regulation, etc.)."},
            {"role": "user", "content": f"Classify the document format and intent from the following content snippet:\n\n{processed_content}\n\nRespond in JSON format with 'format' and 'intent' fields only."}
        ]
        
        response = await self.query_llm(messages)
        
        try:
            result = json.loads(response)
            document_format = result.get("format", "unknown").lower()
            document_intent = result.get("intent", "unknown").lower()
        except json.JSONDecodeError:
            # Fallback parsing if LLM doesn't return valid JSON
            if "json" in response.lower():
                document_format = "json"
            elif "email" in response.lower():
                document_format = "email"
            elif "pdf" in response.lower():
                document_format = "pdf"
            else:
                document_format = "unknown"
                
            if "invoice" in response.lower():
                document_intent = "invoice"
            elif "rfq" in response.lower() or "request for quote" in response.lower():
                document_intent = "rfq"
            elif "complaint" in response.lower():
                document_intent = "complaint"
            elif "regulation" in response.lower():
                document_intent = "regulation"
            else:
                document_intent = "unknown"
        
        # Generate document ID and store in memory
        document_id = self.generate_id()
        
        # Store document information
        self.memory_store.store_document(
            document_id=document_id,
            format=document_format,
            intent=document_intent,
            content=content
        )
        
        return {
            "document_id": document_id,
            "format": document_format,
            "intent": document_intent
        }
    
    async def process(self, content, intent, document_id=None):
        """
        Process method required by BaseAgent
        For Classifier, this just returns the classification
        """
        if document_id is None:
            document_id = self.generate_id()
            
        return await self.classify(content)
