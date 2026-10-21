#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(globals().get("__file__", sys.argv[0])).resolve()
ROOT = SCRIPT_PATH.parents[1]
SRC = ROOT / "src"
DEFAULT_MODEL_NAME = "users.brijendra_raghuwanshi.callcenter_asr_faster_whisper"
DEFAULT_ENDPOINT_NAME = "callcenter-asr-faster-whisper"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register and deploy the call center ASR pyfunc model to Databricks Model Serving."
    )
    parser.add_argument("--model-name", default=os.environ.get("ASR_MODEL_NAME", DEFAULT_MODEL_NAME))
    parser.add_argument("--endpoint-name", default=os.environ.get("ASR_ENDPOINT_NAME", DEFAULT_ENDPOINT_NAME))
    parser.add_argument("--experiment-name", default=os.environ.get("ASR_EXPERIMENT_NAME", "/Users/brijendra.raghuwanshi@databricks.com/callcenter_asr"))
    parser.add_argument("--whisper-model-size", default=os.environ.get("ASR_WHISPER_MODEL_SIZE", "base.en"))
    parser.add_argument("--device", default=os.environ.get("ASR_DEVICE", "cpu"))
    parser.add_argument("--compute-type", default=os.environ.get("ASR_COMPUTE_TYPE", "int8"))
    parser.add_argument("--workload-size", default=os.environ.get("ASR_WORKLOAD_SIZE", "Small"))
    parser.add_argument("--scale-to-zero", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-serving-endpoint", action="store_true")
    return parser.parse_args()


def require_imports() -> tuple[Any, Any, Any]:
    try:
        import mlflow
        import pandas as pd
        from databricks.sdk import WorkspaceClient
    except ImportError as exc:
        raise SystemExit(
            "Missing deployment dependency. Run this script on Databricks or install "
            "`mlflow`, `pandas`, and `databricks-sdk` first."
        ) from exc
    return mlflow, pd, WorkspaceClient


def log_and_register_model(args: argparse.Namespace) -> tuple[str, str]:
    mlflow, pd, _ = require_imports()

    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(args.experiment_name)

    from mlflow.models import ModelSignature
    from mlflow.types import ColSpec, Schema

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

    with mlflow.start_run(run_name="callcenter-asr-faster-whisper") as run:
        model_info = mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=str(ROOT / "scripts" / "asr_serving_model.py"),
            signature=signature,
            pip_requirements=[
                "mlflow>=2.16.0,<3",
                "pandas>=1.5.3,<3",
                "numpy>=1.24,<3",
                "faster-whisper>=1.1.0,<1.2",
                "huggingface-hub>=0.21,<1.0",
                "ctranslate2>=4.0,<4.6",
                "av>=11,<19",
            ],
            registered_model_name=args.model_name,
        )

    version = getattr(model_info, "registered_model_version", None)
    if not version:
        version = latest_model_version(args.model_name)
    print(f"Registered ASR model {args.model_name} version {version} from run {run.info.run_id}")
    return args.model_name, str(version)


def latest_model_version(model_name: str) -> str:
    mlflow, _, _ = require_imports()
    client = mlflow.MlflowClient()
    versions = client.search_model_versions(f"name='{model_name}'")
    if not versions:
        raise RuntimeError(f"No registered versions found for {model_name}")
    return str(max(int(version.version) for version in versions))


def deploy_serving_endpoint(args: argparse.Namespace, model_name: str, model_version: str) -> None:
    _, _, WorkspaceClient = require_imports()
    ws = WorkspaceClient()
    served_entity_name = "asr"
    config = {
        "served_entities": [
            {
                "name": served_entity_name,
                "entity_name": model_name,
                "entity_version": model_version,
                "workload_size": args.workload_size,
                "scale_to_zero_enabled": args.scale_to_zero,
            }
        ],
        "traffic_config": {
            "routes": [
                {
                    "served_entity_name": served_entity_name,
                    "traffic_percentage": 100,
                }
            ]
        },
    }

    api = ws.api_client
    endpoint_path = f"/api/2.0/serving-endpoints/{args.endpoint_name}"
    try:
        api.do("GET", endpoint_path)
        api.do("PUT", f"{endpoint_path}/config", body=config)
        print(f"Updated serving endpoint {args.endpoint_name} to {model_name} version {model_version}")
    except Exception:
        api.do(
            "POST",
            "/api/2.0/serving-endpoints",
            body={
                "name": args.endpoint_name,
                "config": config,
            },
        )
        print(f"Created serving endpoint {args.endpoint_name} for {model_name} version {model_version}")


def main() -> int:
    args = parse_args()
    model_name, model_version = log_and_register_model(args)
    if not args.skip_serving_endpoint:
        deploy_serving_endpoint(args, model_name, model_version)
    print("Set these app env vars after the endpoint is ready:")
    print(f"CALLCENTER_USECASE_ASR_ENDPOINT_NAME={args.endpoint_name}")
    print("CALLCENTER_USECASE_USE_DATABRICKS_ASR=true")
    print("CALLCENTER_USECASE_USE_SCRIPTED_TRANSCRIPT_FALLBACK=false")
    return 0


if __name__ == "__main__":
    main()
