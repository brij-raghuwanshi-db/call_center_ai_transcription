from __future__ import annotations

import base64
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from mlflow.pyfunc import PythonModel
except ImportError:  # Keeps local app imports lightweight; deployment runs with MLflow.
    PythonModel = object


class FasterWhisperASR(PythonModel):
    """MLflow pyfunc-compatible ASR wrapper for Databricks Model Serving."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 1,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self._model = None

    def load_context(self, context: Any) -> None:
        self._patch_av_open()
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    @staticmethod
    def _patch_av_open() -> None:
        """faster-whisper 1.2.x still passes metadata_errors= to av.open; PyAV 19 removed it."""
        try:
            import av

            if getattr(av.open, "_callcenter_patched", False):
                return
            original_open = av.open

            def patched_open(*args: Any, **kwargs: Any):
                kwargs.pop("metadata_errors", None)
                return original_open(*args, **kwargs)

            patched_open._callcenter_patched = True  # type: ignore[attr-defined]
            av.open = patched_open
        except Exception:
            return

    def predict(self, context: Any, model_input: Any) -> list[dict[str, Any]]:
        rows = self._rows(model_input)
        return [self._transcribe_row(row) for row in rows]

    def _transcribe_row(self, row: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        audio_base64 = str(row.get("audio_base64") or "")
        if not audio_base64:
            return self._empty_result(row, "audio_base64 is required")

        language = str(row.get("language") or "en").split("-")[0]
        suffix = self._suffix(row)
        audio_bytes = base64.b64decode(audio_base64, validate=False)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(audio_bytes)
            audio_path = Path(handle.name)

        try:
            if self._model is None:
                self.load_context(None)
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                beam_size=self.beam_size,
                vad_filter=False,
                condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt="A healthcare call center conversation between a patient and an agent.",
            )
            segment_list = list(segments)
            text = " ".join(segment.text.strip() for segment in segment_list).strip()
            confidence = self._confidence(segment_list)
            duration = getattr(info, "duration", None)
            return {
                "call_id": row.get("call_id"),
                "chunk_id": row.get("chunk_id"),
                "text": text,
                "transcript": text,
                "language": getattr(info, "language", language),
                "confidence": confidence,
                "duration_seconds": duration,
                "asr_latency_ms": int((time.perf_counter() - started) * 1000),
                "segments": [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                    }
                    for segment in segment_list
                ],
            }
        except Exception as exc:
            return self._empty_result(row, str(exc))
        finally:
            audio_path.unlink(missing_ok=True)

    @staticmethod
    def _rows(model_input: Any) -> list[dict[str, Any]]:
        if hasattr(model_input, "to_dict"):
            return model_input.to_dict(orient="records")
        if isinstance(model_input, list):
            return [dict(row) for row in model_input]
        if isinstance(model_input, dict):
            if "dataframe_records" in model_input:
                return [dict(row) for row in model_input["dataframe_records"]]
            if "inputs" in model_input and isinstance(model_input["inputs"], dict):
                return [dict(model_input["inputs"])]
            return [dict(model_input)]
        return [{}]

    @staticmethod
    def _suffix(row: dict[str, Any]) -> str:
        filename = str(row.get("filename") or "").lower()
        if filename.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm")):
            return Path(filename).suffix
        mime_type = str(row.get("mime_type") or "").lower()
        if "wav" in mime_type:
            return ".wav"
        if "webm" in mime_type:
            return ".webm"
        return ".wav"

    @staticmethod
    def _confidence(segments: list[Any]) -> float:
        if not segments:
            return 0.0
        probabilities = [
            float(getattr(segment, "avg_logprob", -1.0))
            for segment in segments
            if getattr(segment, "avg_logprob", None) is not None
        ]
        if not probabilities:
            return 0.8
        # Convert the negative log-probability range into a bounded demo confidence.
        return max(0.0, min(0.99, 1.0 + (sum(probabilities) / len(probabilities))))

    @staticmethod
    def _empty_result(row: dict[str, Any], error: str) -> dict[str, Any]:
        return {
            "call_id": row.get("call_id"),
            "chunk_id": row.get("chunk_id"),
            "text": "",
            "transcript": "",
            "confidence": 0.0,
            "error": error,
        }
