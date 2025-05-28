import json
import sqlite3
from typing import Dict, Any, List, Union
import datetime
import sys
import os
import base64

# Fix imports to work in all scenarios
try:
    # When running with the project root in Python path
    from database import get_db_connection
except ImportError:
    try:
        # When running as a module
        from ..database import get_db_connection
    except ImportError:
        # When running from backend directory directly
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from database import get_db_connection

class MemoryStore:
    """Shared memory store for maintaining context across agents"""
    
    def store_document(self, document_id: str, format: str, intent: str, content: Union[str, Dict, bytes]) -> None:
        """
        Store document information in the memory database
        
        Args:
            document_id: Unique identifier for the document
            format: Document format (pdf, json, email)
            intent: Document intent (invoice, rfq, etc.)
            content: Document content (may be serialized if binary)
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Normalize format (lowercase)
        format = format.lower() if format else "unknown"
        intent = intent.lower() if intent else "general"
        
        # Enhanced logging for debugging
        print(f"Storing document: {document_id} with format: {format}, intent: {intent}")
        
        # Serialize content if it's not a string
        if isinstance(content, dict):
            serialized_content = json.dumps(content)
        elif isinstance(content, bytes):
            # For PDF files, we'll store the base64 encoded content
            serialized_content = base64.b64encode(content).decode('utf-8')
            # If the content is very large, store a placeholder instead
            if len(serialized_content) > 1000000:  # 1MB limit
                serialized_content = "BINARY_CONTENT"  # We don't store large binary in SQLite
        else:
            # For string content, limit the size
            serialized_content = str(content)[:100000] if content else ""  # Truncate large content
        
        cursor.execute(
            'INSERT INTO documents (id, format, intent, timestamp, content) VALUES (?, ?, ?, ?, ?)',
            (document_id, format, intent, datetime.datetime.now().isoformat(), serialized_content)
        )
        
        conn.commit()
        conn.close()
    
    def store_field(self, document_id: str, field_name: str, field_value: Any) -> None:
        """
        Store an extracted field value
        
        Args:
            document_id: Document ID the field belongs to
            field_name: Name of the extracted field
            field_value: Value of the extracted field
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Serialize value if it's not a string
        if not isinstance(field_value, (str, int, float, bool)):
            serialized_value = json.dumps(field_value)
        else:
            serialized_value = str(field_value)
        
        # Use REPLACE to update if exists
        cursor.execute(
            'REPLACE INTO extracted_data (document_id, field_name, field_value, timestamp) VALUES (?, ?, ?, ?)',
            (document_id, field_name, serialized_value, datetime.datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve document information by ID
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            Dict with document information or None if not found
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        document = cursor.fetchone()
        
        if not document:
            conn.close()
            return None
        
        # Convert to dict
        document_dict = dict(document)
        
        # Get extracted fields
        cursor.execute('SELECT field_name, field_value FROM extracted_data WHERE document_id = ?', (document_id,))
        fields = cursor.fetchall()
        
        extracted_data = {}
        for field in fields:
            extracted_data[field['field_name']] = field['field_value']
        
        document_dict['extracted_data'] = extracted_data
        
        conn.close()
        return document_dict
    
    def get_field(self, document_id: str, field_name: str) -> Any:
        """
        Retrieve a specific field value
        
        Args:
            document_id: Document ID the field belongs to
            field_name: Name of the field to retrieve
            
        Returns:
            Field value or None if not found
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT field_value FROM extracted_data WHERE document_id = ? AND field_name = ?', 
            (document_id, field_name)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result['field_value']
        return None
    
    def get_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent document processing history
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of document processing records
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.id, d.format, d.intent, d.timestamp, 
                   e1.field_value as sender
            FROM documents d
            LEFT JOIN extracted_data e1 ON d.id = e1.document_id AND e1.field_name = 'sender'
            ORDER BY d.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append(dict(row))
        
        conn.close()
        return history
