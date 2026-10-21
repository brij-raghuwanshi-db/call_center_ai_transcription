# Databricks notebook source
from __future__ import annotations

import json
from pathlib import Path

import mlflow
from mlflow.models import ModelSignature
from mlflow.types import ColSpec, Schema

MODEL_NAME = "classic_stable_84t3jv_catalog.callcenter.callcenter_asr_faster_whisper"
EXPERIMENT_NAME = "/Users/brijendra.raghuwanshi@databricks.com/callcenter_asr"
MODEL_FILE = "/Workspace/Users/brijendra.raghuwanshi@databricks.com/.ai_dev_kit/callcenter_asr/asr_serving_model.py"

PIP_REQUIREMENTS = [
    "mlflow>=2.16.0,<3",
    "pandas>=1.5.3,<3",
    "numpy>=1.24,<3",
    "faster-whisper>=1.1.0,<1.2",
    "huggingface-hub>=0.21,<1.0",
    "ctranslate2>=4.0,<4.6",
    "av>=11,<19",
]

if not Path(MODEL_FILE).exists():
    raise FileNotFoundError(MODEL_FILE)

import sys
import types

# log_model may import these while pickling/validating. Stub them so registration
# does not need Whisper weights; serving still installs the real packages.
faster_whisper = types.ModuleType("faster_whisper")


class WhisperModel:
    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, *args, **kwargs):
        return [], types.SimpleNamespace(language="en", duration=0.0)


faster_whisper.WhisperModel = WhisperModel
sys.modules["faster_whisper"] = faster_whisper

av = types.ModuleType("av")
av.open = lambda *args, **kwargs: None
sys.modules["av"] = av

# Load the pyfunc class without executing set_model().
ns: dict = {"__file__": MODEL_FILE}
exec(
    Path(MODEL_FILE).read_text().replace("mlflow.models.set_model(FasterWhisperASR())", "pass"),
    ns,
)
ModelCls = ns["FasterWhisperASR"]

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT_NAME)

signature = ModelSignature(
    inputs=Schema(
        [
            ColSpec("string", "call_id"),
            ColSpec("string", "chunk_id"),
            ColSpec("string", "audio_base64"),
            ColSpec("long", "sample_rate"),
            ColSpec("string", "language"),
        ]
    ),
    outputs=Schema(
        [
            ColSpec("string", "call_id"),
            ColSpec("string", "chunk_id"),
            ColSpec("string", "text"),
            ColSpec("string", "transcript"),
            ColSpec("double", "confidence"),
            ColSpec("long", "asr_latency_ms"),
        ]
    ),
)

with mlflow.start_run(run_name="callcenter-asr-faster-whisper-v4") as run:
    model_info = mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=ModelCls(),
        signature=signature,
        pip_requirements=PIP_REQUIREMENTS,
        registered_model_name=MODEL_NAME,
    )

version = str(getattr(model_info, "registered_model_version", "") or "")
dbutils.notebook.exit(
    json.dumps(
        {
            "model_name": MODEL_NAME,
            "version": version,
            "run_id": run.info.run_id,
            "pip_requirements": PIP_REQUIREMENTS,
        }
    )
)
