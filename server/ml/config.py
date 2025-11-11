"""ML model configuration for BijutsuBase."""
import os

import onnxruntime as ort

from ml.onnxmodel import OnnxModel

# Get ONNX model configuration from environment
ONNX_REPO_ID = os.getenv("ONNX_REPO_ID", "SmilingWolf/wd-v1-4-convnext-tagger-v2")
ONNX_FILENAME = os.getenv("ONNX_FILENAME", "model.onnx")
ONNX_REVISION = os.getenv("ONNX_REVISION", None)

# Configure ONNX Runtime session options for optimal performance
# These settings enable internal parallelism within each inference call
sess_options = ort.SessionOptions()

# Intra-operator parallelism: number of threads within a single operator
# Default uses all physical cores, but we can configure explicitly
intra_op_threads = int(os.getenv("ONNX_INTRA_OP_THREADS", "0"))  # 0 = use all cores
if intra_op_threads > 0:
    sess_options.intra_op_num_threads = intra_op_threads

# Inter-operator parallelism: parallel execution across different operators
# Enable if the model has independent operators that can run in parallel
enable_inter_op = os.getenv("ONNX_ENABLE_INTER_OP", "false").lower() == "true"
if enable_inter_op:
    sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
    inter_op_threads = int(os.getenv("ONNX_INTER_OP_THREADS", "2"))
    sess_options.inter_op_num_threads = inter_op_threads

# Create and initialize ONNX model instance with optimized session options
onnx_model = OnnxModel(
    repo_id=ONNX_REPO_ID,
    filename=ONNX_FILENAME,
    revision=ONNX_REVISION,
)
onnx_model.initialize(sess_options=sess_options)

