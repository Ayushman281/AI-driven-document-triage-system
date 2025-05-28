import json
import base64
import logging
from typing import Dict, Any, Union

# Try both import styles to support different ways of running the app
try:
    from backend.agents.base_agent import BaseAgent
    from backend.parsers.pdf_parser import extract_pdf_text, extract_pdf_metadata
    from backend.memory.memory_store import MemoryStore
except ImportError:
    from .base_agent import BaseAgent
    from ..parsers.pdf_parser import extract_pdf_text, extract_pdf_metadata
    from ..memory.memory_store import MemoryStore

class PDFAgent(BaseAgent):
    """Agent for processing and extracting information from PDF documents"""
    
    def __init__(self, memory_store: MemoryStore):
        super().__init__(memory_store)
        logging.info("PDF Agent initialized")
    
    async def process(self, content: Union[str, Dict, bytes], intent: str, document_id: str) -> Dict[str, Any]:
        """Process PDF document according to its intent"""
        logging.info(f"Processing PDF document {document_id} with intent: {intent}")
        
        try:
            # Convert the content to bytes if it's a base64 string
            if isinstance(content, str):
                if content == "BINARY_CONTENT":
                    return {
                        "status": "error",
                        "message": "PDF binary content was not stored in the database. Size limit exceeded."
                    }
                    
                try:
                    pdf_bytes = base64.b64decode(content)
                    logging.info(f"Successfully decoded base64 content, size: {len(pdf_bytes)} bytes")
                except Exception as e:
                    logging.error(f"Failed to decode base64 content: {e}")
                    return {
                        "status": "error",
                        "message": f"Failed to decode PDF content: {str(e)}"
                    }
            else:
                pdf_bytes = content
                logging.info(f"Using raw PDF content")
            
            # Extract text from PDF
            try:
                extracted_text = extract_pdf_text(pdf_bytes)
                logging.info(f"Extracted {len(extracted_text)} characters of text from PDF")
                
                # Extract metadata
                metadata = extract_pdf_metadata(pdf_bytes)
                logging.info(f"Extracted metadata: {metadata}")
            except Exception as e:
                logging.error(f"Error extracting PDF content: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to extract content from PDF: {str(e)}"
                }
            
            # Use LLM to extract structured information
            prompt = f"""
            Extract key information from this {intent} document.
            Return a JSON object with the extracted fields.
            
            Document text:
            {extracted_text[:4000]}  # Limit text length for LLM
            """
            
            messages = [
                {"role": "system", "content": "You are an AI assistant specialized in extracting information from documents."},
                {"role": "user", "content": prompt}
            ]
            
            try:
                llm_response = await self.query_llm(messages)
                logging.info(f"Received response from LLM of length {len(llm_response)}")
                
                # Try to parse as JSON
                try:
                    extracted_data = json.loads(llm_response)
                    logging.info(f"Successfully parsed LLM response as JSON")
                except json.JSONDecodeError:
                    logging.warning("Failed to parse LLM response as JSON, using raw response")
                    extracted_data = {"raw_extraction": llm_response}
                
                # Save extracted fields to memory
                for field, value in extracted_data.items():
                    self.memory_store.store_field(document_id, field, value)
                
                return {
                    "status": "success",
                    "extracted_data": extracted_data,
                    "metadata": metadata
                }
            except Exception as e:
                logging.error(f"Error during LLM query: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to process document with LLM: {str(e)}"
                }
                
        except Exception as e:
            logging.exception(f"Unexpected error in PDF processing: {e}")
            return {
                "status": "error", 
                "message": f"Unexpected error processing PDF: {str(e)}"
            }
