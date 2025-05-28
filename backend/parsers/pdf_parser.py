import fitz  # PyMuPDF
from typing import Union

def extract_pdf_text(pdf_content: Union[bytes, str]) -> str:
    """
    Extract text from a PDF file
    
    Args:
        pdf_content: PDF content as bytes or file path
        
    Returns:
        Extracted text from the PDF
    """
    try:
        # Handle file path or bytes
        if isinstance(pdf_content, bytes):
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        else:
            pdf_document = fitz.open(pdf_content)
        
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text += page.get_text()
        
        pdf_document.close()
        return text
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_pdf_metadata(pdf_content: Union[bytes, str]) -> dict:
    """
    Extract metadata from a PDF file
    
    Args:
        pdf_content: PDF content as bytes or file path
        
    Returns:
        Dictionary of metadata
    """
    try:
        # Handle file path or bytes
        if isinstance(pdf_content, bytes):
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        else:
            pdf_document = fitz.open(pdf_content)
        
        metadata = pdf_document.metadata
        pdf_document.close()
        return metadata
    except Exception as e:
        return {"error": f"Error extracting PDF metadata: {str(e)}"}
