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
    
    async def _extract_fields_by_intent(self, text_content: str, intent: str) -> Dict[str, Any]:
        """
        Extract fields from PDF content based on intent
        
        Args:
            text_content: Extracted text from PDF
            intent: Document intent (invoice, rfq, etc.)
            
        Returns:
            Dict of extracted fields
        """
        # Trim content to fit in LLM context
        trimmed_content = text_content[:4000]  # Use more context for PDFs
        
        # Define extraction prompts based on intent
        if intent == "invoice":
            system_prompt = "You are an AI specialized in extracting information from invoice PDFs. Extract the invoice number, amount, due date, vendor, customer, and line items if available."
            field_list = "invoice_number, total_amount, due_date, vendor, customer, items"
        elif intent == "rfq" or intent == "request for quote":
            system_prompt = "You are an AI specialized in extracting information from Request for Quote (RFQ) PDFs. Extract the items requested, quantities, desired delivery date, and any specific requirements."
            field_list = "rfq_number, items_requested, quantities, delivery_date, specific_requirements"
        elif "agreement" in intent.lower() or "contract" in intent.lower() or "license" in intent.lower():
            system_prompt = "You are an AI specialized in extracting information from legal agreements and contracts. Extract the agreement title, parties involved, effective date, termination date, key terms, and identify if signatures are present."
            field_list = "agreement_title, parties_involved, effective_date, termination_date, key_terms, contains_signatures"
        elif "report" in intent.lower() or "research" in intent.lower():
            system_prompt = "You are an AI specialized in extracting information from research reports. Extract the title, authors, date, key findings, methodology, and conclusions."
            field_list = "title, authors, date, key_findings, methodology, conclusions"
        else:
            system_prompt = f"You are an AI specialized in extracting key information from {intent} documents. Extract all significant fields and data points appropriate for this document type."
            field_list = "document_title, date, author, primary_topics, key_points, document_summary"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the following fields from this {intent} document: {field_list}. Respond with only a JSON object with these fields.\n\nDOCUMENT CONTENT:\n{trimmed_content}"}
        ]
        
        try:
            response = await self.query_llm(messages)
            
            # Try to parse as JSON
            extracted_data = json.loads(response)
            return extracted_data
        except json.JSONDecodeError:
            # If LLM doesn't return valid JSON, attempt to extract from the response
            logging.warning(f"Failed to parse LLM response as JSON: {response[:100]}...")
            
            # Make a second attempt with a stronger instruction
            messages = [
                {"role": "system", "content": "You are an AI that extracts structured information from documents and outputs ONLY valid JSON. No explanations or extra text."},
                {"role": "user", "content": f"Extract key information from this {intent} document and return ONLY a JSON object. Fields to include: {field_list}.\n\nDOCUMENT CONTENT:\n{trimmed_content[:2000]}"}
            ]
            
            try:
                response = await self.query_llm(messages)
                # Find JSON in the response by looking for opening brace
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                return {"raw_extraction": response[:1000], "document_type": intent}
            except:
                return {"raw_extraction": response[:1000], "document_type": intent}
        except Exception as e:
            logging.exception("Error in LLM extraction")
            return {"error": str(e), "document_type": intent}
