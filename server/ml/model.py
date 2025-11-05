"""ONNX model downloader and manager for Hugging Face Hub models."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, hf_hub_download


class OnnxModel:
    """
    Manages downloading and caching ONNX models from Hugging Face Hub.
    
    Models are stored locally by SHA-256 hash to avoid re-downloading.
    Files are organized as: models_dir/<sha256>/<sha256>.<ext>
    The SHA-256 hash is fetched from Hugging Face metadata when available,
    or computed after download.
    """
    
    def __init__(
        self,
        repo_id: str,
        filename: str,
        revision: Optional[str] = None,
        models_dir: Optional[str] = None,
    ):
        """
        Initialize OnnxModel with Hugging Face repository information.
        
        Automatically downloads the model if not already present locally.
        
        Args:
            repo_id: Hugging Face repository ID (e.g., 'org/repo')
            filename: Path to the model file within the repository (e.g., 'path/to/model.onnx')
            revision: Optional revision (branch, tag, or commit hash). Defaults to 'main'.
            models_dir: Optional directory to store models. Defaults to 
                       ML_MODELS_DIR env var or 'ml/models' relative to server root.
        """
        self.repo_id = repo_id
        self.filename = filename
        self.revision = revision
        
        # Determine models directory
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            models_dir_env = os.getenv("ML_MODELS_DIR")
            if models_dir_env:
                self.models_dir = Path(models_dir_env)
            else:
                # Default to ml/models relative to server root
                server_root = Path(__file__).parent.parent
                self.models_dir = server_root / "ml" / "models"
        
        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._api = HfApi()
        self._sha256: Optional[str] = None
        self._local_path: Optional[Path] = None
        
    
    def _get_remote_sha256(self) -> Optional[str]:
        """
        Get SHA-256 hash from Hugging Face Hub metadata.
        
        Returns:
            SHA-256 hash if available in metadata, None otherwise.
        """
        try:
            paths_info = self._api.get_paths_info(
                repo_id=self.repo_id,
                paths=[self.filename],
                revision=self.revision,
                expand=True,
            )
            
            if paths_info and len(paths_info) > 0:
                path_info = paths_info[0]
                # Check for LFS oid (SHA256) in the metadata
                if hasattr(path_info, "lfs") and path_info.lfs:
                    oid = path_info.lfs.get("oid")
                    if oid:
                        # LFS oid is SHA256, but sometimes prefixed with "sha256:"
                        return oid.replace("sha256:", "")
            
            return None
        except Exception:
            # If metadata fetch fails, return None (will compute after download)
            return None
    
    def _compute_sha256(self, file_path: Path) -> str:
        """
        Compute SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            SHA-256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _get_model_path(self, sha256: str, extension: str) -> Path:
        """
        Get path to model file using hash as filename.
        
        Args:
            sha256: SHA-256 hash of the model
            extension: File extension (e.g., '.onnx')
            
        Returns:
            Path to the model file: models_dir/<sha256>/<sha256>.<ext>
        """
        return self.models_dir / sha256 / f"{sha256}{extension}"
    
    def _verify_file_hash(self, file_path: Path, expected_sha256: str) -> bool:
        """
        Verify file matches expected SHA-256 hash.
        
        Args:
            file_path: Path to file to verify
            expected_sha256: Expected SHA-256 hash
            
        Returns:
            True if hash matches, False otherwise
        """
        if not file_path.exists():
            return False
        
        computed_hash = self._compute_sha256(file_path)
        return computed_hash == expected_sha256
    
    def ensure_local(self) -> Path:
        """
        Ensure model is downloaded locally and return its path.
        
        This method:
        1. Fetches remote SHA-256 from Hugging Face metadata if available
        2. Checks if model already exists locally by SHA-256
        3. Downloads if not present
        4. Computes SHA-256 hash if not available from metadata
        5. Verifies integrity if file exists
        
        Returns:
            Path to the local ONNX model file
            
        Raises:
            Exception: If download fails or file verification fails
        """
        # Get file extension from original filename
        extension = Path(self.filename).suffix
        
        # Try to get SHA-256 from remote metadata first
        remote_sha256 = self._get_remote_sha256()
        
        if not remote_sha256:
            raise ValueError("No remote SHA-256 hash available")
        
        self._sha256 = remote_sha256
        # Check if we already have this model (path encodes the hash)
        model_path = self._get_model_path(remote_sha256, extension)
            
        if model_path.exists():
            self._local_path = model_path
            return model_path
        
        # Download the model to a temp location first
        temp_dir = self.models_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        downloaded_path = hf_hub_download(
            repo_id=self.repo_id,
            filename=self.filename,
            revision=self.revision,
            cache_dir=None,  # Don't use HF cache, store in our location
            local_dir=temp_dir,
            local_dir_use_symlinks=False,
        )
        
        # hf_hub_download returns the full path to the downloaded file
        downloaded_path = Path(downloaded_path)
        
        # Verify downloaded file matches expected hash before moving
        if not self._verify_file_hash(downloaded_path, remote_sha256):
            downloaded_path.unlink()
            raise ValueError(
                f"Downloaded file hash mismatch. Expected {remote_sha256}, "
                f"got {self._compute_sha256(downloaded_path)}"
            )
        
        # Move to final location (using hash as filename)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if downloaded_path != model_path:
            downloaded_path.rename(model_path)
        
        self._local_path = model_path
        return model_path