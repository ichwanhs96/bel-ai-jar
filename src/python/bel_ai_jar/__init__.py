"""
Bel-ai-jar library - Git hooks for AI-generated code understanding
"""
from .cli import main
from .config import Config
from .diff_processor import process_diff
from .git_hooks import setup_git_hooks, remove_git_hooks
from .evaluation import evaluate_code_changes

__version__ = "0.1.0"
__all__ = ["main", "Config", "process_diff", "setup_git_hooks", "remove_git_hooks", "evaluate_code_changes"]