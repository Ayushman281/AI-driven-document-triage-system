import json
from typing import Dict, Any
import jsonschema
from jsonschema import ValidationError

try:
    from backend.agents.base_agent import BaseAgent
    from backend.memory.memory_store import MemoryStore
except ImportError:
    from .base_agent import BaseAgent
    from ..memory.memory_store import MemoryStore

class JSONAgent(BaseAgent):
    """Agent for processing and extracting information from JSON documents"""
    
    def __init__(self, memory_store: MemoryStore):
        super().__init__(memory_store)
        
        # Define target schemas for different intents
        self.schemas = {
            "invoice": {
                "type": "object",
                "required": ["invoice_number", "issue_date", "due_date", "total_amount"],
                "properties": {
                    "invoice_number": {"type": "string"},
                    "issue_date": {"type": "string", "format": "date"},
                    "due_date": {"type": "string", "format": "date"},
                    "vendor": {"type": "string"},
                    "customer": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "amount": {"type": "number"}
                            }
                        }
                    },
                    "total_amount": {"type": "number"},
                    "currency": {"type": "string"}
                }
            },
            "rfq": {
                "type": "object",
                "required": ["rfq_number", "request_date", "items"],
                "properties": {
                    "rfq_number": {"type": "string"},
                    "request_date": {"type": "string"},
                    "requester": {"type": "string"},
                    "supplier": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_name": {"type": "string"},
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "specifications": {"type": "string"}
                            }
                        }
                    }
                }
            },
            # Additional schemas can be added for other intents
        }
        
    async def process(self, content: Dict[str, Any], intent: str, document_id: str) -> Dict[str, Any]:
        """
        Process JSON document according to its intent
        
        Args:
            content: JSON content as a dictionary
            intent: Document intent (invoice, rfq, etc.)
            document_id: Unique identifier for the document
            
        Returns:
            Dict with processing results and extracted data
        """
        # Ensure content is a dictionary
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON content"}
        
        # Get the appropriate schema based on intent
        target_schema = self.schemas.get(intent)
        
        if not target_schema:
            # If no specific schema for this intent, use LLM to extract key information
            return await self._extract_with_llm(content, intent, document_id)
        
        # Validate against schema
        validation_errors = []
        try:
            jsonschema.validate(instance=content, schema=target_schema)
            is_valid = True
        except ValidationError as e:
            is_valid = False
            validation_errors.append(str(e))
        
        # Extract fields based on schema
        extracted_data = {}
        missing_fields = []
        
        if target_schema:
            for field in target_schema.get("required", []):
                if field in content:
                    extracted_data[field] = content[field]
                    # Store in memory
                    self.memory_store.store_field(document_id, field, content[field])
                else:
                    missing_fields.append(field)
            
            # Get other fields defined in schema
            for field in target_schema.get("properties", {}).keys():
                if field not in extracted_data and field in content:
                    extracted_data[field] = content[field]
                    # Store in memory
                    self.memory_store.store_field(document_id, field, content[field])
        
        return {
            "status": "success" if is_valid else "validation_failed",
            "extracted_data": extracted_data,
            "missing_fields": missing_fields,
            "validation_errors": validation_errors
        }
    
    async def _extract_with_llm(self, content: Dict[str, Any], intent: str, document_id: str) -> Dict[str, Any]:
        """
        Use LLM to extract information when no schema is available
        
        Args:
            content: JSON content as a dictionary
            intent: Document intent
            document_id: Unique identifier for the document
            
        Returns:
            Dict with extracted data
        """
        content_str = json.dumps(content, indent=2)[:2000]  # Limit size for LLM
        
        messages = [
            {"role": "system", "content": f"You are a specialized AI for extracting information from {intent} documents in JSON format. Extract all relevant fields and return them in a clean JSON format."},
            {"role": "user", "content": f"Extract key information from this {intent} JSON document:\n\n{content_str}\n\nReturn only a JSON object with the extracted fields."}
        ]
        
        response = await self.query_llm(messages)
        
        try:
            extracted_data = json.loads(response)
            
            # Store extracted fields in memory
            for field, value in extracted_data.items():
                self.memory_store.store_field(document_id, field, value)
            
            return {
                "status": "success",
                "extracted_data": extracted_data,
                "method": "llm_extraction"
            }
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Failed to parse LLM response",
                "raw_response": response
            }
