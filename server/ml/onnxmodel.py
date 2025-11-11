"""ONNX model downloader and manager for Hugging Face Hub models."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional, Union, Mapping, Sequence, Dict

import numpy as np
import onnxruntime as ort
from huggingface_hub import HfApi, hf_hub_download
from utils.file_info import get_file_sha256


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
        tag_list_filename: str = "selected_tags.csv",
    ):
        """
        Initialize OnnxModel with Hugging Face repository information.
        
        Automatically downloads the model if not already present locally.
        
        Args:
            repo_id: Hugging Face repository ID (e.g., 'org/repo')
            filename: Path to the model file within the repository (e.g., 'path/to/model.onnx')
            revision: Optional revision (branch, tag, or commit hash). Defaults to 'main'.
            models_dir: Optional directory to store models. Defaults to 
                       ML_MODELS_DIR env var or 'ml/blobs' relative to server root.
            tag_list_filename: Filename of the tag list file in the repository. Defaults to 'selected_tags.csv'.
        """
        self.repo_id = repo_id
        self.filename = filename
        self.revision = revision
        
        # Validate tag_list_filename has .csv extension
        if not tag_list_filename.lower().endswith(".csv"):
            raise ValueError(
                f"tag_list_filename must have .csv extension. Got: {tag_list_filename}"
            )
        self.tag_list_filename = tag_list_filename
        
        # Determine models directory
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            models_dir_env = os.getenv("ML_MODELS_DIR")
            if models_dir_env:
                self.models_dir = Path(models_dir_env)
            else:
                # Default to ml/blobs relative to server root
                server_root = Path(__file__).parent.parent
                self.models_dir = server_root / "ml" / "blobs"
        
        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._api = HfApi()
        self._sha256: Optional[str] = None
        self._session: Optional[ort.InferenceSession] = None
        self._session_hash: Optional[str] = None
        self._session_providers: Optional[Sequence[str]] = None
        
    
    def _get_remote_sha256_for(self, path: str) -> Optional[str]:
        """
        Get SHA-256 hash from Hugging Face Hub metadata for a given file path.
        
        Args:
            path: Path to the file within the repository.
        
        Returns:
            SHA-256 hash if available in metadata, None otherwise.
        """
        try:
            paths_info = self._api.get_paths_info(
                repo_id=self.repo_id,
                paths=[path],
                revision=self.revision,
                expand=True,
            )
            
            if paths_info and len(paths_info) > 0:
                path_info = paths_info[0]
                # Check for LFS oid (SHA256) in the metadata
                if hasattr(path_info, "lfs") and path_info.lfs:
                    # LFS info can be a BlobLfsInfo object with sha256 attribute
                    # or a dict with "oid" key
                    if hasattr(path_info.lfs, "sha256"):
                        return path_info.lfs.sha256
                    elif isinstance(path_info.lfs, dict):
                        oid = path_info.lfs.get("oid")
                        if oid:
                            # LFS oid is SHA256, but sometimes prefixed with "sha256:"
                            return oid.replace("sha256:", "")
            
            return None
        except Exception:
            # If metadata fetch fails, return None (will compute after download)
            return None
    
    def _get_remote_sha256(self) -> Optional[str]:
        """
        Get SHA-256 hash from Hugging Face Hub metadata for the model file.
        
        Returns:
            SHA-256 hash if available in metadata, None otherwise.
        """
        return self._get_remote_sha256_for(self.filename)
    
    def _get_hashed_file_path(self, sha256: str, extension: str) -> Path:
        """
        Get path to a file using hash as filename.
        
        Args:
            sha256: SHA-256 hash of the file
            extension: File extension (e.g., '.onnx', '.csv')
            
        Returns:
            Path to the file: models_dir/<sha256>/<sha256>.<ext>
        """
        return self.models_dir / sha256 / f"{sha256}{extension}"
    
    def _get_model_path(self, sha256: str, extension: str) -> Path:
        """
        Get path to model file using hash as filename.
        
        Args:
            sha256: SHA-256 hash of the model
            extension: File extension (e.g., '.onnx')
            
        Returns:
            Path to the model file: models_dir/<sha256>/<sha256>.<ext>
        """
        return self._get_hashed_file_path(sha256, extension)
    
    
    
    def ensure_local(self) -> Path:
        """
        Ensure model is downloaded locally and return its path.
        
        This method:
        1. Fetches remote SHA-256 from Hugging Face metadata if available
        2. Checks if model already exists locally by SHA-256
        3. Downloads if not present
        4. Computes SHA-256 hash if not available from metadata
        5. Verifies integrity if file exists
        6. Also ensures the tag list file is downloaded and verified
        
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
            
        if not model_path.exists():
            # Download the model to a temp location first
            temp_dir = self.models_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            downloaded_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.filename,
                revision=self.revision,
                cache_dir=None,  # Don't use HF cache, store in our location
                local_dir=temp_dir,
            )
            
            # hf_hub_download returns the full path to the downloaded file
            downloaded_path = Path(downloaded_path)
            
            # Verify downloaded file matches expected hash before moving
            computed_hash = get_file_sha256(downloaded_path)
            if computed_hash != remote_sha256:
                downloaded_path.unlink()
                raise ValueError(
                    f"Downloaded file hash mismatch. Expected {remote_sha256}, "
                    f"got {computed_hash}"
                )
            
            # Move to final location (using hash as filename)
            model_path.parent.mkdir(parents=True, exist_ok=True)
            if downloaded_path != model_path:
                downloaded_path.rename(model_path)
        
        # Ensure tag list is downloaded to the model's directory
        # Store it alongside the model as tag_list_<model_hash>.csv
        tag_list_path = model_path.parent / f"tag_list_{self._sha256}.csv"
        
        if not tag_list_path.exists():
            # Download the tag list to a temp location first
            temp_dir = self.models_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            downloaded_tag_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.tag_list_filename,
                revision=self.revision,
                cache_dir=None,  # Don't use HF cache, store in our location
                local_dir=temp_dir,
            )
            
            # hf_hub_download returns the full path to the downloaded file
            downloaded_tag_path = Path(downloaded_tag_path)
            
            # Move to final location (same directory as model, as tag_list_<hash>.csv)
            tag_list_path.parent.mkdir(parents=True, exist_ok=True)
            downloaded_tag_path.rename(tag_list_path)
        
        return model_path
    
    @property
    def tag_list_path(self) -> Path:
        """
        Get the path to the local tag list file.
        
        Ensures the tag list is downloaded if not already present.
        
        Returns:
            Path to the local tag list file.
        """
        # Ensure model is downloaded to get the hash
        model_path = self.ensure_local()
        # Tag list is stored alongside the model as tag_list_<hash>.csv
        return model_path.parent / f"tag_list_{self._sha256}.csv"
    
    def initialize(
        self,
        providers: Optional[Sequence[str]] = None,
        sess_options: Optional[ort.SessionOptions] = None,
    ) -> ort.InferenceSession:
        """
        Initialize and preload the inference session.
        
        This method downloads the model (if needed) and creates the inference
        session, making it ready for use. Call this at server startup to avoid
        the initialization cost on the first inference request.
        
        Example:
            ```python
            model = OnnxModel(repo_id="org/repo", filename="model.onnx")
            model.initialize()  # Preload at startup - required before infer()
            # Later, inference calls will be fast
            outputs = model.infer(inputs)
            ```
        
        Args:
            providers: Optional sequence of execution providers.
                      If None, uses all available providers.
            sess_options: Optional ONNX Runtime session options.
        
        Returns:
            The initialized InferenceSession (also cached internally).
        """
        # Ensure model is downloaded locally
        model_path = self.ensure_local()
        
        # Set up providers (default to all available)
        if providers is None:
            providers = ort.get_available_providers()
        else:
            providers = list(providers)
        
        # Create and cache the session
        return self._get_session(model_path, providers, sess_options)
    
    def _get_session(
        self,
        model_path: Path,
        providers: Sequence[str],
        sess_options: Optional[ort.SessionOptions] = None,
    ) -> ort.InferenceSession:
        """
        Get or create a cached inference session for the given model path.
        
        Sessions are cached per instance. If the model path changes (e.g., 
        after a re-download), a new session will be created.
        
        Args:
            model_path: Path to the ONNX model file.
            providers: Execution providers to use.
            sess_options: Optional session options. If provided, session 
                        will be recreated even if cached.
        
        Returns:
            ONNX Runtime InferenceSession.
        """
        # Check if we need to recreate the session:
        # - No cached session exists
        # - Model hash changed (e.g., re-downloaded)
        # - Providers changed
        # - sess_options provided (can't easily compare, so recreate)
        providers_tuple = tuple(providers)
        if (
            self._session is None
            or self._session_hash != self._sha256
            or self._session_providers != providers_tuple
            or sess_options is not None
        ):
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=providers,
            )
            self._session_hash = self._sha256
            self._session_providers = providers_tuple
        
        return self._session
    
    def infer(
        self,
        inputs: Union[np.ndarray, Mapping[str, np.ndarray]],
        output_names: Optional[Sequence[str]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Run inference with ONNX Runtime using the cached session.
        
        The session must be initialized first by calling `initialize()`.
        This method uses the cached session created during initialization.
        
        Args:
            inputs: Either a single numpy array (will use first model input name)
                   or a dict mapping input names to numpy arrays.
            output_names: Optional sequence of output names to retrieve.
                         If None, returns all outputs.
        
        Returns:
            Dictionary mapping output names to numpy arrays.
            
        Raises:
            RuntimeError: If the session has not been initialized. Call `initialize()` first.
        """
        # Check if session has been initialized
        if self._session is None:
            raise RuntimeError(
                "Session not initialized. Call `initialize()` first before running inference."
            )
        
        session = self._session
        
        # Prepare input feed dictionary
        if isinstance(inputs, dict):
            feed = inputs
        else:
            # Single array input - use first model input name
            input_name = session.get_inputs()[0].name
            feed = {input_name: inputs}
        
        # Run inference
        results = session.run(output_names, feed)
        
        # Map results to output names
        if output_names is None:
            output_names = [output.name for output in session.get_outputs()]
        else:
            output_names = list(output_names)
        
        return dict(zip(output_names, results))
    
    async def infer_async(
        self,
        inputs: Union[np.ndarray, Mapping[str, np.ndarray]],
        output_names: Optional[Sequence[str]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Run inference asynchronously using a thread pool.
        
        This method runs the blocking `infer()` method in a thread pool,
        allowing multiple inference requests to run concurrently without
        blocking the event loop.
        
        Args:
            inputs: Either a single numpy array (will use first model input name)
                   or a dict mapping input names to numpy arrays.
            output_names: Optional sequence of output names to retrieve.
                         If None, returns all outputs.
        
        Returns:
            Dictionary mapping output names to numpy arrays.
            
        Raises:
            RuntimeError: If the session has not been initialized. Call `initialize()` first.
        """
        # Run the blocking infer() method in a thread pool
        return await asyncio.to_thread(self.infer, inputs, output_names)