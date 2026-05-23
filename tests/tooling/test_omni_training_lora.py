from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = PROJECT_ROOT / "omni-training" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_jsonl  # noqa: E402
from training_utils import (  # noqa: E402
    format_training_examples,
    load_json_config,
    load_sft_jsonl,
    validate_training_config,
)


class OmniTrainingLoraTest(unittest.TestCase):
    def test_training_configs_are_loadable_and_valid(self) -> None:
        training_config = load_json_config(PROJECT_ROOT / "omni-training" / "configs" / "training_config.json")
        lora_config = load_json_config(PROJECT_ROOT / "omni-training" / "configs" / "lora_config.json")
        validate_training_config(training_config, lora_config)
        self.assertEqual(training_config["base_model"], "HuggingFaceTB/SmolLM2-360M-Instruct")
        self.assertEqual(lora_config["task_type"], "CAUSAL_LM")

    def test_sft_loader_and_formatter_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "mini.jsonl"
            write_jsonl(
                dataset_path,
                [
                    {"text": "<|system|>\nVocê é Omni\n<|assistant|>\nResposta 1"},
                    {"text": "<|system|>\nVocê é Omni\n<|assistant|>\nResposta 2"},
                ],
            )
            records = load_sft_jsonl(dataset_path)
            formatted = format_training_examples(records, max_samples=1)
            self.assertEqual(len(records), 2)
            self.assertEqual(len(formatted), 1)
            self.assertIn("Você é Omni", formatted[0]["text"])

    def test_invalid_training_config_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_training_config({"base_model": "x"}, {"r": 8})


if __name__ == "__main__":
    unittest.main()
