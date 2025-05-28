import json
import email
from email import policy
from email.parser import Parser
from typing import Dict, Any, Union

# Try both import styles to support different ways of running the app
try:
    from backend.agents.base_agent import BaseAgent
    from backend.memory.memory_store import MemoryStore
except ImportError:
    from .base_agent import BaseAgent
    from ..memory.memory_store import MemoryStore

class EmailAgent(BaseAgent):
    """Agent for processing and extracting information from email content"""
    
    def __init__(self, memory_store: MemoryStore):
        super().__init__(memory_store)
    
    async def process(self, content: str, intent: str, document_id: str) -> Dict[str, Any]:
        """
        Process email content according to intent
        
        Args:
            content: Email content as text
            intent: Document intent (complaint, rfq, etc.)
            document_id: Unique identifier for the document
            
        Returns:
            Dict with processing results and extracted data
        """
        # Try to parse as email if it looks like an email
        parsed_email = self._parse_email(content)
        
        # If successful parsing, use the structured data
        if parsed_email:
            sender = parsed_email.get("sender", "Unknown")
            subject = parsed_email.get("subject", "")
            body = parsed_email.get("body", content)
        else:
            # If not parsable as email, use raw content
            sender = "Unknown"
            subject = ""
            body = content
        
        # Store basic fields
        self.memory_store.store_field(document_id, "sender", sender)
        self.memory_store.store_field(document_id, "subject", subject)
        
        # Extract fields based on intent using LLM
        extracted_fields = await self._extract_fields_by_intent(body, intent)
        
        # Store extracted fields in memory
        for field, value in extracted_fields.items():
            self.memory_store.store_field(document_id, field, value)
        
        # Determine urgency based on content and intent
        urgency = await self._determine_urgency(body, intent)
        self.memory_store.store_field(document_id, "urgency", urgency)
        
        # Prepare CRM-formatted data
        crm_data = {
            "sender": sender,
            "subject": subject,
            "intent": intent,
            "urgency": urgency,
            **extracted_fields
        }
        
        return {
            "status": "success",
            "extracted_data": crm_data,
            "is_parsed_email": parsed_email is not None
        }
    
    def _parse_email(self, content: str) -> Union[Dict[str, str], None]:
        """
        Try to parse content as an email
        
        Args:
            content: Potential email content
            
        Returns:
            Dict with sender, subject, body or None if parsing fails
        """
        try:
            # Check if content might be an email
            if "From:" in content or "Subject:" in content:
                parser = Parser(policy=policy.default)
                parsed_email = parser.parsestr(content)
                
                sender = parsed_email.get("From", "Unknown")
                subject = parsed_email.get("Subject", "")
                
                # Get email body
                body = ""
                if parsed_email.is_multipart():
                    for part in parsed_email.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = parsed_email.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                return {
                    "sender": sender,
                    "subject": subject,
                    "body": body
                }
        except Exception:
            # If parsing fails, return None
            pass
        
        return None
    
    async def _extract_fields_by_intent(self, content: str, intent: str) -> Dict[str, Any]:
        """
        Extract fields from email content based on intent
        
        Args:
            content: Email body content
            intent: Document intent (complaint, rfq, etc.)
            
        Returns:
            Dict of extracted fields
        """
        # Trim content to fit in LLM context
        trimmed_content = content[:2000]
        
        # Define extraction prompts based on intent
        if intent == "complaint":
            system_prompt = "You are an AI specialized in extracting information from customer complaint emails. Extract the issue, product/service, customer ID if available, and sentiment."
            field_list = "issue, product_or_service, customer_id (if available), sentiment (positive, neutral, negative)"
        elif intent == "rfq":
            system_prompt = "You are an AI specialized in extracting information from Request for Quote (RFQ) emails. Extract the items requested, quantities, desired delivery date, and any specific requirements."
            field_list = "items_requested, quantities, delivery_date, specific_requirements"
        elif intent == "invoice":
            system_prompt = "You are an AI specialized in extracting information from invoice-related emails. Extract the invoice number, amount, due date, and payment status if mentioned."
            field_list = "invoice_number, amount, due_date, payment_status"
        else:
            system_prompt = f"You are an AI specialized in extracting key information from emails with {intent} intent."
            field_list = "all relevant fields for this type of communication"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the following fields from this email: {field_list}. Respond with only a JSON object.\n\nEMAIL CONTENT:\n{trimmed_content}"}
        ]
        
        response = await self.query_llm(messages)
        
        try:
            extracted_data = json.loads(response)
            return extracted_data
        except json.JSONDecodeError:
            # If LLM doesn't return valid JSON, return empty dict
            return {}
    
    async def _determine_urgency(self, content: str, intent: str) -> str:
        """
        Determine the urgency level of an email
        
        Args:
            content: Email body content
            intent: Document intent
            
        Returns:
            Urgency level (high, medium, low)
        """
        # Trim content
        trimmed_content = content[:1000]
        
        messages = [
            {"role": "system", "content": "You are an AI that determines the urgency of emails. Classify as 'high', 'medium', or 'low'."},
            {"role": "user", "content": f"This email has been classified with intent: {intent}. Determine the urgency based on content and intent. Respond with only a single word: 'high', 'medium', or 'low'.\n\nEMAIL CONTENT:\n{trimmed_content}"}
        ]
        
        response = await self.query_llm(messages)
        response = response.strip().lower()
        
        # Normalize response
        if "high" in response:
            return "high"
        elif "medium" in response:
            return "medium"
        else:
            return "low"
