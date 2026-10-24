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


@pytest.mark.parametrize("use_provider_env", [False, True])
def test_retired_key_is_checked_in_staging_and_history_after_rotation(repository, monkeypatch, capsys, use_provider_env):
    repo, git, current, env = repository
    private = repo / ".runtime/live"
    retired = private / "retired"
    retired.mkdir(parents=True)
    old_key = "invented-retired-provider-credential-not-a-real-key"
    (private / "provider.key").write_text(current + "\n")
    (retired / "previous.key").write_text(old_key + "\n")
    (repo / ".gitignore").write_text(".runtime/\n")
    (repo / "README.md").write_text("Current project without any credential.\n")
    git("add", ".gitignore", "README.md")
    arguments = ["check_secrets.py"] + (["--provider-env", str(env)] if use_provider_env else [])
    monkeypatch.setattr(sys, "argv", arguments)
    assert guard.main() == 0

    (repo / "accidental.txt").write_text("An old setting was pasted: " + old_key + "\n")
    git("add", "accidental.txt")
    assert guard.main() == 1
    staged = capsys.readouterr()
    assert "STOP" in staged.err and old_key not in staged.out + staged.err
    assert current not in staged.out + staged.err

    git("commit", "--quiet", "-m", "Test-only retired credential leak")
    (repo / "accidental.txt").write_text("The retired credential was removed.\n")
    git("add", "accidental.txt")
    git("commit", "--quiet", "-m", "Test-only working-tree cleanup")
    assert guard.main() == 0
    monkeypatch.setattr(sys, "argv", arguments + ["--history"])
    assert guard.main() == 1
    historical = capsys.readouterr()
    assert "reachable Git history" in historical.err
    assert old_key not in historical.out + historical.err
    assert current not in historical.out + historical.err


def test_retired_key_scan_ignores_symlinks_and_non_regular_files(repository, tmp_path, capsys):
    repo, git, _, _ = repository
    retired = repo / ".runtime/live/retired"
    retired.mkdir(parents=True)
    linked_value = "invented-outside-credential-not-part-of-retired-archive"
    outside = tmp_path / "outside.key"
    outside.write_text(linked_value + "\n")
    (retired / "linked.key").symlink_to(outside)
    (retired / "directory.key").mkdir()
    (repo / ".gitignore").write_text(".runtime/\n")
    (repo / "unrelated.txt").write_text(linked_value + "\n")
    git("add", ".gitignore", "unrelated.txt")
    assert guard.retired_provider_keys(repo) == []
    assert guard.main() == 0
    output = capsys.readouterr()
    assert linked_value not in output.out + output.err


def test_unreadable_as_a_key_retired_archive_blocks_without_disclosure(repository, capsys):
    repo, _, _, _ = repository
    retired = repo / ".runtime/live/retired"
    retired.mkdir(parents=True)
    malformed = "invented-private-content\nnot-a-single-key"
    (retired / "malformed.key").write_text(malformed)
    assert guard.main() == 2
    output = capsys.readouterr()
    assert "could not finish safely" in output.err
    assert malformed not in output.out + output.err
