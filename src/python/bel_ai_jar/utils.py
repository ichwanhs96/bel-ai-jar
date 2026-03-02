"""
Utility functions for bel-ai-jar
"""
import subprocess
from typing import List


def run_command(cmd: List[str], cwd: str = None) -> str:
    """Run a shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return e.stderr or str(e)