#!/usr/bin/env pytest

from subprocess import Popen
from gitrevise.odb import Repository
from tempfile import mkdtemp

import importlib
gitbranchless = importlib.import_module("git-branchless")


def graph(repo):
    return repo.git(
        "log",
        "--graph",
        "--oneline",
        "--all",
        "--format=%d %s",
    ).decode()


def test_simple(tmp_path):
    repo_path = tmp_path / "repo"
    assert Popen(("git", "init", repo_path)).wait() == 0
    remote_path = tmp_path / "repo.git"
    assert Popen(("git", "init", "--bare", remote_path)).wait() == 0

    with Repository(repo_path) as repo:
        repo.git("commit", "--allow-empty", "--message",
                 "master: initial commit")
        repo.git("commit", "--allow-empty", "--message",
                 "master: latest master")
        repo.git("remote", "add", "origin", remote_path)
        repo.git("push", "--set-upstream", "origin", "master")

        a = f"{repo_path}/a"
        with open(a, "w") as f:
            f.write("first change in a\n")
        repo.git("add", a)
        repo.git("commit", "--message", "[a] a1")

        b = f"{repo_path}/b"
        with open(b, "w") as f:
            f.write("created b\n")
        repo.git("add", b)
        repo.git("commit", "--message", "[b] b1")

        # with open(a, 'w') as f:
        #     f.write("conflict in 1\n")
        # repo.git("commit", "--all", "--message", "[c] conflict in a")

        with open(a, "w") as f:
            f.write("second change in a\n")
        repo.git("commit", "--all", "--message", "[a] a2")

        with open(a, "w") as f:
            f.write("third change in a\n")
        repo.git("commit", "--all", "--message", "[] a3")

        repo.git("commit", "--all", "--allow-empty", "--message", "WIP commit")
        repo.git("commit", "--all", "--allow-empty", "--message",
                 "another WIP commit")

        expected = """\
*  (HEAD -> master) another WIP commit
*  WIP commit
*  [] a3
*  [a] a2
*  [b] b1
*  [a] a1
*  (origin/master) master: latest master
*  master: initial commit"""

        assert expected == graph(repo)

        gitbranchless.update_branches_from_HEAD(
            repo,
            gitbranchless.parser().parse_args([]))

        expected = """\
*  (a) a3
*  a2
*  a1
| *  (b) b1
|/  
| *  (HEAD -> master) another WIP commit
| *  WIP commit
| *  [] a3
| *  [a] a2
| *  [b] b1
| *  [a] a1
|/  
*  (origin/master) master: latest master
*  master: initial commit"""

        assert graph(repo) == expected
