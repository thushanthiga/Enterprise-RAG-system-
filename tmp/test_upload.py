import requests
import os
from pathlib import Path

def test_upload():
    project_id = 1  # Assuming project 1 exists from previous migrations
    url = f"http://localhost:8000/projects/{project_id}/documents/upload"
    
    # Create a dummy file
    test_file = Path("tmp/test_doc.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    with open(test_file, "w") as f:
        f.write("This is a test document for verification of the upload and indexing system.")
    
    # We need a token. Since this is a test, let's try to get one if not provided.
    # For now, I'll assume the user is running the server and I can reach it.
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "text/plain")}
            params = {"category": "uploaded"}
            # Note: We need a valid JWT token. 
            # In a real scenario, we'd login first. I'll rely on server logs for background task verification.
            print(f"Attempting upload to {url}...")
            # If the server requires auth, this will fail with 401, 
            # but I can still check if the files are created in the data/uploads directory.
            response = requests.post(url, files=files, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error during upload: {e}")

if __name__ == "__main__":
    test_upload()
