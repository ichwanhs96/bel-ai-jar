"""
Git hooks integration for bel-ai-jar
"""
import os
import subprocess
from pathlib import Path
from typing import List
from .config import Config
from .evaluation import evaluate_code_changes

# Known AI tool names/domains found in Co-Authored-By trailers
_AI_COAUTHOR_PATTERNS = [
    "anthropic",
    "claude",
    "copilot",
    "chatgpt",
    "openai",
    "gemini",
    "cursor",
    "codeium",
    "tabnine",
]


def is_ai_coauthored() -> bool:
    """Return True if the staged commit appears to be co-authored by an AI tool.

    Detection strategy (in order):
    1. BEL_AI_JAR_INTERACTIVE_COMMIT env var — set to '1' / 'true' to force-enable.
    2. .git/COMMIT_EDITMSG — git writes this before the pre-commit hook runs
       when the user passes -m "..." so Co-Authored-By lines are visible here.
    """
    if os.environ.get("BEL_AI_JAR_INTERACTIVE_COMMIT", "").lower() in ("1", "true", "yes"):
        return True

    commit_msg_path = Path(".git/COMMIT_EDITMSG")
    if commit_msg_path.exists():
        content = commit_msg_path.read_text(errors="replace").lower()
        for line in content.splitlines():
            if "co-authored-by:" in line:
                if any(pattern in line for pattern in _AI_COAUTHOR_PATTERNS):
                    return True

    return False


def setup_git_hooks() -> None:
    """Setup git hooks for bel-ai-jar"""
    hooks_dir = Path(".git/hooks")
    
    if not hooks_dir.exists():
        print("⚠️  Git hooks directory not found. Are you in a git repository?")
        return
    
    # Create pre-commit hook
    pre_commit_hook = hooks_dir / "pre-commit"
    
    hook_content = """#!/bin/bash
# bel-ai-jar pre-commit hook

# Reconnect stdin to the terminal so the user can answer questions
# This is the canonical fix for interactive git hooks
exec < /dev/tty

# Try to run evaluation - most terminals should work fine
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import sys
import os
sys.path.insert(0, os.getcwd())
from bel_ai_jar.git_hooks import evaluate_pre_commit
try:
    success = evaluate_pre_commit()
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'❌ bel-ai-jar error: {e}', file=sys.stderr)
    print('Run with --no-verify to skip or bel-ai-jar disable to disable hooks', file=sys.stderr)
    sys.exit(1)
" || exit 1
elif command -v python >/dev/null 2>&1; then
    python -c "
import sys
import os
sys.path.insert(0, os.getcwd())
from bel_ai_jar.git_hooks import evaluate_pre_commit
try:
    success = evaluate_pre_commit()
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'❌ bel-ai-jar error: {e}', file=sys.stderr)
    print('Run with --no-verify to skip or bel-ai-jar disable to disable hooks', file=sys.stderr)
    sys.exit(1)
" || exit 1
else
    echo "Error: Python not found" >&2
    exit 1
fi
"""
    
    with open(pre_commit_hook, "w") as f:
        f.write(hook_content)
    
    # Make it executable
    os.chmod(pre_commit_hook, 0o755)
    
    print(f"✅ Git hook created at {pre_commit_hook}")


def remove_git_hooks() -> None:
    """Remove bel-ai-jar git hooks"""
    hooks_dir = Path(".git/hooks")
    
    if not hooks_dir.exists():
        return
    
    pre_commit_hook = hooks_dir / "pre-commit"
    
    if pre_commit_hook.exists():
        # Check if this is our hook
        with open(pre_commit_hook, "r") as f:
            content = f.read()
            if "bel-ai-jar" in content:
                os.remove(pre_commit_hook)
                print(f"✅ Removed git hook at {pre_commit_hook}")


def evaluate_pre_commit() -> bool:
    """Evaluate code changes during pre-commit.

    Evaluation only runs when the commit is co-authored by an AI tool.
    Pure human commits are passed through immediately.
    """
    try:
        if not is_ai_coauthored():
            print("✅ No AI co-author detected — skipping bel-ai-jar evaluation.")
            print("   Tip: set BEL_AI_JAR_INTERACTIVE_COMMIT=1 to force evaluation.")
            return True

        # Load configuration
        config = Config.from_file()

        # Get staged changes
        staged_files = get_staged_files()

        if not staged_files:
            print("📝 No staged files to evaluate")
            return True

        # Get git diff for staged files
        diff_output = get_git_diff(staged_files)

        if not diff_output:
            print("📝 No changes to evaluate")
            return True

        # Evaluate code changes
        return evaluate_code_changes(diff_output, config)

    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        return False


def get_staged_files() -> List[str]:
    """Get list of staged files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []


def get_git_diff(files: List[str]) -> str:
    """Get git diff for specific files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"] + files,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""