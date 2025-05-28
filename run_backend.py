import sys
import os
import uvicorn

# Add the project root to Python path to fix imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

def main():
    """
    Run the backend server with correct import paths
    """
    print("Starting AI Document Triage System backend...")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()
