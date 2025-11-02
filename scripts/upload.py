#!/usr/bin/env python3
"""Script to upload a file to the BijutsuBase API."""
from __future__ import annotations

import sys
from pathlib import Path

import requests


def upload_file(file_path: str | Path, api_url: str = "http://localhost:8000") -> None:
    """
    Upload a file to the BijutsuBase API.
    
    Args:
        file_path: Path to the file to upload
        api_url: Base URL of the API (default: http://localhost:8000)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    if not file_path.is_file():
        print(f"Error: Path is not a file: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    upload_url = f"{api_url}/api/files/upload"
    
    print(f"Uploading {file_path.name} to {upload_url}...")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = requests.put(upload_url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Successfully uploaded file!")
            print(f"  SHA256: {result.get('sha256_hash', 'N/A')}")
            print(f"  Original filename: {result.get('original_filename', 'N/A')}")
            print(f"  File type: {result.get('file_type', 'N/A')}")
            print(f"  File size: {result.get('file_size', 'N/A')} bytes")
            if result.get('width') and result.get('height'):
                print(f"  Dimensions: {result.get('width')}x{result.get('height')}")
        elif response.status_code == 409:
            print(f"⚠ File already exists (409 Conflict)")
            print(f"  Response: {response.text}")
        else:
            print(f"✗ Upload failed with status {response.status_code}")
            print(f"  Response: {response.text}", file=sys.stderr)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}", file=sys.stderr)
        print("  Make sure the API server is running.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Default to test.jpeg in the same directory as the script
    script_dir = Path(__file__).parent
    default_file = script_dir / "test.jpeg"
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file
    
    # Allow overriding API URL via environment variable or second argument
    if len(sys.argv) > 2:
        api_url = sys.argv[2]
    else:
        import os
        api_url = os.getenv("API_URL", "http://localhost:8000")
    
    upload_file(file_path, api_url)

