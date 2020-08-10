#!/usr/bin/env pytest

from subprocess import Popen
from gitrevise.odb import Repository

import importlib

gitbranchless = importlib.import_module("git-branchless")


def test_branch_out_commits_since_upstream(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    assert Popen(("git", "init", repo_path)).wait() == 0
    remote_path = tmp_path / "repo.git"
    assert Popen(("git", "init", "--bare", remote_path)).wait() == 0

    with Repository(repo_path) as repo:
        repo.git("commit", "--allow-empty", "--message", "master: initial commit")
        repo.git("commit", "--allow-empty", "--message", "master: latest master")
        repo.git("remote", "add", "origin", remote_path)
        repo.git("push", "--set-upstream", "origin", "master")

        a = repo_path / "a"
        write(a, "first change in a\n")
        repo.git("add", a)
        repo.git("commit", "--message", "[a] a1")

        b = repo_path / "b"
        write(b, "created b\n")
        repo.git("add", b)
        repo.git("commit", "--message", "[b] b1")

        repo.git("commit", "--all", "--allow-empty", "--message", "WIP commit")

        write(a, "second change in a\n")
        repo.git("commit", "--all", "--message", "[a] a2")

        write(a, "third change in a\n")
        repo.git("commit", "--all", "--message", "[] a3")

        repo.git("commit", "--all", "--allow-empty", "--message", "another WIP commit")

        expected = """\
*  (HEAD -> master) another WIP commit
*  [] a3
*  [a] a2
*  WIP commit
*  [b] b1
*  [a] a1
*  (origin/master) master: latest master
*  master: initial commit"""

        assert expected == graph(repo)

        gitbranchless.branch_out_commits_since_upstream(
            repo, "master", "@{upstream}", gitbranchless.parser().parse_args([])
        )

        expected = """\
*  (a) a3
*  a2
*  a1
| *  (b) b1
|/  
| *  (HEAD -> master) another WIP commit
| *  [] a3
| *  [a] a2
| *  WIP commit
| *  [b] b1
| *  [a] a1
|/  
*  (origin/master) master: latest master
*  master: initial commit"""

        assert graph(repo) == expected


def test_branch_and_upstream(tmp_path) -> None:
    assert Popen(("git", "init", tmp_path)).wait() == 0

    with Repository(tmp_path) as repo:
        repo.git("commit", "--allow-empty", "--message", "initial commit")
        a = tmp_path / "a"

        # If we are not in an interactive rebase, we use the current branch.
        branch, upstream = gitbranchless.branch_and_upstream(repo)
        assert branch == "master"
        assert upstream == "@{upstream}"

        def commit(contents):
            write(a, contents)
            repo.git("add", a)
            repo.git("commit", "--message", contents)

        commit("1")
        commit("2")
        test_branch = "test-branch"
        repo.git("checkout", "-b", test_branch, "HEAD~")
        commit("3")

        # Interactive rebase, use the head of the branch we are rebasing.
        assert Popen(("git", "rebase", "master"), cwd=tmp_path).wait() != 0
        branch, upstream = gitbranchless.branch_and_upstream(repo)
        assert branch == test_branch
        # No remote means we use origin.
        assert upstream == f"origin/{test_branch}"

        # Same as above, but we do have a remote.
        test_remote = "test-remote"
        repo.git("config", f"branch.{test_branch}.remote", test_remote)
        branch, upstream = gitbranchless.branch_and_upstream(repo)
        assert branch == test_branch
        assert upstream == f"{test_remote}/{test_branch}"


def graph(repo) -> str:
    return repo.git("log", "--graph", "--oneline", "--all", "--format=%d %s",).decode()


def write(filename, contents) -> None:
    with open(filename, "w") as f:
        f.write(contents)
