import uvicorn
import argparse
import sys
import os

# Add the project root to Python path for proper importing
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    parser = argparse.ArgumentParser(description='Run the document triage system')
    parser.add_argument('--host', '-H', default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to bind the server to')
    parser.add_argument('--reload', '-r', action='store_true', help='Enable auto-reload')
    
    args = parser.parse_args()
    
    print(f"Starting server at http://{args.host}:{args.port}")
    uvicorn.run(
        "backend.main:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    )

if __name__ == "__main__":
    main()
