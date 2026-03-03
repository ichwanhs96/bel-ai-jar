"""
Configuration management for bel-ai-jar
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

# File patterns excluded from diff analysis by default.
# These are lock files, build artefacts, and documentation that are not
# worth quizzing developers on.
DEFAULT_EXCLUDED_FILES: List[str] = [
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "dist/*",
    "build/*",
    "*.egg-info/*",
    "__pycache__/*",
    "*.pyc",
    "*.md",
]


class Config:
    """Configuration management class"""

    DEFAULT_CONFIG = {
        "total_questions": 3,
        "passing_grade": 100,
        "answer_options": 4,
        "additional_prompt": None,
        "strict_mode": True,
        "ai_model": "mistral",
        "model_params": {},
        "max_diff_lines": 1000,
        "excluded_files": DEFAULT_EXCLUDED_FILES,
    }

    def __init__(
        self,
        total_questions: int = 3,
        passing_grade: int = 100,
        answer_options: int = 4,
        additional_prompt: Optional[str] = None,
        strict_mode: bool = True,
        ai_model: str = "mistral",
        api_key: Optional[str] = None,
        model_params: Optional[Dict[str, Any]] = None,
        max_diff_lines: int = 1000,
        excluded_files: Optional[List[str]] = None,
    ):
        self.total_questions = total_questions
        self.passing_grade = passing_grade
        self.answer_options = answer_options
        self.additional_prompt = additional_prompt
        self.strict_mode = strict_mode
        self.ai_model = ai_model
        self.api_key = api_key
        self.model_params = model_params or {}
        self.max_diff_lines = max_diff_lines
        self.excluded_files = excluded_files if excluded_files is not None else list(DEFAULT_EXCLUDED_FILES)
        self.config_path = self._get_config_path()
    
    def _get_config_path(self) -> Path:
        """Get the configuration file path"""
        return Path(".bel-ai-jar.json")
    
    def save(self) -> None:
        """Save configuration to file.

        NOTE: API keys are never written to the config file for security reasons.
        Use environment variables (MISTRAL_API_KEY, OPENAI_API_KEY) instead.
        """
        config_data = {
            "total_questions": self.total_questions,
            "passing_grade": self.passing_grade,
            "answer_options": self.answer_options,
            "additional_prompt": self.additional_prompt,
            "strict_mode": self.strict_mode,
            "ai_model": self.ai_model,
            "model_params": self.model_params,
            "max_diff_lines": self.max_diff_lines,
            "excluded_files": self.excluded_files,
        }

        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2)
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file.

        API keys are resolved from environment variables at runtime and are
        never read from the config file.
        """
        if not self.config_path.exists():
            return self.DEFAULT_CONFIG

        with open(self.config_path, "r") as f:
            data = json.load(f)

        # Strip any api_key that may have been written by an older version
        data.pop("api_key", None)
        return data
    
    def delete_config(self) -> None:
        """Delete configuration file"""
        if self.config_path.exists():
            os.remove(self.config_path)
    
    @classmethod
    def from_file(cls) -> "Config":
        """Create Config instance from existing file"""
        config = cls()
        file_config = config.load()
        
        return cls(
            total_questions=file_config.get("total_questions", 3),
            passing_grade=file_config.get("passing_grade", 100),
            answer_options=file_config.get("answer_options", 4),
            additional_prompt=file_config.get("additional_prompt"),
            strict_mode=file_config.get("strict_mode", True),
            ai_model=file_config.get("ai_model", "mistral"),
            model_params=file_config.get("model_params", {}),
            max_diff_lines=file_config.get("max_diff_lines", 1000),
            excluded_files=file_config.get("excluded_files", list(DEFAULT_EXCLUDED_FILES)),
        )
    
    def __repr__(self) -> str:
        return f"Config(total_questions={self.total_questions}, passing_grade={self.passing_grade}, " \
               f"answer_options={self.answer_options}, strict_mode={self.strict_mode}, " \
               f"ai_model={self.ai_model})"