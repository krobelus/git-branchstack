#!/usr/bin/env pytest

from subprocess import Popen
from gitrevise.odb import Repository
from pathlib import Path
import pytest
import textwrap
import gitbranchstack.main as gitbranchstack

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

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)

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
    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)
    assert graph(repo, "a", "b") == expected

    # Modifying a generated branch will make us fail.
    repo.git("update-ref", "refs/heads/a", "HEAD")
    assert graph(repo, "a", "b") != expected
    try:
        gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)
        assert (
            False
        ), "Expect error about refusing to create branch when it was modified since the last run"
    except gitbranchstack.BranchWasModifiedError:
        pass

    # Unless we are asked to overwrite them.
    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT, force=True)
    assert graph(repo, "a", "b") == expected

def test_create_branches_multiline_subject(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a] multi\nline\nsubject")
    repo.git("commit", "--allow-empty", "-m", "[a] more\nlines\n\nmessage\nbody")

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)
    assert repo.git("log", "--reverse", "--format=%B", "-2", f"a").decode() == (
        "multi\nline\nsubject" + "\n" + "more\nlines\n\nmessage\nbody" + "\n"
    )

def test_create_branches_ambiguous_ref(repo) -> None:
    repo.git("update-ref", "clash", "HEAD")
    repo.git("commit", "--allow-empty", "-m", "[clash] commit on branch")

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)

    expected = """\
*  (HEAD -> 🐬) [clash] commit on branch
| *  (clash) commit on branch
|/
*  本"""

    assert graph(repo, "refs/heads/clash") == expected

def test_create_branches_stale_cache(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[lost-branch] subject")

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)

    expected = """\
*  (HEAD -> 🐬) [lost-branch] subject
| *  (lost-branch) subject
|/
*  本"""

    assert graph(repo, "lost-branch") == expected

    (repo.gitdir / "refs/heads/lost-branch").unlink()

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT)
    assert graph(repo, "lost-branch") == expected

def test_create_branches_carry_over_cache(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a] subject a")
    repo.git("commit", "--allow-empty", "-m", "[b] subject b")

    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT, branches=("b",))
    gitbranchstack.create_branches(repo, "🐬", INITIAL_COMMIT, branches=("a",))

    assert tuple(
        line.split()[0]
        for line in (repo.gitdir / "branchstack-cache").read_bytes().splitlines()
    ) == (
        b"b",
        b"a",
    )

def test_create_branches_invalid_topic(repo) -> None:
    try:
        gitbranchstack.create_branches(
            repo,
            "🐬",
            INITIAL_COMMIT,
            branches=("invalid-topic",),
        )
        assert False, "Expect error about missing topic"
    except gitbranchstack.TopicNotFoundError as e:
        assert e.args == ("invalid-topic", INITIAL_COMMIT, "HEAD")

def test_create_branches_custom_range(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a] subject a")
    repo.git("commit", "--allow-empty", "-m", "[b] subject b")

    gitbranchstack.create_branches(repo, "🐬", "HEAD~2", "HEAD~")
    assert repo.git("branch", "--list", "a")
    assert not repo.git("branch", "--list", "b")

def test_create_branches_keep_tags_in_dependencies(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[b] subject b")
    repo.git("commit", "--allow-empty", "-m", "[a:b] subject a")

    gitbranchstack.create_branches(repo, None, INITIAL_COMMIT, "HEAD", keep_tags=None)
    assert (
        repo.git("log", "--format=%s", f"{INITIAL_COMMIT}..a").decode()
        == "subject a\n" + "subject b"
    )

    gitbranchstack.create_branches(
        repo, None, INITIAL_COMMIT, "HEAD", keep_tags="dependencies"
    )
    assert (
        repo.git("log", "--format=%s", f"{INITIAL_COMMIT}..a").decode()
        == "subject a\n" + "[b] subject b"
    )

def test_create_branches_keep_tags_in_prefixed_parents(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[b] subject b")
    repo.git("commit", "--allow-empty", "-m", "[a:+b] subject a")

    gitbranchstack.create_branches(repo, None, INITIAL_COMMIT, "HEAD", keep_tags=None)
    assert (
        repo.git("log", "--format=%s", f"{INITIAL_COMMIT}..a").decode()
        == "subject a\n" + "[b] subject b"
    )

def test_dwim(repo) -> None:
    origin = "origin.git"
    assert Popen(("git", "init", "--bare", origin)).wait() == 0
    repo.git("remote", "add", "origin", origin)

    repo.git("push", "origin", "🐬:🐳")
    repo.git("config", "branch.🐬.remote", "origin")
    repo.git("config", "branch.🐬.merge", "refs/heads/🐳")

    branch, base_commit = gitbranchstack.dwim(repo)
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
    branch, base_commit = gitbranchstack.dwim(repo)
    assert branch == "test-branch"
    assert base_commit == repo.git("rev-parse", "🐬").decode()

def test_parse_log_custom_topic_affixes(repo) -> None:
    prefix = ""
    suffix = ":"
    repo.git("config", "branchstack.subjectPrefixPrefix", prefix.encode())
    repo.git("config", "branchstack.subjectPrefixSuffix", suffix.encode())

    repo.git("commit", "--allow-empty", "-m", "a: a1")
    repo.git("commit", "--allow-empty", "-m", "b: b1")
    repo.git("commit", "--allow-empty", "-m", "b: b2")
    repo.git("commit", "--allow-empty", "-m", "a: a2")
    repo.git("commit", "--allow-empty", "-m", "c:a: c1")

    commit_entries, dependency_graph = gitbranchstack.parse_log(
        repo, prefix, suffix, f"{INITIAL_COMMIT}..HEAD", "--reverse"
    )
    assert tuple((topic, message) for commit_id, topic, message in commit_entries) == (
        ("a", "a1"),
        ("b", "b1"),
        ("b", "b2"),
        ("a", "a2"),
        ("c", "c1"),
    )
    assert dependency_graph == {
        "a": {},
        "b": {},
        "c": {"a": False},
    }

def test_parse_log_forward_dependency(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "[a:b] a")
    repo.git("commit", "--allow-empty", "-m", "[b] b")
    commit_entries, dependency_graph = gitbranchstack.parse_log(
        repo, "[", "]", f"{INITIAL_COMMIT}..HEAD", "--reverse"
    )
    assert tuple((topic, message) for commit_id, topic, message in commit_entries) == (
        ("a", "a"),
        ("b", "b"),
    )
    assert dependency_graph == {
        "a": {"b": False},
        "b": {},
    }

def test_parse_log_include_others(repo) -> None:
    repo.git("commit", "--allow-empty", "-m", "a b c")
    repo.git("commit", "--allow-empty", "-m", "[t] d e f")
    commit_entries, dependency_graph = gitbranchstack.parse_log(
        repo,
        "[",
        "]",
        f"{INITIAL_COMMIT}..HEAD",
    )
    assert tuple((topic, message) for commit_id, topic, message in commit_entries) == (
        ("t", "d e f"),
        (None, "a b c"),
    )

def test_transitive_dependencies() -> None:
    dep_graph = {
        "a": {"c": False},
        "b": {"a": False},
        "c": {"b": False},
    }
    assert gitbranchstack.transitive_dependencies(dep_graph, ("a", False)) == {
        "a": False,
        "b": False,
        "c": False,
    }

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
