"""
Tests for bel_ai_jar.git_hooks module
"""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bel_ai_jar.git_hooks import (
    get_git_diff,
    get_staged_files,
    is_ai_coauthored,
    remove_git_hooks,
    setup_git_hooks,
)


@pytest.fixture()
def fake_git_repo(tmp_path):
    """Create a minimal fake git repository structure."""
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return tmp_path


class TestSetupGitHooks:
    def test_creates_pre_commit_hook(self, fake_git_repo, monkeypatch):
        monkeypatch.chdir(fake_git_repo)
        setup_git_hooks()
        hook_path = fake_git_repo / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()

    def test_hook_is_executable(self, fake_git_repo, monkeypatch):
        monkeypatch.chdir(fake_git_repo)
        setup_git_hooks()
        hook_path = fake_git_repo / ".git" / "hooks" / "pre-commit"
        assert os.access(hook_path, os.X_OK)

    def test_hook_contains_bel_ai_jar(self, fake_git_repo, monkeypatch):
        monkeypatch.chdir(fake_git_repo)
        setup_git_hooks()
        hook_path = fake_git_repo / ".git" / "hooks" / "pre-commit"
        assert "bel-ai-jar" in hook_path.read_text()

    def test_warns_when_no_git_repo(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        setup_git_hooks()
        out = capsys.readouterr().out
        assert "not found" in out.lower() or "git" in out.lower()


class TestRemoveGitHooks:
    def test_removes_bel_ai_jar_hook(self, fake_git_repo, monkeypatch):
        monkeypatch.chdir(fake_git_repo)
        setup_git_hooks()
        hook_path = fake_git_repo / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        remove_git_hooks()
        assert not hook_path.exists()

    def test_does_not_remove_unrelated_hook(self, fake_git_repo, monkeypatch):
        monkeypatch.chdir(fake_git_repo)
        hook_path = fake_git_repo / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/bin/bash\necho 'custom hook'\n")
        remove_git_hooks()
        assert hook_path.exists()

    def test_no_op_when_hooks_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        remove_git_hooks()  # Should not raise


class TestGetStagedFiles:
    def test_returns_list_of_files(self):
        mock_result = MagicMock()
        mock_result.stdout = "file_a.py\nfile_b.py\n"
        with patch("subprocess.run", return_value=mock_result):
            files = get_staged_files()
        assert files == ["file_a.py", "file_b.py"]

    def test_returns_empty_list_on_error(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            files = get_staged_files()
        assert files == []

    def test_ignores_empty_lines(self):
        mock_result = MagicMock()
        mock_result.stdout = "file_a.py\n\nfile_b.py\n"
        with patch("subprocess.run", return_value=mock_result):
            files = get_staged_files()
        assert "" not in files


class TestIsAiCoauthored:
    def test_env_var_override_true(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BEL_AI_JAR_INTERACTIVE_COMMIT", "1")
        assert is_ai_coauthored() is True

    def test_env_var_override_true_values(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        for val in ("true", "yes", "TRUE"):
            monkeypatch.setenv("BEL_AI_JAR_INTERACTIVE_COMMIT", val)
            assert is_ai_coauthored() is True

    def test_env_var_not_set_returns_false(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BEL_AI_JAR_INTERACTIVE_COMMIT", raising=False)
        assert is_ai_coauthored() is False

    def test_detects_claude_coauthor(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BEL_AI_JAR_INTERACTIVE_COMMIT", raising=False)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "COMMIT_EDITMSG").write_text(
            "feat: add feature\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
        )
        assert is_ai_coauthored() is True

    def test_detects_copilot_coauthor(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BEL_AI_JAR_INTERACTIVE_COMMIT", raising=False)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "COMMIT_EDITMSG").write_text(
            "fix: bug\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>\n"
        )
        assert is_ai_coauthored() is True

    def test_ignores_human_coauthor(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BEL_AI_JAR_INTERACTIVE_COMMIT", raising=False)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "COMMIT_EDITMSG").write_text(
            "refactor: cleanup\n\nCo-Authored-By: John Doe <john@example.com>\n"
        )
        assert is_ai_coauthored() is False

    def test_no_commit_msg_file_returns_false(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BEL_AI_JAR_INTERACTIVE_COMMIT", raising=False)
        assert is_ai_coauthored() is False


class TestGetGitDiff:
    def test_returns_diff_output(self):
        mock_result = MagicMock()
        mock_result.stdout = "+def foo(): pass\n"
        with patch("subprocess.run", return_value=mock_result):
            diff = get_git_diff(["foo.py"])
        assert "+def foo(): pass" in diff

    def test_returns_empty_string_on_error(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            diff = get_git_diff(["foo.py"])
        assert diff == ""
