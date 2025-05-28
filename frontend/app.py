import streamlit as st
import requests
import json
import time
import base64
from typing import Dict, Any
import os

# Define backend API URL
BACKEND_API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Document Triage System",
    page_icon="📑",
    layout="wide"
)

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "classification" not in st.session_state:
    st.session_state.classification = None
if "processed_result" not in st.session_state:
    st.session_state.processed_result = None
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

# Header
st.title("🤖 AI Document Triage System")
st.markdown("Upload documents for automatic classification and processing")

def fetch_history():
    """Fetch processing history from backend"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/history")
        if response.status_code == 200:
            return response.json()["history"]
        return []
    except Exception as e:
        st.error(f"Error fetching history: {str(e)}")
        return []

def classify_document(file=None, email_content=None, json_content=None):
    """Send document to backend for classification"""
    try:
        if file:
            files = {"file": file}
            response = requests.post(f"{BACKEND_API_URL}/classify", files=files)
        elif email_content:
            response = requests.post(
                f"{BACKEND_API_URL}/classify", 
                data={"email_content": email_content}
            )
        elif json_content:
            response = requests.post(
                f"{BACKEND_API_URL}/classify", 
                data={"json_content": json_content}
            )
        else:
            st.error("No content provided")
            return None
            
        if response.status_code == 200:
            result = response.json()
            # Add debug info
            if st.session_state.debug_mode:
                st.write("Classification API response:", result)
            return result
        else:
            st.error(f"Classification error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error communicating with backend: {str(e)}")
        return None

def process_document(document_id):
    """Process a classified document"""
    try:
        response = requests.post(f"{BACKEND_API_URL}/process/{document_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Processing error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error communicating with backend: {str(e)}")
        return None

# Sidebar with history
with st.sidebar:
    st.header("📜 Processing History")
    
    # Debug toggle
    st.session_state.debug_mode = st.checkbox("Enable Debug Mode", value=st.session_state.debug_mode)
    
    # Debug info section
    if st.session_state.debug_mode:
        st.subheader("🔍 Debug Information")
        
        # Read and display the current .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        
        if os.path.exists(env_path):
            with st.expander("Environment File Contents"):
                with open(env_path, 'r') as f:
                    env_content = f.read()
                    # Mask the API key for security
                    masked_content = env_content
                    if 'OPENROUTER_API_KEY' in env_content:
                        api_key_line = [line for line in env_content.splitlines() if 'OPENROUTER_API_KEY' in line][0]
                        api_key = api_key_line.split('=', 1)[1].strip()
                        if len(api_key) > 12:
                            masked_key = f"{api_key[:8]}...{api_key[-4:]}"
                            masked_content = env_content.replace(api_key, masked_key)
                    st.code(masked_content, language="properties")
        
        # Add backend connectivity test
        if st.button("Test Backend Connection"):
            try:
                response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
                if response.status_code == 200:
                    st.success(f"Backend connected! Status: {response.status_code}")
                else:
                    st.error(f"Backend error! Status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to backend: {str(e)}")
                
        # API Key checker
        if st.button("Check API Key"):
            try:
                response = requests.get(f"{BACKEND_API_URL}/check-api-key")
                if response.status_code == 200:
                    st.write(response.json())
                else:
                    st.error(f"API Key check failed: {response.text}")
            except Exception as e:
                st.error(f"API Key check error: {str(e)}")

    # Refresh button
    if st.button("🔄 Refresh History"):
        st.session_state.history = fetch_history()
    
    # Display history
    if not st.session_state.history:
        st.session_state.history = fetch_history()
    
    if st.session_state.history:
        for item in st.session_state.history:
            with st.expander(f"{item['format'].upper()}: {item['intent']} ({item['timestamp'][:10]})"):
                st.write(f"**ID:** {item['id']}")
                if item.get('sender'):
                    st.write(f"**Sender:** {item['sender']}")
                st.write(f"**Timestamp:** {item['timestamp']}")
    else:
        st.info("No processing history available")

# Main content
tab1, tab2, tab3 = st.tabs(["Upload Document", "Classification Result", "Processed Result"])

# Tab 1: Document Upload
with tab1:
    st.header("📤 Upload Document")
    
    # Create three columns for the three input methods
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Upload File")
        uploaded_file = st.file_uploader("Choose a PDF or JSON file", type=["pdf", "json"])
    
    with col2:
        st.subheader("Paste Email")
        email_input = st.text_area("Paste email content here", height=200)
    
    with col3:
        st.subheader("Paste JSON")
        json_input = st.text_area("Paste JSON content here", height=200)
    
    # Submit button
    if st.button("🔍 Submit for Classification"):
        with st.spinner("Classifying document..."):
            # Clear previous results
            st.session_state.classification = None
            st.session_state.processed_result = None
            st.session_state.document_id = None
            
            # Process based on input type
            if uploaded_file:
                classification = classify_document(file=uploaded_file)
            elif email_input:
                classification = classify_document(email_content=email_input)
            elif json_input:
                try:
                    # Validate JSON
                    json.loads(json_input)
                    classification = classify_document(json_content=json_input)
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
                    classification = None
            else:
                st.warning("Please provide a document to classify")
                classification = None
            
            if classification:
                st.session_state.classification = classification
                st.session_state.document_id = classification.get("document_id")
                st.success("Document classified successfully!")
                # Auto-switch to the Classification Result tab
                time.sleep(0.5)
                st.experimental_rerun()

# Tab 2: Classification Result
with tab2:
    st.header("🏷️ Classification Result")
    
    if st.session_state.classification:
        classification = st.session_state.classification
        
        # Debug: Print out the full classification response
        if st.session_state.debug_mode:
            st.expander("Classification Response Debug").json(classification)
        
        # Ensure we're using the right field names that match the backend response
        document_id = classification.get("document_id") or classification.get("id")
        format_type = classification.get("format", "Unknown")
        
        # Only show format, removing the intent display
        st.info(f"Document ID: {document_id}")
        
        # Store document_id for later use
        st.session_state.document_id = document_id
        
        if st.button("⚙️ Process Document"):
            with st.spinner("Processing document..."):
                result = process_document(document_id)
                if result:
                    st.session_state.processed_result = result
                    st.success("Document processed successfully!")
                    # Auto-switch to the Processed Result tab
                    time.sleep(0.5)
                    st.experimental_rerun()
    else:
        st.info("No document has been classified yet. Please upload a document first.")

# Tab 3: Processed Result
with tab3:
    st.header("📊 Processed Result")
    
    if st.session_state.processed_result:
        result = st.session_state.processed_result
        
        # Debug view of the full response
        if st.session_state.debug_mode:
            st.expander("Process Response Debug").json(result)
        
        st.subheader("Document Information")
        # Be flexible with field access - try multiple possible paths
        format_type = result.get("format", result.get("processing_result", {}).get("format", "Unknown"))
        intent_type = result.get("intent", result.get("processing_result", {}).get("intent", "Unknown"))
        doc_id = result.get("document_id", result.get("id", "N/A"))
        
        st.write(f"**Format:** {format_type.upper()}")
        st.write(f"**Intent:** {intent_type.title()}")
        st.write(f"**Document ID:** {doc_id}")
        
        st.subheader("Extracted Data")
        extracted_data = result.get("processing_result", {}).get("extracted_data", {})
        
        if extracted_data:
            # Create a formatted display of extracted data
            col1, col2 = st.columns(2)
            
            with col1:
                for key, value in list(extracted_data.items())[:len(extracted_data)//2 + 1]:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            with col2:
                for key, value in list(extracted_data.items())[len(extracted_data)//2 + 1:]:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    
            # Show JSON representation
            with st.expander("View as JSON"):
                st.json(extracted_data)
                
            # Option to download as JSON
            json_str = json.dumps(extracted_data, indent=2)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="extracted_data.json">Download JSON</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning("No data was extracted from this document")
            
        # Show processing status
        status = result.get("processing_result", {}).get("status", "unknown")
        if status == "success":
            st.success("Document processed successfully")
        elif status == "validation_failed":
            st.warning("Document processed with validation warnings")
            errors = result.get("processing_result", {}).get("validation_errors", [])
            if errors:
                with st.expander("View validation errors"):
                    for error in errors:
                        st.error(error)
        else:
            st.error(f"Processing status: {status}")
    else:
        st.info("No document has been processed yet. Please process a document first.")

# Footer
st.markdown("---")
st.markdown("AI Document Triage System - © 2025")
