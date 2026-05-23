from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@dataclass(slots=True)
class LoRAInferenceResult:
    text: str = ""
    model_used: bool = False
    confidence: float = 0.0
    fallback: bool = True
    reason: str = "adapter_missing"
    dataset_origin: str = ""
    adapter_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoRAInferenceEngine:
    """Optional LoRA-backed textual refinement.

    This engine is intentionally conservative: if the adapter or dependencies are
    missing, the runtime keeps the deterministic path untouched.
    """

    def __init__(self, project_root: Path, *, timeout_seconds: float = 4.0) -> None:
        self.project_root = Path(project_root).resolve()
        self.timeout_seconds = max(0.5, float(timeout_seconds))
        self.training_root = self.project_root / "omni-training"
        self.training_config_path = self.training_root / "configs" / "training_config.json"
        self._training_config = _safe_json(self.training_config_path)
        self._dataset_origin = str(self._training_config.get("dataset_path", "") or "").strip()
        self._adapter_path = self._resolve_adapter_path()
        self._model: Any = None
        self._tokenizer: Any = None
        self._load_error = ""

    @property
    def dataset_origin(self) -> str:
        return self._dataset_origin

    @property
    def adapter_path(self) -> Path:
        return self._adapter_path

    def adapter_available(self) -> bool:
        if not self._adapter_path.exists() or not self._adapter_path.is_dir():
            return False
        expected = (
            self._adapter_path / "adapter_config.json",
            self._adapter_path / "adapter_model.safetensors",
            self._adapter_path / "adapter_model.bin",
        )
        return any(path.exists() for path in expected)

    def generate_response(self, prompt: str, context: dict[str, Any] | None = None) -> LoRAInferenceResult:
        context = dict(context or {})
        if not self.adapter_available():
            return LoRAInferenceResult(
                fallback=True,
                model_used=False,
                confidence=0.0,
                reason="adapter_missing",
                dataset_origin=self.dataset_origin,
                adapter_path=str(self.adapter_path),
                metadata={"context_keys": sorted(context.keys())},
            )
        if not self._ensure_loaded():
            return LoRAInferenceResult(
                fallback=True,
                model_used=False,
                confidence=0.0,
                reason="adapter_load_failed",
                dataset_origin=self.dataset_origin,
                adapter_path=str(self.adapter_path),
                metadata={"error": self._load_error[:400]},
            )
        try:
            text = self._generate_text(prompt)
            if not text:
                return LoRAInferenceResult(
                    fallback=True,
                    model_used=False,
                    confidence=0.0,
                    reason="empty_model_response",
                    dataset_origin=self.dataset_origin,
                    adapter_path=str(self.adapter_path),
                )
            return LoRAInferenceResult(
                text=text,
                model_used=True,
                confidence=0.62,
                fallback=False,
                reason="adapter_inference",
                dataset_origin=self.dataset_origin,
                adapter_path=str(self.adapter_path),
                metadata={"context_keys": sorted(context.keys())},
            )
        except Exception as exc:
            return LoRAInferenceResult(
                fallback=True,
                model_used=False,
                confidence=0.0,
                reason="inference_error",
                dataset_origin=self.dataset_origin,
                adapter_path=str(self.adapter_path),
                metadata={"error": str(exc)[:400]},
            )

    def _resolve_adapter_path(self) -> Path:
        configured = str(self._training_config.get("output_dir", "") or "").strip()
        if configured:
            candidate = Path(configured)
            if not candidate.is_absolute():
                candidate = (self.project_root / candidate).resolve()
            return candidate
        return self.project_root / "omni-training" / "artifacts" / "lora"

    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True
        try:
            from peft import AutoPeftModelForCausalLM  # type: ignore
            from transformers import AutoTokenizer  # type: ignore
        except Exception as exc:  # pragma: no cover
            self._load_error = f"missing_ml_dependencies:{exc}"
            return False
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.adapter_path))
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            self._model = AutoPeftModelForCausalLM.from_pretrained(str(self.adapter_path))
            return True
        except Exception as exc:  # pragma: no cover
            self._load_error = str(exc)
            self._model = None
            self._tokenizer = None
            return False

    def _generate_text(self, prompt: str) -> str:
        if self._model is None or self._tokenizer is None:
            return ""
        encoded = self._tokenizer(
            str(prompt or "").strip(),
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )
        device = getattr(self._model, "device", None)
        if device is not None:
            encoded = {key: value.to(device) for key, value in encoded.items()}
        output = self._model.generate(
            **encoded,
            max_new_tokens=160,
            do_sample=False,
            temperature=0.2,
            repetition_penalty=1.05,
            pad_token_id=self._tokenizer.pad_token_id,
        )
        input_length = int(encoded["input_ids"].shape[-1])
        generated = output[0][input_length:]
        text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        return self._sanitize_output(text)

    @staticmethod
    def _sanitize_output(text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned:
            return ""
        for marker in ("<|assistant|>", "<|user|>", "<|system|>"):
            cleaned = cleaned.replace(marker, "").strip()
        if len(cleaned) > 2400:
            cleaned = cleaned[:2400].rstrip()
        return cleaned

