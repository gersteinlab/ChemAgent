import os

import pytest
import yaml

from XAgent.llama_father import parse_literal


def test_parse_literal_accepts_python_and_fenced_literals():
    assert parse_literal("{'final_answer': '2'}") == {"final_answer": "2"}
    assert parse_literal("```json\n[{\"goal\": \"x\"}]\n```") == [{"goal": "x"}]


def test_parse_literal_does_not_execute_code():
    with pytest.raises(ValueError):
        parse_literal("__import__('os').system('echo pwned')")


def test_default_config_memory_paths_exist():
    with open("assets/config.yml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    for key in ("save_dir", "plan_save_dir"):
        assert os.path.isfile(os.path.join(config[key], "docstore.json")), key
