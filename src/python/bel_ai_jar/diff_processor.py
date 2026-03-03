"""
Diff processor for bel-ai-jar.
Filters and trims git diffs to reduce LLM token consumption.
"""
import fnmatch
import re
from typing import Dict, List

from .config import Config


def _matches_excluded(filepath: str, patterns: List[str]) -> bool:
    """Return True if filepath matches any excluded glob pattern."""
    basename = filepath.split("/")[-1]
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Patterns without a slash are matched against the basename only
        if "/" not in pattern and fnmatch.fnmatch(basename, pattern):
            return True
    return False


def _parse_diff_into_files(diff: str) -> List[Dict]:
    """Split a unified diff string into per-file sections."""
    sections: List[Dict] = []
    current_path: str | None = None
    current_lines: List[str] = []

    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            if current_path is not None:
                sections.append({"path": current_path, "lines": current_lines})
            match = re.match(r"^diff --git a/(.*) b/(.*)$", line)
            current_path = match.group(2) if match else ""
            current_lines = [line]
        elif current_path is not None:
            current_lines.append(line)

    if current_path is not None:
        sections.append({"path": current_path, "lines": current_lines})

    return sections


def _strip_to_additions(lines: List[str]) -> List[str]:
    """Keep file/hunk headers and added lines; drop context and deletions."""
    result = []
    for line in lines:
        if (
            line.startswith("diff ")
            or line.startswith("index ")
            or line.startswith("--- ")
            or line.startswith("+++ ")
            or line.startswith("@@ ")
        ):
            result.append(line)
        elif line.startswith("+"):
            # Actual addition (not the +++ file header already captured above)
            result.append(line)
        # Context lines (space prefix), deletions (- prefix), and meta (\) are dropped
    return result


def process_diff(diff: str, config: Config) -> tuple[str, dict]:
    """Filter and truncate a git diff to reduce LLM token consumption.

    Steps applied in order:
      1. Filter out files matching excluded_files patterns.
      2. Strip context lines and deletion lines (keep additions + headers).
      3. Truncate evenly across remaining files if still over max_diff_lines.

    Returns:
        (processed_diff, stats) where stats is a dict with diagnostic info:
          - original_lines: total lines before processing
          - filtered_files: number of files excluded
          - final_lines: total lines after processing
    """
    if not diff:
        return diff, {"original_lines": 0, "filtered_files": 0, "final_lines": 0}

    sections = _parse_diff_into_files(diff)
    original_lines = sum(len(s["lines"]) for s in sections)

    # Step 1: filter excluded files
    excluded_patterns = config.excluded_files or []
    included = [s for s in sections if not _matches_excluded(s["path"], excluded_patterns)]
    filtered_files = len(sections) - len(included)

    if not included:
        return "", {"original_lines": original_lines, "filtered_files": filtered_files, "final_lines": 0}

    # Step 2: strip to additions only
    for section in included:
        section["lines"] = _strip_to_additions(section["lines"])

    # Step 3: truncate to max_diff_lines, distributed evenly across files
    max_lines = config.max_diff_lines
    total = sum(len(s["lines"]) for s in included)

    if total > max_lines:
        lines_per_file = max(10, max_lines // len(included))
        for section in included:
            if len(section["lines"]) > lines_per_file:
                section["lines"] = section["lines"][:lines_per_file]

    final_lines = sum(len(s["lines"]) for s in included)
    result = "\n".join("\n".join(s["lines"]) for s in included)

    stats = {
        "original_lines": original_lines,
        "filtered_files": filtered_files,
        "final_lines": final_lines,
    }
    return result, stats
