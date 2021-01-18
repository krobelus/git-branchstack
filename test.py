#!/usr/bin/env pytest

from subprocess import Popen
from gitrevise.odb import Repository
from pathlib import Path
import pytest
import textwrap
import importlib

gitbranchless = importlib.import_module("git-branchless")

def test_create_branches(repo) -> None:
    a = repo.workdir / "a"
    repo.git("commit", "--allow-empty", "-m", "[a] a1")
    repo.git("commit", "--allow-empty", "-m", "[b] b1")
    repo.git("commit", "--allow-empty", "-m", "WIP commit")
    repo.git("commit", "--allow-empty", "-m", "[a] a2")
    repo.git("commit", "--allow-empty", "-m", "[a] a3")
    repo.git("commit", "--allow-empty", "-m", "another WIP commit")

    expected = """\
*  (HEAD -> 🐬) another WIP commit
*  [a] a3
*  [a] a2
*  WIP commit
*  [b] b1
*  [a] a1
*  本"""

    assert expected == graph(repo)

    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)

    expected = """\
*  (HEAD -> 🐬) another WIP commit
*  [a] a3
*  [a] a2
*  WIP commit
*  [b] b1
*  [a] a1
| *  (a) a3
| *  a2
| *  a1
|/
| *  (b) b1
|/
*  本"""

    assert graph(repo, "a", "b") == expected

    # A repeated invocation does not change anything.
    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)
    assert graph(repo, "a", "b") == expected

    # Modifying a generated branch will make us fail.
    repo.git("update-ref", "refs/heads/a", "HEAD")
    assert graph(repo, "a", "b") != expected
    try:
        gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)
        assert (
            False
        ), "Expect error about refusing to create branch when it was modified since the last run"
    except gitbranchless.BranchWasModifiedError:
        pass

    # Unless we are asked to overwrite them.
    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT, force=True)
    assert graph(repo, "a", "b") == expected

def test_create_branches_ambiguos_ref(repo) -> None:
    repo.git("update-ref", "clash", "HEAD")
    repo.git("commit", "--allow-empty", "-m", "[clash] commit on branch")

    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)

    expected = """\
*  (HEAD -> 🐬) [clash] commit on branch
| *  (clash) commit on branch
|/
*  本"""

    assert graph(repo, "refs/heads/clash") == expected

def test_create_branches_stale_cache(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[lost-branch] subject")

    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)

    expected = """\
*  (HEAD -> 🐬) [lost-branch] subject
| *  (lost-branch) subject
|/
*  本"""

    assert graph(repo, "lost-branch") == expected

    (repo.gitdir / "refs/heads/lost-branch").unlink()

    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT)
    assert graph(repo, "lost-branch") == expected

def test_create_branches_carry_over_cache(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a] subject a")
    repo.git("commit", "--allow-empty", "-m", "[b] subject b")

    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT, branches=("b",))
    gitbranchless.create_branches(repo, "🐬", INITIAL_COMMIT, branches=("a",))

    assert tuple(
        line.split()[0]
        for line in (repo.gitdir / "branchless-cache").read_bytes().splitlines()
    ) == (
        b"b",
        b"a",
    )

def test_dwim(repo) -> None:
    origin = "origin.git"
    assert Popen(("git", "init", "--bare", origin)).wait() == 0
    repo.git("remote", "add", "origin", origin)

    repo.git("push", "origin", "🐬:🐳")
    repo.git("config", "branch.🐬.remote", "origin")
    repo.git("config", "branch.🐬.merge", "refs/heads/🐳")

    branch, base_commit = gitbranchless.dwim(repo)
    assert branch == "🐬"
    assert base_commit == "@{upstream}"
    root_id = repo.git("rev-parse", INITIAL_COMMIT).decode()
    assert repo.git("rev-parse", "@{upstream}").decode() == root_id
    def commit(contents):
        repo.git("add", write("a", contents))
        repo.git("commit", "-m", contents)
    commit("onto")
    commit("2")
    test_branch = "test-branch"
    repo.git("checkout", "-b", test_branch, "HEAD~")
    commit("3")

    assert Popen(("git", "rebase", "🐬")).wait() != 0
    branch, base_commit = gitbranchless.dwim(repo)
    assert branch == "test-branch"
    assert base_commit == repo.git("rev-parse", "🐬").decode()

def test_parse_log_custom_topic_affixes(repo) -> None:
    repo.git("config", "branchless.subjectPrefixPrefix", r"")
    repo.git("config", "branchless.subjectPrefixSuffix", r":")

    repo.git("commit", "--allow-empty", "-m", "a: a1")
    repo.git("commit", "--allow-empty", "-m", "b: b1")
    repo.git("commit", "--allow-empty", "-m", "b: b2")
    repo.git("commit", "--allow-empty", "-m", "a: a2")
    repo.git("commit", "--allow-empty", "-m", "c:a: c1")

    commit_entries, dependency_graph = gitbranchless.parse_log(repo, INITIAL_COMMIT)
    assert tuple((topic, message) for commit_id, topic, message in commit_entries) == (
        ("a", "a1"),
        ("b", "b1"),
        ("b", "b2"),
        ("a", "a2"),
        ("c", "c1"),
    )
    assert dependency_graph == {
        "a": set(),
        "b": set(),
        "c": {"a"},
    }

def test_parse_log_forward_dependency(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a:b] a")
    repo.git("commit", "--allow-empty", "-m", "[b] b")
    commit_entries, dependency_graph = gitbranchless.parse_log(repo, INITIAL_COMMIT)
    assert tuple((topic, message) for commit_id, topic, message in commit_entries) == (
        ("a", "a"),
        ("b", "b"),
    )
    assert dependency_graph == {
        "a": {"b"},
        "b": set(),
    }

def test_transitive_dependencies() -> None:
    dep_graph = {
        "a": {"c"},
        "b": {"a"},
        "c": {"b"},
    }
    assert gitbranchless.transitive_dependencies(dep_graph, "a") == {"a", "b", "c"}

# Taken from git-revise
@pytest.fixture(autouse=True)
def hermetic_seal(tmp_path_factory, monkeypatch):
    # Lock down user git configuration
    home = tmp_path_factory.mktemp("home")
    xdg_config_home = home / ".config"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "true")

    # Lock down commit/authoring time
    monkeypatch.setenv("GIT_AUTHOR_DATE", "1500000000 -0500")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "1500000000 -0500")

    # Install known configuration
    gitconfig = home / ".gitconfig"
    gitconfig.write_bytes(
        textwrap.dedent(
            """\
            [core]
                eol = lf
                autocrlf = false
            [init]
                defaultBranch = "🐬"
            [user]
                email = test@example.com
                name = Test User
            """
        ).encode()
    )
    monkeypatch.setenv("GIT_EDITOR", "false")

    # Switch into a test workdir, and init our repo
    workdir = tmp_path_factory.mktemp("workdir")
    monkeypatch.chdir(workdir)
    assert Popen(("git", "init", "-q")).wait() == 0
    assert Popen(("git", "commit", "--allow-empty", "-m", "本")).wait() == 0

INITIAL_COMMIT = ":/本"
@pytest.fixture
def repo(hermetic_seal):
    with Repository() as repo:
        yield repo

def graph(repo, *args) -> str:
    output = repo.git(
        "log",
        "--graph",
        "--oneline",
        "--format=%d %s",
        "🐬",
        *args,
        "--",
    ).decode()
    return "\n".join(line.rstrip() for line in output.splitlines())

def write(filename, contents) -> str:
    with open(filename, "w") as f:
        f.write(contents)
    return filename
