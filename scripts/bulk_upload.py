#!/usr/bin/env python3
"""
Bulk upload script for BijutsuBase.

Uploads files from a local folder to BijutsuBase API recursively,
sorted by last modified time, with resume capability.
"""
from __future__ import annotations

import getpass
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Supported file extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".mpg"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


def get_progress_file_path(folder_path: Path) -> Path:
    """Get the path to the progress file for a given folder."""
    script_dir = Path(__file__).parent
    folder_name = folder_path.name or "root"
    # Sanitize folder name for filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in folder_name)
    return script_dir / f"{safe_name}_upload_progress.json"


def load_progress(progress_file: Path) -> dict:
    """Load progress from file if it exists."""
    if progress_file.exists():
        try:
            with open(progress_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load progress file: {e}")
    return {
        "folder": "",
        "started_at": "",
        "uploaded": [],
        "failed": {},
        "total_files": 0,
    }


def save_progress(progress_file: Path, progress: dict) -> None:
    """Save progress to file."""
    try:
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)
    except OSError as e:
        print(f"Warning: Could not save progress file: {e}")


def discover_files(folder: Path) -> list[Path]:
    """
    Recursively discover all supported media files in a folder.
    Returns files sorted by modification time (oldest first).
    """
    files = []
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)

    # Sort by modification time (oldest first)
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def authenticate(client: httpx.Client, base_url: str, username: str, password: str) -> bool:
    """Authenticate with the API and get session cookie."""
    login_url = f"{base_url}/api/auth/cookie/login"
    try:
        response = client.post(
            login_url,
            data={"username": username, "password": password},
        )
        if response.status_code == 200 or response.status_code == 204:
            print("Authentication successful!")
            return True
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "Bad request")
            print(f"Authentication failed: {error_detail}")
            return False
        else:
            print(f"Authentication failed with status {response.status_code}")
            return False
    except httpx.RequestError as e:
        print(f"Authentication request failed: {e}")
        return False


def upload_file(client: httpx.Client, base_url: str, file_path: Path) -> tuple[bool, str]:
    """
    Upload a single file to the API.
    Returns (success, message).
    """
    upload_url = f"{base_url}/api/upload/file"

    for attempt in range(MAX_RETRIES):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                response = client.put(upload_url, files=files, timeout=300.0)

            if response.status_code == 200:
                return True, "uploaded"
            elif response.status_code == 409:
                return True, "already exists"
            elif response.status_code == 401:
                return False, "authentication expired"
            else:
                error_detail = "unknown error"
                try:
                    error_detail = response.json().get("detail", error_detail)
                except Exception:
                    pass
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE ** (attempt + 1)
                    print(f"  Retry {attempt + 1}/{MAX_RETRIES} in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return False, f"HTTP {response.status_code}: {error_detail}"

        except httpx.TimeoutException:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_BASE ** (attempt + 1)
                print(f"  Timeout, retry {attempt + 1}/{MAX_RETRIES} in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return False, "timeout"

        except httpx.RequestError as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_BASE ** (attempt + 1)
                print(f"  Error, retry {attempt + 1}/{MAX_RETRIES} in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return False, str(e)

    return False, "max retries exceeded"


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("BijutsuBase Bulk Upload Script")
    print("=" * 60)
    print()

    # Get server configuration
    server = input("Server IP/hostname [localhost]: ").strip() or "localhost"
    port = input("Port [8000]: ").strip() or "8000"
    base_url = f"http://{server}:{port}"

    print()
    print(f"Target server: {base_url}")
    print()

    # Get credentials
    username = input("Username (email): ").strip()
    if not username:
        print("Error: Username is required")
        return 1

    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password is required")
        return 1

    print()

    # Get folder path
    folder_input = input("Folder path to upload: ").strip()
    if not folder_input:
        print("Error: Folder path is required")
        return 1

    folder = Path(folder_input).expanduser().resolve()
    if not folder.exists():
        print(f"Error: Folder does not exist: {folder}")
        return 1
    if not folder.is_dir():
        print(f"Error: Path is not a directory: {folder}")
        return 1

    print()
    print(f"Scanning folder: {folder}")

    # Discover files
    all_files = discover_files(folder)
    if not all_files:
        print("No supported media files found in the folder.")
        return 0

    print(f"Found {len(all_files)} media files")
    print()

    # Load progress
    progress_file = get_progress_file_path(folder)
    progress = load_progress(progress_file)

    # Check if resuming from previous run
    uploaded_set = set(progress.get("uploaded", []))
    if uploaded_set:
        print(f"Resuming from previous run: {len(uploaded_set)} files already uploaded")

    # Initialize progress if new run
    if not progress.get("started_at"):
        progress["started_at"] = datetime.now().isoformat()
    progress["folder"] = str(folder)
    progress["total_files"] = len(all_files)

    # Filter out already uploaded files
    files_to_upload = [f for f in all_files if str(f) not in uploaded_set]
    print(f"Files to upload: {len(files_to_upload)}")
    print()

    if not files_to_upload:
        print("All files have already been uploaded!")
        return 0

    # Create HTTP client with cookie persistence
    with httpx.Client(timeout=30.0) as client:
        # Authenticate
        print("Authenticating...")
        if not authenticate(client, base_url, username, password):
            return 1

        print()
        print("Starting upload...")
        print("-" * 60)

        # Upload files
        uploaded_count = 0
        skipped_count = len(uploaded_set)
        failed_count = 0
        exists_count = 0

        for i, file_path in enumerate(files_to_upload, start=1):
            relative_path = file_path.relative_to(folder) if file_path.is_relative_to(folder) else file_path.name
            progress_str = f"[{skipped_count + uploaded_count + exists_count + failed_count + 1}/{len(all_files)}]"

            print(f"{progress_str} {relative_path}...", end=" ", flush=True)

            success, message = upload_file(client, base_url, file_path)

            if success:
                if message == "already exists":
                    print(f"SKIP ({message})")
                    exists_count += 1
                else:
                    print("OK")
                    uploaded_count += 1
                # Mark as uploaded in progress
                progress["uploaded"].append(str(file_path))
            else:
                print(f"FAILED ({message})")
                failed_count += 1
                progress["failed"][str(file_path)] = message

                # Check if authentication expired
                if message == "authentication expired":
                    print()
                    print("Session expired. Please re-run the script to continue.")
                    save_progress(progress_file, progress)
                    return 1

            # Save progress periodically (every 10 files)
            if i % 10 == 0:
                save_progress(progress_file, progress)

        # Final save
        save_progress(progress_file, progress)

    print()
    print("-" * 60)
    print("Upload complete!")
    print()
    print(f"  Total files:     {len(all_files)}")
    print(f"  Previously done: {skipped_count}")
    print(f"  Uploaded:        {uploaded_count}")
    print(f"  Already existed: {exists_count}")
    print(f"  Failed:          {failed_count}")
    print()

    if failed_count > 0:
        print(f"Failed files are recorded in: {progress_file}")
        return 1

    # Clean up progress file on complete success
    if failed_count == 0 and progress_file.exists():
        try:
            progress_file.unlink()
            print("Progress file cleaned up (all files uploaded successfully)")
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nUpload interrupted. Progress has been saved.")
        print("Run the script again to resume.")
        sys.exit(130)
