"""
Tests for bel_ai_jar.config module
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from bel_ai_jar.config import Config


@pytest.fixture(autouse=True)
def tmp_cwd(tmp_path, monkeypatch):
    """Run every test in a temporary directory so config files don't pollute the project."""
    monkeypatch.chdir(tmp_path)


class TestConfigDefaults:
    def test_default_values(self):
        config = Config()
        assert config.total_questions == 3
        assert config.passing_grade == 100
        assert config.answer_options == 4
        assert config.additional_prompt is None
        assert config.strict_mode is True
        assert config.ai_model == "mistral"
        assert config.api_key is None
        assert config.model_params == {}

    def test_config_path(self):
        config = Config()
        assert config.config_path == Path(".bel-ai-jar.json")


class TestConfigSaveLoad:
    def test_save_creates_file(self):
        config = Config(total_questions=5)
        config.save()
        assert config.config_path.exists()

    def test_save_does_not_store_api_key(self):
        config = Config(api_key="super-secret-key")
        config.save()
        with open(config.config_path) as f:
            data = json.load(f)
        assert "api_key" not in data

    def test_load_returns_defaults_when_no_file(self):
        config = Config()
        data = config.load()
        assert data == Config.DEFAULT_CONFIG

    def test_save_and_load_roundtrip(self):
        config = Config(
            total_questions=5,
            passing_grade=80,
            answer_options=3,
            additional_prompt="Focus on security",
            strict_mode=False,
            ai_model="openai-gpt4",
        )
        config.save()

        loaded = Config.from_file()
        assert loaded.total_questions == 5
        assert loaded.passing_grade == 80
        assert loaded.answer_options == 3
        assert loaded.additional_prompt == "Focus on security"
        assert loaded.strict_mode is False
        assert loaded.ai_model == "openai-gpt4"

    def test_load_strips_legacy_api_key(self, tmp_path, monkeypatch):
        """Older versions may have written api_key to disk; load() must strip it."""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / ".bel-ai-jar.json"
        config_path.write_text(json.dumps({"total_questions": 3, "api_key": "leaked-key"}))

        config = Config()
        data = config.load()
        assert "api_key" not in data

    def test_from_file_uses_defaults_for_missing_keys(self):
        Config(total_questions=2).save()
        loaded = Config.from_file()
        # Keys not in file should fall back to defaults
        assert loaded.passing_grade == 100


class TestConfigDelete:
    def test_delete_removes_file(self):
        config = Config()
        config.save()
        assert config.config_path.exists()
        config.delete_config()
        assert not config.config_path.exists()

    def test_delete_no_op_when_no_file(self):
        config = Config()
        config.delete_config()  # Should not raise


class TestConfigRepr:
    def test_repr_contains_key_fields(self):
        config = Config(total_questions=7, ai_model="mistral")
        r = repr(config)
        assert "total_questions=7" in r
        assert "ai_model=mistral" in r
