# git branchless

*Efficiently manage topic branches without leaving your local branch*

## Motivation

Sometimes I am working on multiple unrelated changes to a [Git]
repository. Instead of checking out a separate branch for each change,
I prefer to do most of my work on a single branch. This [blog post] lists
some advantages.

Git already supports this workflow via [git format-patch] and [git send-email],
however, many projects prefer to receive patches as pull requests.  To make
proposed changes easy to review, you'll want to submit a separate pull
request for each independent change.  With a branchless workflow, the sole
local branch typically contains multiple independent changes. To submit
those upstream as pull requests, you need to create a separate branch for
each change.  Running `git branchless` creates the desired branches without
requiring you to switch back and forth between branches. This allows you
to submit small pull requests while enjoying the benefits of a branchless
workflow. After making any changes to your worktree's branch you can easily
update the generated branches: just re-run `git branchless`.

## Installation

1. Make sure you have Python 3.6 or higher.
2. Install [git revise]. Currently the latest development version is required:

   ```sh
   $ pip install git+https://github.com/mystor/git-revise.git@543863fa994afe8304b4afa34e4c37abf35a52ff
   ```

3. Add `git branchless` to your `$PATH`:

   ```sh
   $ git clone https://git.sr.ht/~krobelus/git-branchless && cd git-branchless
   $ ln -s $PWD/git-branchless ~/bin/
   ```

## Usage

Create some commits with commit messages starting with `[<topic>] ` where
`<topic>` is a valid branch name.  Then run `git branchless` to create a branch
for each of those topics among commits in the range `@{upstream}..HEAD`.
Each topic branch is the result of applying the topic's commits on top of
the common ancestor of your branch and the upstream branch, that is,
`git merge-base @{upstream} HEAD`.

For example, if you have a history like

    $ git log :/'Initial commit'.. --format=%s
    [my-awesome-feature] Initial support for feature
    [my-awesome-feature] Some more work on feature
    [some-unrelated-fix] Unrelated fix
    Local commit without topic tag

Then this command will create or update two branches that branch away
from HEAD:

    $ git branchless
    $ git log --all --graph --oneline
    * 2708e12 (HEAD) [my-awesome-feature] Initial support for feature
    * c6dd3ab [my-awesome-feature] Some more work on feature
    * 683de4b [some-unrelated-fix] Unrelated fix
    * 3eee379 Local commit without topic tag
    | * 7645890 (my-awesome-feature) Initial support for feature
    | * e420fd6 Some more work on feature
    |/
    | * d5f4bb2 (some-unrelated-fix) Unrelated fix
    |/
    * 2ec4d51 Initial commit

`git branchless` ignores commits whose subject does not start with a topic tag.

To avoid conflicts, you can specify dependencies between branches.
For example use `[child:parent1:parent2]` to base `child` off both `parent1`
and `parent2`. The order here does not matter because it will be determined
by which topic occurs first in the commit log.

If there is a merge conflict when trying to apply a commit, you will be
shown potentially missing dependencies. You can either add the missing
dependencies, or resolve the conflict. The conflict resolution will
be remembered if you enable `git rerere` support in `git revise`
(use `git config rerere.enabled true; git config rerere.autoUpdate true`).

Instead of the default topic tag delimiters (`[` and `]`), you can
set Git configuration values `branchless.subjectPrefixPrefix` and
`branchless.subjectPrefixSuffix`, respectively.

## Integrating commits from other branches

You can use [git-branchless-pick](./git-branchless-pick) to integrate
other commit ranges into your branch:

```sh
$ ln -s $PWD/git-branchless-pick ~/bin/
$ git branchless-pick ..some-branch 
```

This starts an interactive rebase, prompting you to cherry-pick all
missing commits from `some-branch`, prefixing their commit subjects with
`[some-branch]`.  Old commits with such a subject are dropped, so this
allows you to quickly update to the latest upstream version of a ref that
has been force-pushed.

Here's how you would use this to cherry-pick GitHub pull requests:

```sh
$ git config --add remote.origin.fetch '+refs/pull/*/head:refs/remotes/origin/pr-*'
$ git fetch origin
$ git branchless-pick $(git merge-base origin/pr-123 HEAD)..origin/pr-123
```

## Tips

You can use [git revise] to efficiently modify your commit messages to contain
the `[<topic>]` tags. This command lets you edit all commit messages in
`@{upstream}..HEAD`.

```sh
$ git revise --interactive --edit
```

Like `git revise`, you can use `git branchless` during an interactive rebase.

## Contributing

You're welcome give feedback on the public mailing list by sending email
to <mailto:~krobelus/git-branchless@lists.sr.ht>.  To see prior postings,
visit the [list archive](https://lists.sr.ht/~krobelus/git-branchless).

[Git]: <https://git-scm.com/>
[git revise]: <https://github.com/mystor/git-revise/>
[git format-patch]: <https://git-scm.com/docs/git-format-patch>
[git send-email]: <https://git-send-email.io/>
[blog post]: <https://drewdevault.com/2020/04/06/My-weird-branchless-git-workflow.html>
