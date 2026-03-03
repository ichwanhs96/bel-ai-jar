"""
Tests for bel_ai_jar.diff_processor module
"""
import pytest
from bel_ai_jar.config import Config
from bel_ai_jar.diff_processor import (
    _matches_excluded,
    _parse_diff_into_files,
    _strip_to_additions,
    process_diff,
)

SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
index 000000..111111 100644
--- a/app.py
+++ b/app.py
@@ -1,5 +1,8 @@
 import os
-old_line = 1
+new_line = 1
+
+def greet(name):
+    return f"Hello {name}"
diff --git a/package-lock.json b/package-lock.json
index 000000..222222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,3 +1,3 @@
-{"version": "1"}
+{"version": "2"}
"""


@pytest.fixture()
def default_config():
    return Config()


class TestMatchesExcluded:
    def test_exact_filename_match(self):
        assert _matches_excluded("package-lock.json", ["package-lock.json"])

    def test_glob_extension_match(self):
        assert _matches_excluded("path/to/file.lock", ["*.lock"])

    def test_glob_in_directory(self):
        assert _matches_excluded("dist/bundle.js", ["dist/*"])

    def test_basename_matched_without_path(self):
        assert _matches_excluded("some/nested/path/yarn.lock", ["yarn.lock"])

    def test_no_match(self):
        assert not _matches_excluded("src/app.py", ["*.lock", "dist/*"])

    def test_md_pattern(self):
        assert _matches_excluded("README.md", ["*.md"])
        assert _matches_excluded("docs/guide.md", ["*.md"])


class TestParseDiffIntoFiles:
    def test_splits_into_two_files(self):
        sections = _parse_diff_into_files(SAMPLE_DIFF)
        assert len(sections) == 2
        assert sections[0]["path"] == "app.py"
        assert sections[1]["path"] == "package-lock.json"

    def test_empty_diff(self):
        assert _parse_diff_into_files("") == []

    def test_each_section_starts_with_diff_header(self):
        for section in _parse_diff_into_files(SAMPLE_DIFF):
            assert section["lines"][0].startswith("diff --git")


class TestStripToAdditions:
    def test_keeps_addition_lines(self):
        lines = ["+new_line = 1", "+def greet(name):"]
        assert _strip_to_additions(lines) == lines

    def test_drops_context_lines(self):
        lines = [" import os", "+new_line = 1", " other context"]
        result = _strip_to_additions(lines)
        assert " import os" not in result
        assert " other context" not in result
        assert "+new_line = 1" in result

    def test_drops_deletion_lines(self):
        lines = ["-old_line = 1", "+new_line = 1"]
        result = _strip_to_additions(lines)
        assert "-old_line = 1" not in result

    def test_keeps_hunk_and_file_headers(self):
        lines = ["diff --git a/f b/f", "--- a/f", "+++ b/f", "@@ -1,2 +1,3 @@"]
        result = _strip_to_additions(lines)
        assert result == lines


class TestProcessDiff:
    def test_filters_excluded_files(self, default_config):
        result, stats = process_diff(SAMPLE_DIFF, default_config)
        assert "package-lock.json" not in result
        assert stats["filtered_files"] == 1

    def test_keeps_non_excluded_files(self, default_config):
        result, stats = process_diff(SAMPLE_DIFF, default_config)
        assert "app.py" in result

    def test_strips_deletions_and_context(self, default_config):
        result, stats = process_diff(SAMPLE_DIFF, default_config)
        assert "-old_line" not in result
        assert " import os" not in result

    def test_keeps_additions(self, default_config):
        result, stats = process_diff(SAMPLE_DIFF, default_config)
        assert "+new_line" in result
        assert "+def greet" in result

    def test_empty_diff_returns_empty(self, default_config):
        result, stats = process_diff("", default_config)
        assert result == ""
        assert stats["final_lines"] == 0

    def test_all_files_excluded_returns_empty(self):
        config = Config(excluded_files=["*.py", "*.json"])
        result, stats = process_diff(SAMPLE_DIFF, config)
        assert result == ""
        assert stats["filtered_files"] == 2

    def test_truncates_to_max_diff_lines(self):
        # Build a diff that is 200 addition lines
        big_diff = "diff --git a/big.py b/big.py\n--- a/big.py\n+++ b/big.py\n@@ -1 +1 @@\n"
        big_diff += "\n".join(f"+line_{i}" for i in range(200))
        config = Config(max_diff_lines=50, excluded_files=[])
        result, stats = process_diff(big_diff, config)
        assert stats["final_lines"] <= 50

    def test_stats_reflect_changes(self, default_config):
        _, stats = process_diff(SAMPLE_DIFF, default_config)
        assert stats["original_lines"] > stats["final_lines"]
        assert stats["filtered_files"] >= 1

    def test_no_excluded_config_keeps_all_files(self):
        config = Config(excluded_files=[])
        result, stats = process_diff(SAMPLE_DIFF, config)
        assert stats["filtered_files"] == 0
        assert "package-lock.json" in result
