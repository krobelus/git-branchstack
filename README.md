# git branchstack

[![PyPi](https://img.shields.io/pypi/v/git-branchstack.svg)](https://pypi.org/project/git-branchstack)

## Motivation

When I am working on multiple changes to a [Git] repository, I usually want to
combine all of my changes in a single branch, but send them upstream in small,
reviewable chunks. As stated in [the related articles](#related-articles)
one advantage is that you can base new work on previous changes, and test
them in combination.

Git already supports this workflow via [git format-patch] and [git send-email],
however, many projects prefer to receive patches via pull requests.  To make
proposed changes easy to review, you'll want to submit a separate pull request
for each independent change on your worktree's branch.  This means that you
want to create branches containing those independent changes and nothing else.

`git branchstack` creates the desired branches without requiring you to switch
back and forth between branches (and invalidating builds). This allows you
to submit small pull requests, while enjoying the benefits of a branchless
workflow. After making any changes to your worktree's branch you can easily
update the generated branches: just re-run `git branchstack`.

## Installation

### Via pip

```sh
$ pip install --user git-branchstack
```

Instead of the last command you can also run [`./git-branchstack`](./git-branchstack) directly, provided you have `git-revise>=0.7.0`.

### Via [pipx](https://pypa.github.io/pipx/)

Use this instead to avoid breakage when your Python installation is upgraded.

```sh
$ pipx install git-branchstack
```

## Usage

Create some commits with commit messages starting with a topic tag `[...]`.
The topic name, `<topic>`, inside the square bracket tag markers `[<topic>]`,
must be an unused valid branch name.  Then run `git branchstack` to create
the branch `<topic>` with the given commits.

For example, if you have created a commit history like

    $ git log --graph --oneline
    * 9629a6c (HEAD -> local-branch) [some-unrelated-fix] Unrelated fix
    * e764f47 [my-awesome-feature] Some more work on feature
    * a9a811f [my-awesome-feature] Initial support for feature
    * 28fcf9c Local commit without topic tag
    * 5fb0776 (master) Initial commit

Then this command will (re)create two branches:

    $ git branchstack
    $ git log --graph --oneline --all
    * 9629a6c (HEAD -> local-branch) [some-unrelated-fix] Unrelated fix
    * e764f47 [my-awesome-feature] Some more work on feature
    * a9a811f [my-awesome-feature] Initial support for feature
    * 28fcf9c Local commit without topic tag
    | * 7d4d166 (my-awesome-feature) Some more work on feature
    | * fb0941f Initial support for feature
    |/
    | * 1a37fd0 (some-unrelated-fix) Unrelated fix
    |/
    * 5fb0776 (master) Initial commit

By default, `git branchstack` looks only at commits in the range
`@{upstream}..HEAD`.  It ignores commits whose subject does not start with
a topic tag.

Created branches are based on the common ancestor of your branch and the
upstream branch, that is, `git merge-base @{upstream} HEAD`.

To avoid conflicts, you can specify dependencies between branches.
For example use `[child:parent1:parent2]` to base `child` off both `parent1`
and `parent2`. The order of parents does not matter: the one that occurs
first in the commit log will be added first.

Pass `--keep-tags` to mark dependency commits by keeping the commits'
topic tags. Use `keep-tags=all` to keep all topic tags. To only keep topic
tags of select dependencies, prefix them with the `+` character (like
`[child:+parent]`).

If a commit cannot be applied cleanly, `git branchstack` will show topics
that would avoid the conflict if added as dependencies. You can either
add the missing dependencies, or resolve the conflict in your editor. You
can tell Git to remember your conflict resolution by enabling `git rerere`
(use `git config rerere.enabled true; git config rerere.autoUpdate true`).

Instead of the default topic tag delimiters (`[` and `]`), you can
set Git configuration values `branchstack.subjectPrefixPrefix` and
`branchstack.subjectPrefixSuffix`, respectively.

## Integrating Commits from Other Branches

You can use [git-branchstack-pick](./git-branchstack-pick) to integrate
other commit ranges into your branch:

```sh
$ git branchstack-pick ..some-branch 
```

This behaves like `git rebase -i` except it prefills the rebase-todo list to
cherry-pick all missing commits from `some-branch`, prefixing their commit
subjects with `[some-branch]`.  Old commits with such a subject are dropped,
so this allows you to quickly update to the latest upstream version of a
ref that has been force-pushed.

Here's how you would use this to cherry-pick GitHub pull requests:

```sh
$ git config --add remote.origin.fetch '+refs/pull/*/head:refs/remotes/origin/pr-*'
$ git fetch origin
$ git branchstack-pick ..origin/pr-123
```

## Tips

- You can use [git revise] to efficiently modify your commit messages
  to contain the `[<topic>]` tags. This command lets you edit all commit
  messages in `@{upstream}..HEAD`.

  ```sh
  $ git revise --interactive --edit
  ```

  Like `git revise`, you can use `git branchstack` during an interactive rebase.

- [`git-autofixup`](https://github.com/torbiak/git-autofixup/) can eliminate
  some of the busywork involved in creating fixup commits.

## Related Articles

- In [Stacked Diffs Versus Pull Requests], Jackson Gabbard
  describes the advantages of a patch-based workflow (using [Phabricator])
  over the one-branch-per-reviewable-change model; `git branchstack` can be used
  to implement the first workflow, even when you have to use pull-requests.

- In [My unorthodox, branchless git workflow], Drew
  DeVault explains some advantages of a similar workflow.

## Peer Projects

While `git branchstack` only offers one command and relies on standard Git
tools for everything else, there are some tools that offer a more comprehensive
set of commands to achieve a similar workflow:

- [Stacked Git](https://stacked-git.github.io/)
- [git ps](https://github.com/uptech/git-ps)
- [gh-stack](https://github.com/timothyandrew/gh-stack)
- [git machete](https://github.com/VirtusLab/git-machete)
- [git-stack](https://github.com/epage/git-stack)
- [depot-tools](https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools_tutorial.html)

Unlike its peers, `git branchstack` never modifies any worktree files,
since it uses `git revise` internally.  This makes it faster, and avoids
invalidating builds.

## Contributing

Submit feedback at <https://github.com/krobelus/git-branchstack/> or to the
[public mailing list](https://lists.sr.ht/~krobelus/git-branchless) by
sending email to <mailto:~krobelus/git-branchless@lists.sr.ht>.

[Git]: <https://git-scm.com/>
[git revise]: <https://github.com/mystor/git-revise/>
[git format-patch]: <https://git-scm.com/docs/git-format-patch>
[git send-email]: <https://git-send-email.io/>
[Stacked Diffs Versus Pull Requests]: <https://jg.gg/2018/09/29/stacked-diffs-versus-pull-requests/>
[My unorthodox, branchless git workflow]: <https://drewdevault.com/2020/04/06/My-weird-branchless-git-workflow.html>
[Phabricator]: <https://www.phacility.com/>
