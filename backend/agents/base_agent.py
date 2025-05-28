import json
import aiohttp
from abc import ABC, abstractmethod
import uuid
import os
import logging

# Try both import styles to support different ways of running the app
try:
    from backend.memory.memory_store import MemoryStore
    from backend.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, DEFAULT_MODEL
except ImportError:
    try:
        from ..memory.memory_store import MemoryStore
        from ..config import OPENROUTER_API_KEY, OPENROUTER_API_URL, DEFAULT_MODEL
    except ImportError:
        # Direct import as a fallback
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from memory.memory_store import MemoryStore
        from config import OPENROUTER_API_KEY, OPENROUTER_API_URL, DEFAULT_MODEL

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        
        # Get API key directly from config
        self.api_key = OPENROUTER_API_KEY
        
        # Remove any placeholder values
        if self.api_key == "your_openrouter_api_here":
            self.api_key = ""
            
        self.api_url = OPENROUTER_API_URL
        self.model = DEFAULT_MODEL
        
        # Log API key info (masked)
        if not self.api_key:
            logging.error("OpenRouter API key is missing or empty!")
        else:
            masked = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "[invalid format]"
            logging.debug(f"API key loaded: {masked}")
    
    async def query_llm(self, messages, temperature=0.7):
        """Send a request to the OpenRouter API and get response"""
        if not self.api_key:
            raise Exception("OpenRouter API key not configured. Please add it to your .env file.")
            
        # Prepare headers exactly as required by OpenRouter
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",  # OpenRouter requires this
            "X-Title": "AI Document Triage System"    # Helpful for OpenRouter logs
        }
        
        # Print debug info to console to verify API key
        api_key_masked = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "[invalid]"
        print(f"DEBUG: Using API key: {api_key_masked}")
        print(f"DEBUG: Using model: {self.model}")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Print the full URL and first few characters of the API key to debug
                print(f"DEBUG: Sending request to {self.api_url}")
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    
                    # Always print response for debugging
                    print(f"DEBUG: Response status: {response.status}")
                    print(f"DEBUG: Response: {response_text[:300]}...")
                    
                    if response.status != 200:
                        raise Exception(f"LLM API error: {response.status}, {response_text}")
                    
                    response_data = json.loads(response_text)
                    return response_data["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            error_msg = f"Network error when contacting API: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
    
    def generate_id(self):
        """Generate a unique ID for a document"""
        return str(uuid.uuid4())
    
    @abstractmethod
    async def process(self, content, intent, document_id=None):
        """Process the document content according to agent specialty"""
        pass
