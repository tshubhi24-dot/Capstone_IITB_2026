"""Known-secret guard checks against temporary Git repositories and invented keys."""
import subprocess
import sys

import pytest

from ops import check_secrets as guard


@pytest.fixture
def repository(tmp_path, monkeypatch):
    repo = tmp_path / "test-repository"
    repo.mkdir()

    def git(*arguments):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                               "-c", "user.name=Secret Guard Test", "-c", "user.email=test@example.invalid",
                               *arguments], cwd=repo, capture_output=True, text=True, check=True)

    git("init", "--quiet")
    key = "invented-provider-credential-for-unit-testing-only"
    env = tmp_path / "fake-provider.env"
    env.write_text("OPENROUTER_API_KEY=" + key + "\n")
    monkeypatch.setattr(guard, "ROOT", repo)
    monkeypatch.setattr(sys, "argv", ["check_secrets.py", "--provider-env", str(env)])
    return repo, git, key, env


def test_clean_staging_passes_and_staged_secret_is_blocked_without_disclosure(repository, capsys):
    repo, git, key, _ = repository
    (repo / "README.md").write_text("Ordinary tracked project content.\n")
    git("add", "README.md")
    assert guard.staged_matches(repo, [key.encode()]) == []
    assert guard.main() == 0
    clean_output = capsys.readouterr()
    assert key not in clean_output.out + clean_output.err

    (repo / "unsafe.txt").write_text("Accidentally saved setting: " + key + "\n")
    git("add", "unsafe.txt")
    assert guard.staged_matches(repo, [key.encode()]) == ["unsafe.txt"]
    assert guard.main() == 1
    blocked_output = capsys.readouterr()
    assert "STOP" in blocked_output.err
    assert key not in blocked_output.out + blocked_output.err


def test_history_guard_finds_removed_secret_without_disclosing_it(repository, monkeypatch, capsys):
    repo, git, key, env = repository
    (repo / "setting.txt").write_text("Temporary test-only secret: " + key + "\n")
    git("add", "setting.txt")
    git("commit", "--quiet", "-m", "Test-only accidental credential")
    (repo / "setting.txt").write_text("Credential removed from the current working tree.\n")
    git("add", "setting.txt")
    git("commit", "--quiet", "-m", "Test-only cleanup")

    assert guard.staged_matches(repo, [key.encode()]) == []
    assert guard.history_contains(repo, [key.encode()]) is True
    monkeypatch.setattr(sys, "argv", ["check_secrets.py", "--provider-env", str(env), "--history"])
    assert guard.main() == 1
    output = capsys.readouterr()
    assert "reachable Git history" in output.err
    assert key not in output.out + output.err
