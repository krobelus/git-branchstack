# git branchless

*Efficiently create topic branches without leaving your local branch*

## Motivation

Sometimes I am working on multiple unrelated changes to a [Git]
repository. Instead of using a separate branch for each change, I prefer
a branchless workflow similar to the one described in this [blog post by
Drew DeVault].

Git ships with [git send-email] which suits this workflow, however, many
projects prefer to receive patches via pull requests.  To make proposed
changes easy to review, you'll want to submit a separate pull request for
each independent change.  With a branchless workflow, the sole local branch
typically contains multiple independent changes. To submit those upstream as
pull requests, you need to create a separate topic branch for each change.
`git branchless` creates the desired topic branches without requiring
you to switch back and forth between branches. This allows you to submit
small, isolated pull requests while enjoying the benefits of a branchless
workflow. After making any changes to your branch (for example by addressing
review comments or rebasing on upstream changes) you can trivially update
the generated topic branches: just re-run `git branchless`.

## Installation

1. Make sure you have Python 3.6 or higher.
2. Install [git revise]. This is currently used as a library to perform merges
   in-memory.
3. Add `git branchless` to your `$PATH`:

   ```sh
   $ git clone https://git.sr.ht/~krobelus/git-branchless && cd git-branchless
   $ ln -s $PWD/git-branchless ~/bin/
   ```

## Usage

Create some commits with commit messages starting with `[topic] ` where `topic`
is any valid branch name.  Then run `git branchless` to create a branch
for each of those topics among commits in the range `@{upstream}..HEAD`.
Each topic branch is the result of applying the topic's commits on top of
`@{upstream}`.

For example, if you have a history like

    $ git log @{upstream}.. --format=%s
    WIP unfinished commit
    [my-awesome-feature] Some more work on feature
    [some-unrelated-fix] Unrelated fix
    [my-awesome-feature] Initial support for feature

Then this command will create two branches:

    $ git branchless
    Updating refs/heads/my-awesome-feature (ba5e58a => 48a53fec)
    Updating refs/heads/some-unrelated-fix (ba5e58a => e612f26e)

    my-awesome-feature
        9d33b57e Initial support for feature
        48a53fec Some more work on feature

    some-unrelated-fix
        e612f26e Unrelated fix

When you add another commit, or update a previous one, simply re-run `git
branchless` to update the generated topic branches.

Commits whose message does not start with a topic tag are ignored.
Use the special commit message prefix `[]` to reuse the prevous commit's topic.

If there is a merge conflict, you will be prompted to resolve it.  However,
it is usually a good idea to avoid this by using the same topic for dependent
commits.

## Tips

You can use [git revise] to efficiently modify your commit messages to
contain the `[topic]` tags. This command lets you edit all commit messages in
`@{upstream}..`.

```sh
$ git revise --interactive --edit
```
Like `git revise`, you can use `git branchless` during an interactive rebase.

To push all branches there is a separate script [git-branchless-push](./git-branchless-push):

```sh
$ ln -s $PWD/git-branchless-push ~/bin/
$ git branchless && git branchless-push
```

## Contributing

You can send feedback to the [git-branchless mailing
list](https://lists.sr.ht/~krobelus/git-branchless).

[blog post by Drew DeVault]: <https://drewdevault.com/2020/04/06/My-weird-branchless-git-workflow.html>
[Git]: <https://git-scm.com/>
[git revise]: <https://github.com/mystor/git-revise/>
[git send-email]: <https://git-send-email.io/>
